import logging
import json
from decimal import Decimal
from django.db import transaction, models
from django.utils import timezone
from apps.finance.models import ReporteProveedor, ItemReporte, DiferenciaFinanciera
from django.apps import apps
from apps.finance.services.smart_processor import SmartReportProcessor

logger = logging.getLogger(__name__)

class ReconciliationService:
    """
    Servicio SaaS para procesar reportes financieros y conciliarlos con los boletos.
    Orquestra el parsing IA, el matching por PNR/Ticket y el registro de discrepancias.
    """

    @classmethod
    @transaction.atomic
    def process_report(cls, report_id: int):
        report = ReporteProveedor.objects.select_related('agencia', 'proveedor').get(pk=report_id)
        
        try:
            report.estado = 'PRO' # Marcar como procesando (custom state logic)
            # 1. Parsing Inteligente
            items_data = SmartReportProcessor.parse(report.archivo.path)
            report.total_registros = len(items_data)
            
            # Limpiar items previos para evitar duplicados en re-procesamiento
            report.items.all().delete()

            # 2. Procesamiento de Matches
            for data in items_data:
                cls._process_item(report, data)
            
            # 3. Consolidación de Resultados
            report.total_con_diferencia = report.items.filter(estado='DIS').count()
            report.estado = ReporteProveedor.EstadoReporte.PROCESADO
            report.save()
            
            logger.info(f"Reporte {report_id} conciliado: {report.total_registros} items, {report.total_con_diferencia} discrepancias.")
            return True
        except Exception as e:
            logger.error(f"Error procesando reporte {report_id}: {e}")
            report.estado = ReporteProveedor.EstadoReporte.ERROR
            report.notas = f"Error en procesamiento: {str(e)}"
            report.save()
            raise

    @classmethod
    def _process_item(cls, report: ReporteProveedor, data: dict):
        BoletoImportado = apps.get_model('bookings', 'BoletoImportado')
        
        num_boleto = data.get('numero_boleto')
        monto_externo = data.get('monto_total') or Decimal(0)
        
        # BÚSQUEDA ROBUSTA (Aislamiento por Agencia)
        # Probamos match por número completo, luego por los últimos 10 dígitos (standard IATA)
        boleto_interno = BoletoImportado.objects.filter(
            agencia=report.agencia
        ).filter(
            models.Q(numero_boleto=num_boleto) | 
            models.Q(numero_boleto__endswith=str(num_boleto)[-10:])
        ).first() if num_boleto else None

        item_reporte = ItemReporte.objects.create(
            reporte=report,
            numero_boleto=num_boleto or "S/N",
            pnr=data.get('pnr', ''),
            pasajero=data.get('pasajero', 'Desconocido'),
            monto_total_proveedor=monto_externo,
            tax_proveedor=data.get('tax', Decimal(0)),
            comision_proveedor=data.get('comision', Decimal(0)),
            fecha_emision=cls._parse_date(data.get('fecha_emision')),
            boleto_interno=boleto_interno
        )

        if not boleto_interno:
            item_reporte.estado = ItemReporte.EstadoConciliacion.MISSING_INTERNAL
            item_reporte.save()
            return

        # COMPARACIÓN DE MONTOS
        monto_interno = Decimal(str(boleto_interno.total_boleto or 0))
        item_reporte.monto_sistema = monto_interno
        
        # Tolerancia de 0.10 para diferencias de redondeo
        if abs(monto_interno - monto_externo) > Decimal('0.10'):
            item_reporte.estado = ItemReporte.EstadoConciliacion.DISCREPANCY
            DiferenciaFinanciera.objects.create(
                item_reporte=item_reporte,
                campo_discrepancia='monto_total',
                valor_sistema=monto_interno,
                valor_proveedor=monto_externo,
                diferencia=monto_externo - monto_interno
            )
        else:
            item_reporte.estado = ItemReporte.EstadoConciliacion.MATCH
            item_reporte.fecha_conciliacion = timezone.now()
        
        item_reporte.save()

    @staticmethod
    def _parse_date(date_val):
        if not date_val: return None
        # Aquí se podría mejorar con dateutil.parser pero mantenemos simple por ahora
        return timezone.now().date() # Placeholder or simple convert
