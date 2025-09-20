import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

# Asumimos que el cliente de Gemini está configurado en el proyecto
from core.gemini import get_gemini_model

from . import tools

# Importamos las definiciones y las implementaciones de nuestras herramientas
from .tool_definitions import travel_tools

logger = logging.getLogger(__name__)

class ChatbotConverseView(APIView):
    """
    Endpoint principal para interactuar con el chatbot de TravelHub.
    """
    def post(self, request, *args, **kwargs):
        user_message = request.data.get('message')
        # El historial es clave para mantener el contexto de la conversación
        conversation_history = request.data.get('history', [])

        if not user_message:
            return Response({"error": "El mensaje no puede estar vacío."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            model = get_gemini_model(tools=travel_tools)
            
            # Adjuntamos el nuevo mensaje del usuario al historial
            conversation_history.append({'role': 'user', 'parts': [{'text': user_message}]})
            
            # Iniciamos la sesión de chat con el historial
            chat = model.start_chat(history=conversation_history)
            
            # Enviamos el mensaje a Gemini (ya está en el historial)
            response = chat.send_message(conversation_history[-1])
            
            # Verificamos si Gemini quiere usar una herramienta
            function_call = response.candidates[0].content.parts[0].function_call
            
            if function_call:
                # Gemini quiere ejecutar una función
                function_name = function_call.name
                function_args = dict(function_call.args.items())
                
                logger.info(f"Gemini solicita llamar a la función: {function_name} con args: {function_args}")

                # Buscamos y ejecutamos la función correspondiente en nuestro módulo de herramientas
                tool_function = getattr(tools, function_name, None)
                
                if not tool_function:
                    raise ValueError(f"Función '{function_name}' no encontrada.")

                # Ejecutamos la función con los argumentos proporcionados por Gemini
                function_response = tool_function(**function_args)
                
                logger.info(f"Resultado de la función: {function_response}")

                # Enviamos el resultado de la función de vuelta a Gemini
                response = chat.send_message(
                    [{'function_response': {
                        'name': function_name,
                        'response': function_response
                    }}]
                )

            # La respuesta final de Gemini (sea directa o después de la función)
            final_reply = response.candidates[0].content.parts[0].text
            
            # Actualizamos el historial con la respuesta del modelo
            conversation_history.append({'role': 'model', 'parts': [{'text': final_reply}]})

            return Response({
                "reply": final_reply,
                "history": conversation_history # Devolvemos el historial actualizado
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error en la conversación con el chatbot: {e}")
            return Response({"error": "Ocurrió un error inesperado."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
