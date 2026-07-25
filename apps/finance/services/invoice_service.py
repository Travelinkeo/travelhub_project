"""Servicio de invoice service para la aplicación finance.
"""

import logging
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.bookings.models import BoletoImportado, Proveedor, Venta
from apps.common.models import Moneda
from apps.finance.models import Factura, ItemFactura

logger = logging.getLogger(__name__)


class InvoiceService:
    """Servicio para invoice. Uso: instanciar según necesidad del dominio.
    """
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
                cliente=venta.cliente,
            ).first()

            if not factura_tercero:
                factura_tercero = Factura.objects.create(
                    cliente=venta.cliente,
                    tasa_bcv_aplicada=getattr(venta, "tasa_cambio_bcv", Decimal("1.00")),
                    fecha_emision=timezone.localtime(timezone.now()).date(),
                    agencia=venta.agencia,
                )
            else:
                factura_tercero.cliente = venta.cliente
                factura_tercero.save(update_fields=["cliente"])

            # Synchronize items for each boleto
            factura_tercero.items.all().delete()

            for boleto in boletos:
                nombre_pax = (
                    getattr(boleto, "nombre_pasajero_completo", "")
                    or getattr(boleto, "nombre_pasajero_procesado", "")
                    or "Pasajero"
                )
                ticket_num = boleto.numero_boleto or "N/A"

                ItemFactura.objects.create(
                    factura=factura_tercero,
                    agencia=venta.agencia,
                    descripcion=f"Boleto {ticket_num} - {nombre_pax}",
                    cantidad=1,
                    precio_unitario_usd=boleto.total_boleto or 0,
                    exento=True,
                )

            factura_tercero.save()

        # 2. Agency Fee Invoice (Venta Propia)
        fees = venta.fees_venta.all()
        factura_propia = None

        if fees.exists() or not factura_tercero:
            factura_propia = Factura.objects.filter(cliente=venta.cliente).first()

            if not factura_propia:
                factura_propia = Factura.objects.create(
                    cliente=venta.cliente,
                    tasa_bcv_aplicada=getattr(venta, "tasa_cambio_bcv", Decimal("1.00")),
                    fecha_emision=timezone.localtime(timezone.now()).date(),
                    agencia=venta.agencia,
                )
            else:
                factura_propia.cliente = venta.cliente
                factura_propia.save(update_fields=["cliente"])

            # Sync fee items: delete and recreate
            factura_propia.items.all().delete()

            for fee in fees:
                ItemFactura.objects.create(
                    factura=factura_propia,
                    descripcion=f"Fee de Gestión: {fee.get_tipo_fee_display()}",
                    cantidad=1,
                    precio_unitario_usd=fee.monto,
                    exento=False,
                    agencia=venta.agencia,
                )

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
