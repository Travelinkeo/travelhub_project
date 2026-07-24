import logging

from django.db import transaction

from apps.contabilidad.models import ItemReporteVentaProveedor, ReporteVentaProveedor
from apps.contabilidad.supplier_parsers import SupplierReportParserFactory
from core.middleware import agency_context

logger = logging.getLogger(__name__)


class SupplierReportProcessorService:
    """
    Servicio centralizado para procesar reportes de ventas de proveedores (PDF/.EML).
    Procesamiento Multi-Tenant por Agencia.
    """

    @classmethod
    def procesar_pdf_reporte(
        cls,
        pdf_bytes: bytes,
        filename: str,
        subject: str,
        sender_email: str,
        agencia,
    ) -> ReporteVentaProveedor | None:
        """
        Procesa un archivo PDF de reporte de proveedor y persiste los modelos
        asociados a la agencia especificada.
        """
        if not agencia:
            logger.error("No se proporcionó agencia para procesar reporte de proveedor.")
            return None

        # 1. Obtener Parser vía Factory
        parser = SupplierReportParserFactory.get_parser(
            pdf_bytes=pdf_bytes,
            filename=filename,
            subject=subject,
            sender_email=sender_email,
        )

        if not parser:
            logger.warning(
                f"No se pudo determinar el proveedor para el archivo {filename} ({sender_email})."
            )
            return None

        # 2. Parsear el PDF
        parsed_data = parser.parse()

        if not parsed_data.get("items") and parsed_data.get("monto_total_ventas") == 0:
            logger.warning(f"El reporte {filename} no arrojó ítems ni ventas válidas.")

        # 3. Guardar en Base de Datos bajo el contexto estricto de la Agencia
        with agency_context(agencia):
            with transaction.atomic():
                reporte = ReporteVentaProveedor.objects.create(
                    agencia=agencia,
                    proveedor_nombre=parsed_data.get("proveedor_nombre", "DESCONOCIDO"),
                    codigo_agencia_proveedor=parsed_data.get("codigo_agencia_proveedor", ""),
                    asunto_correo=subject[:255],
                    emisor_correo=sender_email[:150],
                    fecha_reporte_desde=parsed_data.get("fecha_reporte_desde"),
                    fecha_reporte_hasta=parsed_data.get("fecha_reporte_hasta"),
                    nombre_archivo_adjunto=filename[:255],
                    saldo_anterior=parsed_data.get("saldo_anterior", 0),
                    monto_total_ventas=parsed_data.get("monto_total_ventas", 0),
                    saldo_final=parsed_data.get("saldo_final", 0),
                    estado=ReporteVentaProveedor.EstadoReporte.PROCESADO,
                    raw_data={
                        "total_items": len(parsed_data.get("items", [])),
                        "filename": filename,
                    },
                )

                items_a_crear = []
                for item_data in parsed_data.get("items", []):
                    items_a_crear.append(
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
                            monto_fare=item_data.get("monto_fare", 0),
                            monto_tax=item_data.get("monto_tax", 0),
                            monto_subtotal=item_data.get("monto_subtotal", 0),
                            monto_fee=item_data.get("monto_fee", 0),
                            porcentaje_comision=item_data.get("porcentaje_comision", 0),
                            monto_comision=item_data.get("monto_comision", 0),
                            monto_neto_pagar=item_data.get("monto_neto_pagar", 0),
                            remarks=item_data.get("remarks", ""),
                        )
                    )

                if items_a_crear:
                    ItemReporteVentaProveedor.objects.bulk_create(items_a_crear)

                logger.info(
                    f"✅ Reporte de Proveedor {reporte.proveedor_nombre} procesado con éxito "
                    f"({len(items_a_crear)} boletos/ítems, Total ${reporte.monto_total_ventas}) "
                    f"para la agencia {agencia.nombre}."
                )

                return reporte
