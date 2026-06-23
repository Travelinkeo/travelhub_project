import logging
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.bookings.models import BoletoImportado, Proveedor, Venta
from apps.finance.models import Factura, ItemFactura
from apps.finance.models.currencies import Moneda

logger = logging.getLogger(__name__)


class InvoiceService:
    @staticmethod
    def create_invoice_from_sale(venta_id):
        """Wrapper for generate_double_invoice using ID"""
        try:
            venta = Venta.objects.get(pk=venta_id)
            return InvoiceService.generate_double_invoice(venta)
        except Venta.DoesNotExist:
            logger.error(f"Cannot generate invoice: Venta {venta_id} not found.")
            return None

    @staticmethod
    @transaction.atomic
    def generate_double_invoice(venta: Venta):
        """
        Generates or updates two separate invoices (Factura) for a Venta:
        1. Intermediación: For the provider (Airline/GDS) amount.
        2. Venta Propia: For the agency fee/commission.
        """
        if not venta.cliente:
            raise ValueError(f"Venta {venta.id_venta} must have a client assigned.")

        # 1. Intermediation Invoice (Terceros)
        boletos = BoletoImportado.objects.filter(venta_asociada=venta).select_related(
            "proveedor_emisor"
        )
        factura_tercero = None

        if boletos.exists():
            first_boleto = boletos.first()
            proveedor_emisor = first_boleto.proveedor_emisor
            if not proveedor_emisor and first_boleto.aerolinea_emisora:
                proveedor_emisor = Proveedor.objects.filter(
                    nombre__icontains=first_boleto.aerolinea_emisora
                ).first()

            # Look for existing intermediation invoice for this sale
            factura_tercero = Factura.objects.filter(
                venta_asociada=venta, tipo_operacion=Factura.TipoOperacion.INTERMEDIACION
            ).first()

            if not factura_tercero:
                # Create a new one if it doesn't exist
                factura_tercero = Factura.objects.create(
                    venta_asociada=venta,
                    cliente=venta.cliente,
                    moneda=venta.moneda,
                    tipo_operacion=Factura.TipoOperacion.INTERMEDIACION,
                    tasa_cambio_bcv=venta.tasa_cambio_bcv,
                    fecha_emision=timezone.localtime(timezone.now()).date(),
                    tercero_rif=proveedor_emisor.rif if proveedor_emisor else "J-00000000-0",
                    tercero_razon_social=proveedor_emisor.nombre
                    if proveedor_emisor
                    else (first_boleto.aerolinea_emisora or "Aerolínea Genérica"),
                    cliente_identificacion=venta.cliente.numero_documento or "N/A",
                    cliente_direccion=venta.cliente.direccion_linea1 or "N/A",
                    emisor_rif=venta.agencia.rif if venta.agencia else "J-00000000-0",
                    emisor_razon_social=venta.agencia.nombre
                    if venta.agencia
                    else "Agencia de Viajes",
                    emisor_direccion_fiscal=venta.agencia.direccion
                    if venta.agencia
                    else "Dirección Agencia",
                    agencia=venta.agencia,
                )
            else:
                # Update client info on existing invoice if changed
                factura_tercero.cliente = venta.cliente
                factura_tercero.cliente_identificacion = venta.cliente.numero_documento or "N/A"
                factura_tercero.cliente_direccion = venta.cliente.direccion_linea1 or "N/A"
                factura_tercero.save(
                    update_fields=["cliente", "cliente_identificacion", "cliente_direccion"]
                )

            # Synchronize items for each boleto
            existing_items = {
                item.numero_boleto: item
                for item in factura_tercero.items_factura.all()
                if item.numero_boleto
            }
            processed_tickets = set()

            for boleto in boletos:
                ticket_num = boleto.numero_boleto
                if not ticket_num:
                    continue
                processed_tickets.add(ticket_num)
                nombre_pax = (
                    getattr(boleto, "nombre_pasajero_completo", "")
                    or getattr(boleto, "nombre_pasajero_procesado", "")
                    or "Pasajero"
                )

                item_data = {
                    "descripcion": f"Boleto {ticket_num} - {nombre_pax}",
                    "cantidad": 1,
                    "precio_unitario": boleto.total_boleto or 0,
                    "tipo_servicio": ItemFactura.TipoServicio.TRANSPORTE_AEREO_NACIONAL
                    if "NAC" in (boleto.ruta_vuelo or "")
                    else ItemFactura.TipoServicio.COMISION_INTERMEDIACION,
                    "es_gravado": False,
                    "nombre_pasajero": nombre_pax,
                    "itinerario": boleto.ruta_vuelo or "",
                    "codigo_aerolinea": boleto.aerolinea_emisora[:10]
                    if boleto.aerolinea_emisora
                    else "",
                }

                if ticket_num in existing_items:
                    # Update existing item
                    item = existing_items[ticket_num]
                    for key, val in item_data.items():
                        setattr(item, key, val)
                    item.save()
                else:
                    # Create new item
                    ItemFactura.objects.create(
                        factura=factura_tercero,
                        numero_boleto=ticket_num,
                        agencia=venta.agencia,
                        **item_data,
                    )

            # Remove items from the invoice that are no longer in the sale's boletos
            for ticket_num, item in existing_items.items():
                if ticket_num not in processed_tickets:
                    item.delete()

            # Recalculate totals of the invoice
            if hasattr(factura_tercero, "calcular_impuestos_venezuela"):
                factura_tercero.calcular_impuestos_venezuela()
            else:
                factura_tercero.recalcular_totales()
                factura_tercero.save()

        # 2. Agency Fee Invoice (Venta Propia)
        fees = venta.fees_venta.all()
        factura_propia = None

        if fees.exists() or not factura_tercero:
            factura_propia = Factura.objects.filter(
                venta_asociada=venta, tipo_operacion=Factura.TipoOperacion.VENTA_PROPIA
            ).first()

            if not factura_propia:
                factura_propia = Factura.objects.create(
                    venta_asociada=venta,
                    cliente=venta.cliente,
                    moneda=venta.moneda,
                    tipo_operacion=Factura.TipoOperacion.VENTA_PROPIA,
                    tasa_cambio_bcv=venta.tasa_cambio_bcv,
                    fecha_emision=timezone.localtime(timezone.now()).date(),
                    cliente_identificacion=venta.cliente.numero_documento or "N/A",
                    cliente_direccion=venta.cliente.direccion_linea1 or "N/A",
                    emisor_rif=venta.agencia.rif if venta.agencia else "J-00000000-0",
                    emisor_razon_social=venta.agencia.nombre
                    if venta.agencia
                    else "Agencia de Viajes",
                    emisor_direccion_fiscal=venta.agencia.direccion
                    if venta.agencia
                    else "Dirección Agencia",
                    agencia=venta.agencia,
                )
            else:
                factura_propia.cliente = venta.cliente
                factura_propia.cliente_identificacion = venta.cliente.numero_documento or "N/A"
                factura_propia.cliente_direccion = venta.cliente.direccion_linea1 or "N/A"
                factura_propia.save(
                    update_fields=["cliente", "cliente_identificacion", "cliente_direccion"]
                )

            # Sync fee items: delete and recreate
            factura_propia.items_factura.all().hard_delete()

            for fee in fees:
                ItemFactura.objects.create(
                    factura=factura_propia,
                    descripcion=f"Fee de Gestión: {fee.get_tipo_fee_display()}",
                    cantidad=1,
                    precio_unitario=fee.monto,
                    tipo_servicio=ItemFactura.TipoServicio.ALOJAMIENTO_Y_OTROS_GRAVADOS,
                    es_gravado=True,
                    alicuota_iva=Decimal("25.00"),
                    agencia=venta.agencia,
                )

            # Recalculate totals of own invoice
            if hasattr(factura_propia, "calcular_impuestos_venezuela"):
                factura_propia.calcular_impuestos_venezuela()
            else:
                factura_propia.recalcular_totales()
                factura_propia.save()

        return factura_tercero, factura_propia

    @staticmethod
    @transaction.atomic
    def mass_assign_and_invoice(queryset, cliente):
        """
        Processes a queryset of BoletoImportado:
        1. Ensures Venta existence.
        2. Assigns cliente.
        3. Generates and returns double invoices.
        """
        results = []
        for boleto in queryset:
            try:
                # 1. Get or Create Venta
                venta = boleto.venta_asociada
                if not venta:
                    venta = Venta.objects.create(
                        cliente=cliente,
                        agencia=boleto.agencia,
                        moneda=Moneda.objects.get(codigo_iso="USD"),
                        subtotal=boleto.tarifa_base or 0,
                        impuestos=boleto.impuestos_total_calculado or 0,
                        descripcion_general=f"Venta masiva desde Boleto {boleto.numero_boleto}",
                        canal_origen=Venta.CanalOrigen.IMPORTACION,
                    )
                    boleto.venta_asociada = venta
                    boleto.save(update_fields=["venta_asociada"])
                else:
                    venta.cliente = cliente
                    venta.save(update_fields=["cliente"])

                # 2. Generate Invoices
                f_tercero, f_propia = InvoiceService.generate_double_invoice(venta)
                results.append(
                    {
                        "boleto_id": boleto.pk,
                        "venta_id": venta.pk,
                        "factura_tercero": f_tercero.pk if f_tercero else None,
                        "factura_propia": f_propia.pk if f_propia else None,
                    }
                )
            except Exception as e:
                logger.error(f"Error mass processing boleto {boleto.pk}: {e}")
                results.append({"boleto_id": boleto.pk, "error": str(e)})

        return results
