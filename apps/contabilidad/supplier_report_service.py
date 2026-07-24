import logging

from django.db import transaction

from apps.contabilidad.models import ItemReporteVentaProveedor, ReporteVentaProveedor
from apps.contabilidad.supplier_parsers import SupplierReportParserFactory
from core.middleware import agency_context

logger = logging.getLogger(__name__)


class SupplierReportProcessorService:
    @classmethod
    def process_pdf_report(
        cls,
        agencia,
        pdf_bytes: bytes,
        filename: str = "",
        subject: str = "",
        sender_email: str = "",
    ) -> ReporteVentaProveedor:
        parser = SupplierReportParserFactory.get_parser(
            pdf_bytes=pdf_bytes,
            filename=filename,
            subject=subject,
            sender_email=sender_email,
        )

        if not parser:
            raise ValueError(
                f"No se pudo determinar un parser adecuado para el reporte (emisor: {sender_email}, asunto: {subject}, archivo: {filename})."
            )

        parsed_data = parser.parse()

        with agency_context(agencia):
            with transaction.atomic():
                reporte = ReporteVentaProveedor.objects.create(
                    agencia=agencia,
                    proveedor_nombre=parsed_data.get("proveedor_nombre", "DESCONOCIDO"),
                    codigo_agencia_proveedor=parsed_data.get("codigo_agencia_proveedor", ""),
                    fecha_reporte_desde=parsed_data.get("fecha_reporte_desde"),
                    fecha_reporte_hasta=parsed_data.get("fecha_reporte_hasta"),
                    saldo_anterior=parsed_data.get("saldo_anterior"),
                    monto_total_ventas=parsed_data.get("monto_total_ventas"),
                    saldo_final=parsed_data.get("saldo_final"),
                    archivo_reporte_pdf=None,
                    raw_extracted_text=parsed_data.get("raw_text", ""),
                )

                items_to_create = []
                for item_data in parsed_data.get("items", []):
                    items_to_create.append(
                        ItemReporteVentaProveedor(
                            agencia=agencia,
                            reporte=reporte,
                            fecha_emision=item_data.get("fecha_emision"),
                            numero_factura=item_data.get("numero_factura", ""),
                            numero_boleto=item_data.get("numero_boleto", ""),
                            pasajero=item_data.get("pasajero", ""),
                            aerolinea=item_data.get("aerolinea", ""),
                            fecha_vuelo=item_data.get("fecha_vuelo"),
                            ruta_itinerario=item_data.get("ruta_itinerario", ""),
                            monto_fare=item_data.get("monto_fare"),
                            monto_tax=item_data.get("monto_tax"),
                            monto_subtotal=item_data.get("monto_subtotal"),
                            monto_fee=item_data.get("monto_fee"),
                            porcentaje_comision=item_data.get("porcentaje_comision"),
                            monto_comision=item_data.get("monto_comision"),
                            monto_neto_pagar=item_data.get("monto_neto_pagar"),
                            remarks=item_data.get("remarks", ""),
                        )
                    )

                if items_to_create:
                    ItemReporteVentaProveedor.objects.bulk_create(items_to_create)

                logger.info(
                    f"Reporte de proveedor {reporte.proveedor_nombre} procesado con éxito para la agencia {agencia.nombre}. "
                    f"Reporte ID: {reporte.id}, Ítems guardados: {len(items_to_create)}"
                )

                return reporte
