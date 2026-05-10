import logging
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum, Q
from apps.finance.models.core_finance import Factura
from core.services.ai_parser_service import AIParserService
from google import genai
from django.conf import settings

logger = logging.getLogger(__name__)

class CollectionAIService:
    """
    Servicio de Inteligencia Contable para la gestión proactiva de cobranzas y cashflow.
    """

    def __init__(self, agencia=None):
        self.agencia = agencia
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model_name = 'gemini-2.0-flash'

    def get_pending_portfolio(self, days_threshold=0):
        """
        Obtiene las facturas pendientes de cobro.
        days_threshold > 0: Facturas que vencen en los próximos X días.
        days_threshold < 0: Facturas ya vencidas hace X días.
        """
        query = Q(estado__in=['EMI', 'PAR'], saldo_pendiente__gt=0)
        
        if self.agencia:
            query &= Q(agencia=self.agencia)
            
        if days_threshold > 0:
            # Por vencer en los próximos X días
            fecha_limite = timezone.now().date() + timedelta(days=days_threshold)
            query &= Q(fecha_vencimiento__lte=fecha_limite, fecha_vencimiento__gte=timezone.now().date())
        elif days_threshold < 0:
            # Ya vencidas
            query &= Q(fecha_vencimiento__lt=timezone.now().date())
            
        return Factura.objects.filter(query).select_related('cliente', 'moneda', 'agencia')

    def generate_collection_reminder(self, factura_id):
        """
        Genera un recordatorio de cobro personalizado usando IA.
        """
        try:
            factura = Factura.objects.select_related('cliente', 'agencia').get(pk=factura_id)
            cliente = factura.cliente
            dias_retraso = 0
            if factura.fecha_vencimiento:
                dias_retraso = (timezone.now().date() - factura.fecha_vencimiento).days

            # Contexto para la IA
            prompt = f"""
            Actúa como el asistente contable de la agencia de viajes "{factura.agencia.nombre if factura.agencia else 'TravelHub'}".
            Tu objetivo es redactar un mensaje de recordatorio de pago para el cliente {cliente.get_nombre_completo() if cliente else 'Estimado Cliente'}.
            
            DATOS DE LA DEUDA:
            - Factura Nro: {factura.numero_factura}
            - Monto Pendiente: {factura.saldo_pendiente} {factura.moneda.codigo_iso}
            - Fecha de Vencimiento: {factura.fecha_vencimiento}
            - Días de retraso: {dias_retraso if dias_retraso > 0 else 0}
            
            INSTRUCCIONES:
            - Tono: {"Cordial pero firme" if dias_retraso > 5 else "Amigable y servicial"}.
            - Formato: WhatsApp (máximo 150 palabras).
            - Incluye un llamado a la acción claro.
            - Usa emojis de forma profesional.
            - Menciona que si ya realizó el pago, ignore el mensaje.
            
            Escribe solo el cuerpo del mensaje.
            """

            response = self.client.models.generate_content(model=self.model_name, contents=prompt)
            return response.text.strip()

        except Exception as e:
            logger.error(f"Error generando recordatorio IA para factura {factura_id}: {e}")
            return None

    def get_cashflow_projection(self, days=30):
        """
        Proyecta la entrada de dinero esperada en los próximos X días.
        """
        hace_un_mes = timezone.now().date() - timedelta(days=30)
        proximos_dias = timezone.now().date() + timedelta(days=days)
        
        query = Q(estado__in=['EMI', 'PAR'], saldo_pendiente__gt=0)
        if self.agencia:
            query &= Q(agencia=self.agencia)
            
        proyeccion = Factura.objects.filter(
            query,
            fecha_vencimiento__lte=proximos_dias
        ).values('fecha_vencimiento', 'moneda__codigo_iso').annotate(
            total_esperado=Sum('saldo_pendiente')
        ).order_by('fecha_vencimiento')

        return list(proyeccion)
