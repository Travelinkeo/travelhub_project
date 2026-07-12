import logging
from datetime import timedelta

from django.db.models import Q, Sum
from django.utils import timezone

from apps.finance.models.core_finance import Factura

logger = logging.getLogger(__name__)


def _get_genai():
    from google import genai

    return genai


class CollectionAIService:
    """
    Servicio de Inteligencia Contable para la gestión proactiva de cobranzas y cashflow.
    """

    def __init__(self, agencia=None):
        self.agencia = agencia
        from apps.automation.services.ai_engine import get_gemini_api_key

        api_key = get_gemini_api_key(self.agencia)
        genai = _get_genai()
        self.client = genai.Client(api_key=api_key) if api_key else None
        self.model_name = "gemini-1.5-flash"

    def get_pending_portfolio(self, days_threshold=0):
        """
        Obtiene las facturas pendientes de cobro.
        days_threshold > 0: Facturas que vencen en los próximos X días.
        days_threshold < 0: Facturas ya vencidas hace X días.
        """
        query = Q(estado__in=["EMI", "PAR"], saldo_pendiente__gt=0)

        if self.agencia:
            query &= Q(agencia=self.agencia)

        if days_threshold > 0:
            # Por vencer en los próximos X días
            fecha_limite = timezone.now().date() + timedelta(days=days_threshold)
            query &= Q(
                fecha_vencimiento__lte=fecha_limite, fecha_vencimiento__gte=timezone.now().date()
            )
        elif days_threshold < 0:
            # Ya vencidas
            query &= Q(fecha_vencimiento__lt=timezone.now().date())

        return Factura.objects.filter(query).select_related("cliente", "moneda", "agencia")

    def generate_collection_reminder(self, factura_id):
        """
        Genera un recordatorio de cobro personalizado usando IA.
        """
        if not self.client:
            logger.error("Gemini client not configured.")
            return None
        try:
            factura = Factura.objects.select_related("cliente", "agencia").get(pk=factura_id)
            cliente = factura.cliente
            dias_retraso = 0
            if factura.fecha_vencimiento:
                dias_retraso = (timezone.now().date() - factura.fecha_vencimiento).days

            # Contexto para la IA
            prompt = f"""
            Actúa como el asistente contable de la agencia de viajes "{factura.agencia.nombre if factura.agencia else "TravelHub"}".
            Tu objetivo es redactar un mensaje de recordatorio de pago para el cliente {cliente.get_nombre_completo() if cliente else "Estimado Cliente"}.

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
        proximos_dias = timezone.now().date() + timedelta(days=days)

        query = Q(estado__in=["EMI", "PAR"], saldo_pendiente__gt=0)
        if self.agencia:
            query &= Q(agencia=self.agencia)

        proyeccion = (
            Factura.objects.filter(query, fecha_vencimiento__lte=proximos_dias)
            .values("fecha_vencimiento", "moneda__codigo_iso")
            .annotate(total_esperado=Sum("saldo_pendiente"))
            .order_by("fecha_vencimiento")
        )

        return list(proyeccion)

    def process_overdue_accounts(self):
        """
        Procesa todas las facturas vencidas: genera recordatorios IA y envía por WhatsApp.
        Retorna lista de resultados por factura.
        """
        from apps.communications.services.whatsapp_unified import enviar_whatsapp

        facturas_vencidas = self.get_pending_portfolio(days_threshold=-1)
        resultados = []

        for factura in facturas_vencidas:
            resultado = {"factura": factura.numero_factura, "success": False, "error": None}
            try:
                cliente = factura.cliente
                if not cliente or not cliente.telefono_principal:
                    resultado["error"] = "Sin teléfono configurado"
                    resultados.append(resultado)
                    continue

                mensaje = self.generate_collection_reminder(factura.pk)
                if not mensaje:
                    resultado["error"] = "Error generando mensaje IA"
                    resultados.append(resultado)
                    continue

                agencia = getattr(factura, "agencia", None)
                enviado = enviar_whatsapp(cliente.telefono_principal, mensaje, agencia=agencia)
                resultado["success"] = enviado
                if not enviado:
                    resultado["error"] = "Error en envío WhatsApp"

            except Exception as e:
                resultado["error"] = str(e)

            resultados.append(resultado)

        return resultados
