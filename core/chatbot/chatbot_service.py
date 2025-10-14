# core/chatbot/chatbot_service.py

import logging
from typing import Dict, List, Optional
from django.conf import settings
from core.services.gemini_client import generate_text_from_prompt
from .knowledge_base import get_knowledge_context

logger = logging.getLogger(__name__)

class TravelHubChatbot:
    """
    Chatbot inteligente para TravelHub usando Gemini AI.
    Maneja consultas de clientes sobre viajes, reservas y servicios.
    """
    
    def __init__(self):
        self.context_history = []
        self.max_history = 10
        
    def get_system_prompt(self) -> str:
        """Prompt del sistema que define el comportamiento del chatbot."""
        knowledge = get_knowledge_context()
        
        return f"""Eres Linkeo, el asistente virtual de TravelHub desarrollado por Linkeo Tech.

Tu nombre es Linkeo y eres amigable, profesional y servicial.

CONOCIMIENTO DEL SISTEMA:
{knowledge}

Tu rol es ayudar con:
- Explicar funcionalidades de TravelHub
- Guiar en el uso del sistema
- Información sobre destinos turísticos
- Consultas generales sobre servicios
- Requisitos de viaje
- Conectar con agentes humanos cuando sea necesario

Características de tu personalidad:
- Amable, profesional y servicial
- Respuestas concisas pero completas
- Usa lenguaje claro y accesible
- Conoces TODO el sistema TravelHub
- Si no sabes algo específico, ofrece contactar a un agente humano
- Siempre termina preguntando si necesita más ayuda

IMPORTANTE:
- NO inventes información sobre precios o disponibilidad
- NO confirmes reservas (solo un agente humano puede hacerlo)
- Si te preguntan por algo específico de una reserva, pide el localizador
- Usa tu conocimiento del sistema para dar respuestas precisas
- Responde SIEMPRE en español
"""

    def build_conversation_context(self, user_message: str, history: List[Dict] = None) -> str:
        """Construye el contexto de la conversación para enviar a Gemini."""
        context = self.get_system_prompt() + "\n\n"
        
        # Agregar historial si existe
        if history:
            context += "Historial de conversación:\n"
            for msg in history[-5:]:  # Últimos 5 mensajes
                role = msg.get('role', 'user')
                content = msg.get('content', '')
                context += f"{role.upper()}: {content}\n"
            context += "\n"
        
        context += f"USUARIO: {user_message}\nASISTENTE:"
        return context

    def chat(self, user_message: str, conversation_history: List[Dict] = None) -> Dict:
        """
        Procesa un mensaje del usuario y devuelve la respuesta del chatbot.
        
        Args:
            user_message: Mensaje del usuario
            conversation_history: Historial de la conversación (opcional)
            
        Returns:
            Dict con 'response', 'success' y opcionalmente 'error'
        """
        try:
            # Construir contexto
            prompt = self.build_conversation_context(user_message, conversation_history)
            
            # Generar respuesta con Gemini
            response_text = generate_text_from_prompt(prompt)
            
            # Verificar si hubo error
            if response_text.startswith("Error"):
                logger.error(f"Error en Gemini: {response_text}")
                return {
                    'success': False,
                    'response': self.get_fallback_response(user_message),
                    'error': response_text,
                    'fallback': True
                }
            
            return {
                'success': True,
                'response': response_text.strip(),
                'fallback': False
            }
            
        except Exception as e:
            logger.error(f"Error en chatbot: {e}", exc_info=True)
            return {
                'success': False,
                'response': self.get_fallback_response(user_message),
                'error': str(e),
                'fallback': True
            }

    def get_fallback_response(self, user_message: str) -> str:
        """
        Respuesta de fallback cuando Gemini no está disponible.
        Usa reglas simples basadas en palabras clave.
        """
        message_lower = user_message.lower()
        
        # Saludos
        if any(word in message_lower for word in ['hola', 'buenos', 'buenas', 'saludos']):
            return ("¡Hola! Soy Linkeo, tu asistente virtual de TravelHub. Estoy aquí para ayudarte con información sobre "
                   "viajes, destinos y servicios. ¿En qué puedo asistirte hoy?")
        
        # Precios/Cotizaciones
        if any(word in message_lower for word in ['precio', 'costo', 'cotiza', 'cuanto']):
            return ("Para obtener una cotización personalizada, por favor contáctanos directamente. "
                   "Nuestros agentes te ayudarán con los mejores precios según tu destino y fechas. "
                   "¿Te gustaría que un agente te contacte?")
        
        # Reservas
        if any(word in message_lower for word in ['reserva', 'reservar', 'boleto', 'vuelo']):
            return ("Para realizar una reserva, necesitamos algunos datos. Un agente puede ayudarte "
                   "con el proceso completo. ¿Tienes un destino en mente?")
        
        # Documentos
        if any(word in message_lower for word in ['pasaporte', 'visa', 'documento', 'requisito']):
            return ("Los requisitos de documentación varían según el destino. Te recomiendo consultar "
                   "con nuestros agentes para información actualizada sobre tu destino específico. "
                   "¿A dónde planeas viajar?")
        
        # Hoteles
        if any(word in message_lower for word in ['hotel', 'hospedaje', 'alojamiento']):
            return ("Ofrecemos una amplia selección de hoteles en diversos destinos. Para recomendaciones "
                   "personalizadas según tu presupuesto y preferencias, un agente puede asesorarte mejor. "
                   "¿Qué tipo de alojamiento buscas?")
        
        # Paquetes
        if any(word in message_lower for word in ['paquete', 'tour', 'excursion']):
            return ("Tenemos paquetes turísticos para diversos destinos. Para ver opciones disponibles "
                   "y armar un paquete a tu medida, te invito a contactar con nuestros agentes. "
                   "¿Qué destino te interesa?")
        
        # Agradecimientos
        if any(word in message_lower for word in ['gracias', 'thank']):
            return "¡De nada! Estoy aquí para ayudarte. ¿Hay algo más en lo que pueda asistirte?"
        
        # Despedidas
        if any(word in message_lower for word in ['adios', 'chao', 'hasta luego', 'bye']):
            return "¡Hasta pronto! Que tengas un excelente día. Estamos aquí cuando nos necesites."
        
        # Respuesta genérica
        return ("Gracias por tu consulta. Para brindarte la mejor atención, te recomiendo contactar "
               "directamente con uno de nuestros agentes. Ellos podrán ayudarte de manera personalizada. "
               "¿Te gustaría que te contactemos?")

    def get_quick_replies(self, context: str = None) -> List[str]:
        """Genera respuestas rápidas sugeridas basadas en el contexto."""
        default_replies = [
            "¿Cuáles son los destinos más populares?",
            "Necesito información sobre documentos",
            "Quiero cotizar un viaje",
            "¿Ofrecen paquetes turísticos?",
            "Hablar con un agente"
        ]
        
        # TODO: Personalizar según el contexto de la conversación
        return default_replies

    def extract_intent(self, user_message: str) -> str:
        """Extrae la intención del mensaje del usuario."""
        message_lower = user_message.lower()
        
        intents = {
            'greeting': ['hola', 'buenos', 'buenas', 'saludos'],
            'pricing': ['precio', 'costo', 'cotiza', 'cuanto'],
            'booking': ['reserva', 'reservar', 'boleto', 'vuelo'],
            'documents': ['pasaporte', 'visa', 'documento', 'requisito'],
            'hotels': ['hotel', 'hospedaje', 'alojamiento'],
            'packages': ['paquete', 'tour', 'excursion'],
            'contact': ['contacto', 'agente', 'hablar', 'llamar'],
            'farewell': ['adios', 'chao', 'hasta luego', 'bye']
        }
        
        for intent, keywords in intents.items():
            if any(keyword in message_lower for keyword in keywords):
                return intent
        
        return 'general'


# Instancia global del chatbot
chatbot = TravelHubChatbot()