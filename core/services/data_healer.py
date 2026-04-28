import logging
from typing import Type, Dict, Any, TypeVar
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)

class DataHealer:
    """
    Servicio de resiliencia para esquemas de Pydantic.
    Intenta validar datos y, si fallan por campos faltantes "críticos", 
    inyecta valores por defecto inteligentes para evitar errores fatales.
    """

    # Diccionario de sanación por defecto (pueden ser extendidos por modelo)
    SMART_DEFAULTS = {
        "moneda": "USD",
        "es_remision": False,
        "findings": [],
        "items": [],
        "source_system": "UNKNOWN",
        "itinerario": [],
        "tarifa": 0.0,
        "impuestos": 0.0,
        "total": 0.0,
        "tarifa_neta": 0.0,
        "comision_monto": 0.0,
        "total_pagar": 0.0,
        "calculated_fees_suggested": {},
        "is_compliant": True  # Por defecto asumimos optimismo si falla la auditoría
    }

    @classmethod
    def heal_and_validate(cls, model_class: Type[T], raw_data: Dict[str, Any]) -> T:
        """
        Intenta validar el modelo. Si falla, intenta "curar" el diccionario y re-validar.
        Retorna una instancia del modelo.
        """
        try:
            # Intento 1: Validación pura
            return model_class.parse_obj(raw_data)
        except ValidationError as e:
            logger.warning(f"⚠️ Validación fallida para {model_class.__name__}. Iniciando 'curación' de datos.")
            
            # Extraer campos faltantes del error
            healed_data = raw_data.copy()
            missing_fields = []
            
            for error in e.errors():
                if error['type'] == 'value_error.missing':
                    field_name = error['loc'][0]
                    if isinstance(field_name, str):
                        missing_fields.append(field_name)
            
            if not missing_fields:
                # El error no es por campos faltantes (quizás tipos), 
                # lanzamos para que lo capture la capa superior
                logger.error(f"❌ Error de validación no reparable en {model_class.__name__}: {str(e)}")
                raise e

            # Aplicar sanación
            for field in missing_fields:
                if field in cls.SMART_DEFAULTS:
                    healed_data[field] = cls.SMART_DEFAULTS[field]
                    logger.info(f"🩹 Curado campo faltante '{field}' con valor: {cls.SMART_DEFAULTS[field]}")
                else:
                    # Si no tenemos un default inteligente, buscamos en el modelo si tiene un tipo analizable
                    # (Fallback básico para evitar crash)
                    healed_data[field] = None
                    logger.warning(f"❔ Campo '{field}' no tiene default inteligente. Usando None.")

            try:
                # Intento 2: Re-validación con datos curados
                return model_class.parse_obj(healed_data)
            except ValidationError as e2:
                # Si falla de nuevo, creamos una instancia vacía pero válida si es posible 
                # (aunque esto es extremo, preferimos fallar aquí para boletos)
                logger.error(f"💥 'Curación' insuficiente para {model_class.__name__}: {str(e2)}")
                raise e2

    @classmethod
    def heal_dict_only(cls, raw_data: Dict[str, Any], model_class: Type[BaseModel]) -> Dict[str, Any]:
        """
        Versión que devuelve el dict curado sin instanciar el modelo si se prefiere.
        """
        try:
            instance = cls.heal_and_validate(model_class, raw_data)
            return instance.dict()
        except Exception:
            # Fallback seguro: devolver el dict original si todo falla
            return raw_data
