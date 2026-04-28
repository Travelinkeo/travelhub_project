import json
import logging
from typing import Any, Dict, Optional
from django.apps import apps
from django.db.models import Avg, Count, Sum
from core.services.ai_engine import ai_engine
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

AGGREGATION_FUNCTIONS = {
    'sum': Sum,
    'avg': Avg,
    'count': Count,
}

MODEL_SCHEMA = {
    "BoletoImportado": {
        "app": "bookings",
        "fields": ["id", "numero_boleto", "pasajero_nombre_completo", "total_boleto", "fecha_emision", "total_moneda"],
    },
    "Venta": {
        "app": "core",
        "fields": ["id", "localizador", "total_venta", "fecha_creacion", "estado_vuelo"],
    },
    "AsientoContable": {
        "app": "contabilidad",
        "fields": ["id_asiento", "numero_asiento", "fecha_contable", "total_debe", "total_haber", "descripcion_general"],
    },
    "PlanContable": {
        "app": "contabilidad",
        "fields": ["id_cuenta", "codigo_cuenta", "nombre_cuenta", "tipo_cuenta", "naturaleza"],
    },
    "DetalleAsiento": {
        "app": "contabilidad",
        "fields": ["debe", "haber", "descripcion_linea"],
        "relations": ["asiento", "cuenta_contable"]
    }
}

class QuerySpec(BaseModel):
    model: str = Field(description="Nombre del modelo (ej: AsientoContable)")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Filtros Django (ej: {'fecha_contable__year': 2024})")
    aggregation: Optional[Dict[str, Any]] = Field(default=None, description="Agregación: {'type': 'sum', 'field': 'total_debe'}")

def build_query_from_natural_language(question: str) -> Optional[Dict[str, Any]]:
    """
    Traduce lenguaje natural a resultados de consulta ORM.
    """
    prompt = f"""
    Genera una consulta Django ORM para la siguiente pregunta: "{question}"
    
    ESQUEMA DISPONIBLE:
    {json.dumps(MODEL_SCHEMA, indent=2)}
    
    Reglas:
    1. Usa filtros exactos de Django.
    2. Si preguntan por 'Bancos', filtra PlanContable por tipo_cuenta='AC' o nombre_cuenta icontains 'Banco'.
    3. Si preguntan por saldos, usa sum en DetalleAsiento o AsientoContable.
    """
    
    try:
        res = ai_engine.call_gemini(
            prompt=prompt,
            response_schema=QuerySpec
        )
        
        if "error" in res:
            return None
            
        model_name = res.get('model')
        if model_name not in MODEL_SCHEMA:
            return None
            
        model_info = MODEL_SCHEMA[model_name]
        ModelClass = apps.get_model(app_label=model_info['app'], model_name=model_name)
        
        queryset = ModelClass.objects.filter(**res.get('filters', {}))
        
        aggregation = res.get('aggregation')
        if aggregation:
            agg_type = aggregation.get('type')
            agg_field = aggregation.get('field')
            agg_func = AGGREGATION_FUNCTIONS.get(agg_type)
            if agg_func:
                return queryset.aggregate(resultado=agg_func(agg_field))
        
        # Devolver una muestra de datos si no hay agregación
        return list(queryset.values(*model_info['fields'])[:5])

    except Exception as e:
        logger.error(f"Error en AI Query Builder: {e}")
        return None
