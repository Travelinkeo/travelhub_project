
import logging
from datetime import datetime, timedelta
import google.generativeai as genai
from django.conf import settings
from django.db.models import Sum, Count
from django.utils import timezone

from apps.bookings.models import Venta
from apps.crm.models import Cliente
from core.models_catalogos import Moneda

logger = logging.getLogger(__name__)

class AIAccountingService:
    """
    Servicio de Asistente Financiero con IA (Gemini Pro).
    Implementa Function Calling seguro con aislamiento por Agencia.
    """
    
    def __init__(self, agencia):
        self.agencia = agencia
        self.api_key = settings.GEMINI_API_KEY
        genai.configure(api_key=self.api_key)
        
        # Definición de Herramientas permitidas (SaaS Safe)
        self.tools = [
            self.get_ventas_periodo,
            self.get_top_clientes,
            self.get_deuda_clientes
        ]
        
        self.model = genai.GenerativeModel(
            model_name='gemini-1.5-pro-latest', # O gemini-pro según disponibilidad
            tools=self.tools,
            system_instruction=f"""
            Eres un experto analista financiero para la agencia de viajes '{agencia.nombre}'.
            Tu objetivo es responder preguntas sobre ventas, deudas y rendimiento usando las herramientas disponibles.
            SIEMPRE responde en Español y formatea los montos monetarios claramente.
            Si no tienes datos, dilo honestamente.
            """
        )
        self.chat = self.model.start_chat(enable_automatic_function_calling=True)

    def ask(self, user_message):
        """Envía el mensaje al modelo y retorna la respuesta procesada."""
        try:
            response = self.chat.send_message(user_message)
            return response.text
        except Exception as e:
            logger.error(f"Error en AI Chat: {e}")
            return "Lo siento, tuve un problema procesando tu consulta financiera."

    # --- TOOLS (SaaS Secured) ---
    
    def get_ventas_periodo(self, dias: int = 30):
        """
        Obtiene el total de ventas de los últimos N días.
        Args:
            dias: Número de días hacia atrás a consultar (default 30).
        """
        fecha_inicio = timezone.now() - timedelta(days=dias)
        ventas = Venta.objects.filter(
            agencia=self.agencia, 
            fecha_venta__gte=fecha_inicio
        )
        
        total = ventas.aggregate(total=Sum('total_venta'))['total'] or 0
        count = ventas.count()
        
        return {
            "periodo_dias": dias,
            "total_ventas": float(total),
            "cantidad_operaciones": count,
            "moneda": "USD" # Asumiendo base USD por simplicidad, idealmente por moneda
        }

    def get_top_clientes(self, limit: int = 5):
        """
        Devuelve los clientes con mayor volumen de compra histórico.
        Args:
            limit: Cantidad de clientes a mostrar.
        """
        top_clientes = Venta.objects.filter(agencia=self.agencia).values(
            'cliente__nombres', 'cliente__apellidos'
        ).annotate(
            total_comprado=Sum('total_venta'),
            operaciones=Count('id_venta')
        ).order_by('-total_comprado')[:limit]
        
        return [
            {
                "cliente": f"{c['cliente__nombres']} {c['cliente__apellidos']}",
                "total": float(c['total_comprado'] or 0),
                "operaciones": c['operaciones']
            }
            for c in top_clientes
        ]

    def get_deuda_clientes(self):
        """
        Lista los clientes que tienen Facturas pendientes de pago (saldo > 0).
        """
        # Nota: Importamos Factura aquí para evitar ciclos si fuera necesario, 
        # pero como están en apps.finance.models diferente, no debería.
        from apps.finance.models import Factura
        
        facturas_pendientes = Factura.objects.filter(
            agencia=self.agencia,
            saldo_pendiente__gt=0,
            estado__in=['EMI', 'PAR', 'VEN']
        ).values(
            'cliente__nombres', 'cliente__apellidos'
        ).annotate(
            deuda_total=Sum('saldo_pendiente'),
            cantidad_facturas=Count('id_factura')
        ).order_by('-deuda_total')[:10]
        
        return [
            {
                "cliente": f"{c['cliente__nombres']} {c['cliente__apellidos']}",
                "deuda_pendiente": float(c['deuda_total'] or 0),
                "facturas_abiertas": c['cantidad_facturas']
            }
            for c in facturas_pendientes
        ]
