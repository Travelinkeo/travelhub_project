# core/chatbot/views.py

import logging
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt

from .chatbot_service import chatbot

logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@csrf_exempt
def chat_message(request):
    """
    API para enviar mensajes al chatbot.
    
    POST /api/chatbot/message/
    {
        "message": "Hola, necesito información sobre viajes a Miami",
        "conversation_history": [
            {"role": "user", "content": "mensaje anterior"},
            {"role": "assistant", "content": "respuesta anterior"}
        ]
    }
    """
    try:
        user_message = request.data.get('message', '').strip()
        conversation_history = request.data.get('conversation_history', [])
        
        if not user_message:
            return Response(
                {'error': 'El mensaje no puede estar vacío'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Procesar mensaje con el chatbot
        result = chatbot.chat(user_message, conversation_history)
        
        # Agregar respuestas rápidas sugeridas
        quick_replies = chatbot.get_quick_replies()
        
        # Extraer intención
        intent = chatbot.extract_intent(user_message)
        
        return Response({
            'success': result['success'],
            'response': result['response'],
            'fallback': result.get('fallback', False),
            'intent': intent,
            'quick_replies': quick_replies,
            'timestamp': request.data.get('timestamp')
        })
        
    except Exception as e:
        logger.error(f"Error en chat_message: {e}", exc_info=True)
        return Response(
            {'error': 'Error interno del servidor'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_quick_replies(request):
    """
    API para obtener respuestas rápidas sugeridas.
    
    GET /api/chatbot/quick-replies/
    """
    try:
        quick_replies = chatbot.get_quick_replies()
        
        return Response({
            'success': True,
            'quick_replies': quick_replies
        })
        
    except Exception as e:
        logger.error(f"Error en get_quick_replies: {e}", exc_info=True)
        return Response(
            {'error': 'Error interno del servidor'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def chatbot_status(request):
    """
    API para verificar el estado del chatbot.
    
    GET /api/chatbot/status/
    """
    try:
        from core.services.gemini_client import GEMINI_API_KEY
        
        gemini_available = bool(GEMINI_API_KEY)
        
        return Response({
            'success': True,
            'status': 'online',
            'name': 'Linkeo',
            'avatar': '/static/images/linkeo-avatar.png',
            'gemini_available': gemini_available,
            'fallback_enabled': True,
            'features': {
                'conversation_history': True,
                'quick_replies': True,
                'intent_detection': True,
                'multilanguage': False  # Por ahora solo español
            }
        })
        
    except Exception as e:
        logger.error(f"Error en chatbot_status: {e}", exc_info=True)
        return Response(
            {'error': 'Error interno del servidor'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )