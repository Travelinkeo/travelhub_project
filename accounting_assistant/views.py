import json
import logging
from datetime import date

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.gemini import generate_content  # Asumiendo servicio centralizado de Gemini

# Modelos y Servicios del Proyecto
from contabilidad.models import PlanContable

logger = logging.getLogger(__name__)

class SugerirAsientoView(APIView):
    """
    Endpoint que recibe una descripción de una transacción y sugiere
    un asiento contable de partida doble usando IA.
    """
    permission_classes = [permissions.IsAuthenticated] # Proteger el endpoint

    def post(self, request, *args, **kwargs):
        descripcion_usuario = request.data.get('descripcion')

        if not descripcion_usuario:
            return Response({"error": "El campo 'descripcion' es requerido."}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Obtener y formatear el Plan Contable
        try:
            cuentas_activas = PlanContable.objects.filter(permite_movimientos=True).order_by('codigo_cuenta')
            if not cuentas_activas.exists():
                return Response({"error": "El plan contable no está configurado o no tiene cuentas activas."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            plan_contable_texto = "\n".join(
                [f"- {c.codigo_cuenta}: {c.nombre_cuenta} (Naturaleza: {'Deudora' if c.naturaleza == 'D' else 'Acreedora'})" for c in cuentas_activas]
            )
        except Exception as e:
            logger.error(f"Error al cargar el plan contable: {e}")
            return Response({"error": "No se pudo cargar el plan contable."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 2. Construir el prompt inteligente
        prompt = f"""
        Eres un asistente contable experto especializado en agencias de viajes.
        Tu tarea es analizar una descripción de transacción y sugerir un asiento contable de partida doble,
        utilizando EXCLUSIVAMENTE las cuentas del Plan Contable proporcionado.

        **Plan de Cuentas Disponible:**
        ---
        {plan_contable_texto}
        ---

        **Descripción de la Transacción:**
        "{descripcion_usuario}"

        **Instrucciones:**
        1. Analiza la descripción para identificar las cuentas involucradas y el monto.
        2. Crea un asiento de partida doble (el total de débitos debe ser igual al total de créditos).
        3. Basa tu sugerencia en la naturaleza de las cuentas (una cuenta de gastos como 'Costo de Ventas' normally se debita, una cuenta de banco como 'Banco' normally se acredita cuando sale dinero).
        4. Genera una descripción contable concisa para el asiento.
        5. Tu respuesta DEBE ser un único objeto JSON válido, sin explicaciones, con la siguiente estructura:
        {{
            "descripcion_sugerida": "<tu descripción concisa>",
            "fecha_sugerida": "{date.today().strftime('%Y-%m-%d')}",
            "detalles": [
                {{ "cuenta_codigo": "<código de la cuenta débito>", "cuenta_nombre": "<nombre de la cuenta débito>", "tipo": "DEBIT", "monto": <monto> }},
                {{ "cuenta_codigo": "<código de la cuenta crédito>", "cuenta_nombre": "<nombre de la cuenta crédito>", "tipo": "CREDIT", "monto": <monto> }}
            ]
        }}
        """

        # 3. Llamar a Gemini y procesar la respuesta
        try:
            response_text = generate_content(prompt)
            if response_text.strip().startswith("```json"):
                response_text = response_text.strip()[7:-3].strip()
            
            suggested_entry = json.loads(response_text)

            # Validación simple de la respuesta de la IA
            if 'detalles' not in suggested_entry or len(suggested_entry['detalles']) < 2:
                raise ValueError("La IA no devolvió los detalles del asiento correctamente.")

            return Response(suggested_entry, status=status.HTTP_200_OK)

        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"No se pudo parsear o validar la sugerencia de la IA: {e}. Respuesta recibida: {response_text}")
            return Response({"error": "La IA devolvió una respuesta inválida. Inténtalo de nuevo con una descripción más clara."}, status=status.HTTP_408_REQUEST_TIMEOUT)
        except Exception as e:
            logger.error(f"Error inesperado en la llamada a Gemini: {e}")
            return Response({"error": "Ocurrió un error al comunicarse con el asistente de IA."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)