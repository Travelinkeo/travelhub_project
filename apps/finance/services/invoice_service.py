import logging
from decimal import Decimal
from django.utils import timezone
from django.db import transaction
from apps.finance.models import Factura, ItemFactura
from core.models.facturacion_consolidada import FacturaConsolidada, ItemFacturaConsolidada
from apps.bookings.models import Venta, ItemVenta, BoletoImportado, FeeVenta
from core.models_catalogos import Proveedor, Moneda
from apps.crm.models import Cliente

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
        Generates two separate invoices (FacturaConsolidada) for a Venta:
        1. Intermediación: For the provider (Airline/GDS) amount.
        2. Venta Propia: For the agency fee/commission.
        """
        if not venta.cliente:
            raise ValueError(f"Venta {venta.id_venta} must have a client assigned.")

        # 1. Gather Boleto Data (Intermediation)
        boleto = BoletoImportado.objects.filter(venta_asociada=venta).first()
        factura_tercero = None
        if boleto:
            # Determine provider
            proveedor_emisor = boleto.proveedor_emisor
            if not proveedor_emisor and boleto.aerolinea_emisora:
                proveedor_emisor = Proveedor.objects.filter(nombre__icontains=boleto.aerolinea_emisora).first()

            # Create Intermediation Invoice
            factura_tercero = FacturaConsolidada.objects.create(
                venta_asociada=venta,
                cliente=venta.cliente,
                moneda=venta.moneda,
                tipo_operacion=FacturaConsolidada.TipoOperacion.INTERMEDIACION,
                tasa_cambio_bcv=venta.tasa_cambio_bcv,
                tercero_rif=proveedor_emisor.rif if proveedor_emisor else "J-00000000-0",
                tercero_razon_social=proveedor_emisor.nombre if proveedor_emisor else (boleto.aerolinea_emisora or "Aerolínea Genérica"),
                cliente_identificacion=venta.cliente.numero_documento or "N/A",
                cliente_direccion=venta.cliente.direccion_linea1 or "N/A",
                emisor_rif=venta.agencia.rif if venta.agencia else "J-00000000-0",
                emisor_razon_social=venta.agencia.nombre if venta.agencia else "Agencia de Viajes",
                emisor_direccion_fiscal=venta.agencia.direccion if venta.agencia else "Dirección Agencia",
                agencia=venta.agencia  # SaaS Isolation
            )

            # Add Item for Intermediation
            ItemFacturaConsolidada.objects.create(
                factura=factura_tercero,
                descripcion=f"Boleto {boleto.numero_boleto} - {boleto.nombre_pasajero_completo}",
                cantidad=1,
                precio_unitario=boleto.total_boleto or 0,
                tipo_servicio=ItemFacturaConsolidada.TipoServicio.TRANSPORTE_AEREO_NACIONAL if "NAC" in (boleto.ruta_vuelo or "") else ItemFacturaConsolidada.TipoServicio.COMISION_INTERMEDIACION,
                es_gravado=False,  # Usually excluded from agency's VAT if handled as intermediation
                nombre_pasajero=boleto.nombre_pasajero_completo,
                numero_boleto=boleto.numero_boleto,
                itinerario=boleto.ruta_vuelo,
                codigo_aerolinea=boleto.aerolinea_emisora[:10] if boleto.aerolinea_emisora else "",
            )

        # 2. Create Agency Fee Invoice
        fees = venta.fees_venta.all()
        factura_propia = None
        if fees.exists() or not factura_tercero:
             factura_propia = FacturaConsolidada.objects.create(
                venta_asociada=venta,
                cliente=venta.cliente,
                moneda=venta.moneda,
                tipo_operacion=FacturaConsolidada.TipoOperacion.VENTA_PROPIA,
                tasa_cambio_bcv=venta.tasa_cambio_bcv,
                cliente_identificacion=venta.cliente.numero_documento or "N/A",
                cliente_direccion=venta.cliente.direccion_linea1 or "N/A",
                emisor_rif=venta.agencia.rif if venta.agencia else "J-00000000-0",
                emisor_razon_social=venta.agencia.nombre if venta.agencia else "Agencia de Viajes",
                emisor_direccion_fiscal=venta.agencia.direccion if venta.agencia else "Dirección Agencia",
                agencia=venta.agencia  # SaaS Isolation
            )

             for fee in fees:
                 ItemFacturaConsolidada.objects.create(
                     factura=factura_propia,
                     descripcion=f"Fee de Gestión: {fee.get_tipo_fee_display()}",
                     cantidad=1,
                     precio_unitario=fee.monto,
                     tipo_servicio=ItemFacturaConsolidada.TipoServicio.ALOJAMIENTO_Y_OTROS_GRAVADOS,
                     es_gravado=True,
                     alicuota_iva=Decimal('16.00')
                 )

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
                        moneda=Moneda.objects.get(codigo_iso='USD'),
                        subtotal=boleto.tarifa_base or 0,
                        impuestos=boleto.impuestos_total_calculado or 0,
                        descripcion_general=f"Venta masiva desde Boleto {boleto.numero_boleto}",
                        canal_origen=Venta.CanalOrigen.IMPORTACION
                    )
                    boleto.venta_asociada = venta
                    boleto.save(update_fields=['venta_asociada'])
                else:
                    venta.cliente = cliente
                    venta.save(update_fields=['cliente'])

                # 2. Generate Invoices
                f_tercero, f_propia = InvoiceService.generate_double_invoice(venta)
                results.append({
                    'boleto_id': boleto.pk,
                    'venta_id': venta.pk,
                    'factura_tercero': f_tercero.pk if f_tercero else None,
                    'factura_propia': f_propia.pk if f_propia else None,
                })
            except Exception as e:
                logger.error(f"Error mass processing boleto {boleto.pk}: {e}")
                results.append({'boleto_id': boleto.pk, 'error': str(e)})
        
        return results
