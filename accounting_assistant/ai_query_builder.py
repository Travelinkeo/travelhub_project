
import json
import logging
from typing import Any

from django.apps import apps
from django.db.models import Avg, Count, Sum

from core.gemini import generate_content

logger = logging.getLogger(__name__)

# Mapeo de agregaciones de Django para seguridad
AGGREGATION_FUNCTIONS = {
    'sum': Sum,
    'avg': Avg,
    'count': Count,
}

MODEL_SCHEMA = """
{
  "BoletoImportado": {
    "fields": ["id", "numero_boleto", "pasajero_nombre_completo", "total_a_pagar", "fecha_emision"],
    "relations": []
  },
  "Venta": {
    "fields": ["id", "localizador", "total_venta", "fecha_creacion"],
    "relations": [{"field": "pasajero", "related_model": "Pasajero"}]
  },
  "Pasajero": {
    "fields": ["id", "nombre", "apellido"],
    "relations": []
  }
}
"""

def build_query_from_natural_language(question: str) -> dict[str, Any] | None:
    """
    Convierte una pregunta en lenguaje natural en una consulta de Django ORM usando IA.

    Args:
        question: La pregunta del usuario.

    Returns:
        Un diccionario con los resultados de la consulta o None si falla.
    """
    prompt = f"""
    Eres un experto en Django ORM. Tu tarea es convertir una pregunta en lenguaje natural
    en una consulta de base de datos. Analiza la pregunta y el esquema de modelos proporcionado.
    Devuelve un objeto JSON que represente la consulta.

    El JSON debe tener la siguiente estructura:
    {{
        "model": "NombreDelModelo",
        "filters": {{ "campo__operador": "valor" }},
        "aggregation": {{ "type": "sum|avg|count", "field": "campo", "output_field_name": "nombre_resultado" }}
    }}

    - 'model': El modelo de Django a consultar (ej: "BoletoImportado").
    - 'filters': Un diccionario de filtros a aplicar. Usa los operadores de Django (ej: '__gte', '__icontains').
    - 'aggregation': (Opcional) La operación de agregación a realizar.

    Esquema de Modelos Disponibles:
    {MODEL_SCHEMA}

    Pregunta del usuario:
    ---
    {question}
    ---

    Basado en la pregunta, genera solo el objeto JSON de la consulta.
    """

    try:
        response_text = generate_content(prompt)
        query_spec = json.loads(response_text)

        model_name = query_spec.get('model')
        filters = query_spec.get('filters', {})
        aggregation = query_spec.get('aggregation')

        Model_class = apps.get_model(app_label='core', model_name=model_name)
        
        queryset = Model_class.objects.filter(**filters)

        if aggregation:
            agg_type = aggregation.get('type')
            agg_field = aggregation.get('field')
            output_field = aggregation.get('output_field_name', 'result')
            
            agg_func = AGGREGATION_FUNCTIONS.get(agg_type)
            if not agg_func:
                raise ValueError(f"Agregación no válida: {agg_type}")

            result = queryset.aggregate(**{output_field: agg_func(agg_field)})
            return result
        else:
            # Por ahora, si no hay agregación, devolvemos los primeros 10 resultados.
            return list(queryset.values()[:10])

    except Exception as e:
        logger.error(f"Error construyendo o ejecutando la consulta de IA: {e}")
        return None
