import json
import logging
from datetime import date
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from core.services.ai_engine import ai_engine
from apps.contabilidad.models import PlanContable
from .ai_query_builder import build_query_from_natural_language

logger = logging.getLogger(__name__)

class AssistantChatView(APIView):
    """
    Endpoint de chat conversacional con acceso a datos financieros.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user_message = request.data.get('message')
        if not user_message:
            return Response({"error": "El mensaje es requerido."}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Intentar extraer datos de la BD
        data_context = build_query_from_natural_language(user_message)
        
        # 2. Generar respuesta final con Gemini
        prompt = f"""
        Actúa como el Asistente Contable de TravelHub. 
        Responde a la consulta del usuario basándote en este contexto de datos reales extraídos de la base de datos:
        
        CONTEXTO DE DATOS:
        {json.dumps(data_context, indent=2) if data_context else "No se encontraron datos específicos para esta consulta."}
        
        MENSAJE DEL USUARIO:
        {user_message}
        
        Instrucciones:
        - Sé conciso y profesional.
        - Si encontraste datos, cítalos (ej: 'El saldo del Banco Mercantil es de 1,500 USD').
        - Si no hay datos, explica amablemente que no tienes acceso a esa información específica.
        """
        
        res = ai_engine.call_gemini(prompt)
        return Response({
            "response": res.get("text", "Lo siento, tuve un problema procesando tu mensaje."),
            "data_found": data_context is not None
        }, status=status.HTTP_200_OK)

class SugerirAsientoView(APIView):
    """
    Endpoint que recibe una descripción y sugiere un asiento contable.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        descripcion_usuario = request.data.get('descripcion')
        if not descripcion_usuario:
            return Response({"error": "Descripción requerida."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            cuentas = PlanContable.objects.filter(permite_movimientos=True).order_by('codigo_cuenta')
            plan_texto = "\n".join([f"- {c.codigo_cuenta}: {c.nombre_cuenta}" for c in cuentas])
            
            prompt = f"Sugiere un asiento para: {descripcion_usuario}. PLAN DE CUENTAS:\n{plan_texto}"
            
            from pydantic import BaseModel
            class AsientoDetalle(BaseModel):
                cuenta_codigo: str
                cuenta_nombre: str
                tipo: str
                monto: float

            class AsientoSugerido(BaseModel):
                descripcion_sugerida: str
                fecha_sugerida: str
                detalles: list[AsientoDetalle]

            res = ai_engine.call_gemini(
                prompt=prompt,
                response_schema=AsientoSugerido,
                system_instruction="Eres un experto contable. Genera asientos de partida doble."
            )
            
            return Response(res, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error sugiriendo asiento: {e}")
            return Response({"error": "Error interno al generar sugerencia."}, status=500)
