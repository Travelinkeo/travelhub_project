# core/chatbot/views.py

import logging

from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.auth_helpers import internal_auth

from .chatbot_service import chatbot

logger = logging.getLogger(__name__)


@extend_schema(
    description="Enviar un mensaje al chatbot IA 'Linkeo' y obtener respuesta.",
    request={
        "application/json": {
            "schema": {
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "Mensaje del usuario"},
                    "conversation_history": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "role": {"type": "string", "enum": ["user", "assistant"]},
                                "content": {"type": "string"},
                            },
                        },
                        "description": "Historial de conversación previo",
                    },
                },
                "required": ["message"],
            }
        }
    },
    responses={200: {"description": "Respuesta del chatbot con intención y respuestas rápidas"}},
    tags=["Chatbot"],
)
@api_view(["POST"])
@internal_auth  # CSRF exempt: secured by token-based internal_auth + IsAuthenticated
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
        user_message = request.data.get("message", "").strip()
        conversation_history = request.data.get("conversation_history", [])

        if not user_message:
            return Response(
                {"error": "El mensaje no puede estar vacío"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Procesar mensaje con el chatbot
        result = chatbot.chat(user_message, conversation_history)

        # Agregar respuestas rápidas sugeridas
        quick_replies = chatbot.get_quick_replies()

        # Extraer intención
        intent = chatbot.extract_intent(user_message)

        return Response(
            {
                "success": result["success"],
                "response": result["response"],
                "fallback": result.get("fallback", False),
                "intent": intent,
                "quick_replies": quick_replies,
                "timestamp": request.data.get("timestamp"),
            }
        )

    except Exception as e:
        logger.error(f"Error en chat_message: {e}", exc_info=True)
        return Response(
            {"error": "Error interno del servidor"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema(
    description="Obtener las respuestas rápidas sugeridas por el chatbot.",
    responses={200: {"description": "Lista de respuestas rápidas"}},
    tags=["Chatbot"],
)
@api_view(["GET"])
@internal_auth
@permission_classes([IsAuthenticated])
def get_quick_replies(request):
    """
    API para obtener respuestas rápidas sugeridas.
    """
    try:
        quick_replies = chatbot.get_quick_replies()

        return Response({"success": True, "quick_replies": quick_replies})

    except Exception as e:
        logger.error(f"Error en get_quick_replies: {e}", exc_info=True)
        return Response(
            {"error": "Error interno del servidor"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema(
    description="Verificar el estado y disponibilidad del chatbot (Gemini API, features activas).",
    responses={200: {"description": "Estado actual del chatbot con features disponibles"}},
    tags=["Chatbot"],
)
@api_view(["GET"])
@internal_auth
@permission_classes([IsAuthenticated])
def chatbot_status(request):
    """
    API para verificar el estado del chatbot.
    """
    try:
        from apps.automation.services.ai_engine import GEMINI_API_KEY

        gemini_available = bool(GEMINI_API_KEY)

        return Response(
            {
                "success": True,
                "status": "online",
                "name": "Linkeo",
                "avatar": "/static/images/linkeo-avatar.png",
                "gemini_available": gemini_available,
                "fallback_enabled": True,
                "features": {
                    "conversation_history": True,
                    "quick_replies": True,
                    "intent_detection": True,
                    "multilanguage": False,  # Por ahora solo español
                },
            }
        )

    except Exception as e:
        logger.error(f"Error en chatbot_status: {e}", exc_info=True)
        return Response(
            {"error": "Error interno del servidor"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
