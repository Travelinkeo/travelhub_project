import json
import logging
import datetime
from django.utils import timezone
from core.services.gemini_client import generate_structured_data, generate_text_from_prompt
from core.models import Venta, Cliente
from core.services.migration_checker_service import MigrationCheckerService
from django.db.models import Sum, Q

logger = logging.getLogger(__name__)

class LinkeoAgentService:
    """
    Servicio de Inteligencia Artificial para Agentes de Viajes (Nivel 2).
    Permite consultas en lenguaje natural sobre ventas, clientes y requisitos.
    """
    
    def process_message(self, text: str, user_context: str = None) -> str:
        """
        Orquestador principal: Detecta intención -> Ejecuta -> Responde.
        """
        try:
            # 1. Detectar Intención
            intent_data = self._detect_intent(text)
            intent = intent_data.get('intent')
            params = intent_data.get('params', {})
            
            logger.info(f"Linkeo Intent: {intent} | Params: {params}")

            # 2. Ejecutar Acción
            if intent == 'QUERY_SALES':
                return self._handle_sales_query(params)
            
            elif intent == 'QUERY_CLIENT':
                return self._handle_client_query(params)
                
            elif intent == 'CHECK_MIGRATION':
                return self._handle_migration_check(params)
                
            elif intent == 'GENERAL':
                 # Responder con personalidad de Linkeo
                 prompt = f"Eres Linkeo, un asistente útil para agentes de viajes. Responde amablemente a: {text}"
                 return generate_text_from_prompt(prompt)
            
            else:
                return "No entendí tu solicitud. ¿Podrías ser más específico?"

        except Exception as e:
            logger.error(f"Error en LinkeoAgentService: {e}")
            return "Tuve un error procesando tu solicitud. Por favor intenta de nuevo."

    def _detect_intent(self, text: str) -> dict:
        """
        Usa Gemini para clasificar la intención y extraer parámetros estructurados.
        """
        prompt = f"""
        Actúa como un clasificador de intenciones para una agencia de viajes.
        Analiza el siguiente texto y extrae la intención y parámetros en JSON.
        
        TEXTO: "{text}"
        
        INTENCIONES POSIBLES:
        - QUERY_SALES: Consultas de ventas, montos, reservas recientes. (Params: date_range_start, date_range_end, destination, airline)
        - QUERY_CLIENT: Búsqueda de teléfonos, emails o datos de clientes. (Params: name_query)
        - CHECK_MIGRATION: Preguntas sobre visas, pasaportes o requisitos de entrada. (Params: nationality, destination)
        - GENERAL: Saludos, agradecimientos, preguntas fuera de contexto.
        
        REGLAS:
        - Fechas en formato YYYY-MM-DD. Si dice "hoy", usa {timezone.now().date()}.
        - Si dice "ayer", usa {timezone.now().date() - datetime.timedelta(days=1)}.
        - Nationalidad y Destinos en códigos ISO 3 letras si es posible, o nombre completo.
        
        RESPUESTA JSON:
        {{
            "intent": "INTENTION_NAME",
            "params": {{ ... }}
        }}
        """
        
        try:
            response = generate_structured_data(prompt)
            return json.loads(response)
        except json.JSONDecodeError:
            logger.error("Error decodificando JSON de Gemini. Fallback a GENERAL.")
            return {"intent": "GENERAL", "params": {}}

    def _handle_sales_query(self, params: dict) -> str:
        """Maneja consultas de ventas."""
        queryset = Venta.objects.all()
        
        # Filtros básicos
        start_date = params.get('date_range_start')
        if start_date:
            queryset = queryset.filter(fecha_venta__date__gte=start_date)
            
        destination = params.get('destination')
        # Nota: Filtrar por destino en Venta es complejo porque está en SegmentoVuelo.
        # Simplificación MVP: buscar en descripción general o ignorar
        
        total = queryset.count()
        monto = queryset.aggregate(Sum('total_venta'))['total_venta__sum'] or 0
        
        # Generar resumen natural con Gemini para que no suene robótico
        resumen_prompt = f"""
        Genera una respuesta corta para el agente sobre estos datos de ventas:
        - Total Ventas: {total}
        - Monto Total: ${monto}
        - Filtros aplicados: {params}
        """
        return generate_text_from_prompt(resumen_prompt)

    def _handle_client_query(self, params: dict) -> str:
        """Maneja búsqueda de clientes."""
        query = params.get('name_query')
        if not query:
            return "Necesito un nombre para buscar al cliente."
            
        clientes = Cliente.objects.filter(
            Q(nombres__icontains=query) | Q(apellidos__icontains=query) | Q(nombre_empresa__icontains=query)
        )[:3]
        
        if not clientes:
            return f"No encontré clientes con el nombre '{query}'."
            
        msg = f"🔍 Encontré estos clientes para '{query}':\n"
        for c in clientes:
            nombre = c.nombre_empresa if c.nombre_empresa else f"{c.nombres} {c.apellidos}"
            msg += f"- {nombre} | 📞 {c.telefono_principal or 'N/A'}\n"
        return msg

    def _handle_migration_check(self, params: dict) -> str:
        """Consulta requisitos migratorios."""
        nationality = params.get('nationality')
        destination = params.get('destination')
        
        if not nationality or not destination:
            return "Para consultar requisitos necesito la nacionalidad y el destino. Ej: 'Visa para ir a España siendo Chileno'."
            
        # Usamos el servicio existente
        service = MigrationCheckerService()
        result = service.quick_check(nationality, destination)
        
        emoji = "✅" if not result.visa_required else "🛂"
        return f"{emoji} **Requisitos {nationality} ➡️ {destination}**\n\n{result.summary}\n\nVisa: {'Sí' if result.visa_required else 'No'}"
