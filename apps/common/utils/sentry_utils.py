"""
Utilidades para Sentry - Sanitización de Datos Sensibles

Este módulo proporciona funciones para limpiar datos sensibles
antes de enviarlos a Sentry para monitoreo de errores.
"""
import logging

logger = logging.getLogger(__name__)

# Palabras clave que indican datos sensibles
SENSITIVE_KEYWORDS = [
    'pasaporte',
    'passport',
    'password',
    'contraseña',
    'token',
    'api_key',
    'secret',
    'credit_card',
    'tarjeta',
    'ssn',
    'cedula',
    'documento',
]


def sanitize_sensitive_data(event, hint):
    """
    Elimina datos sensibles antes de enviar a Sentry
    
    Args:
        event: Evento de Sentry
        hint: Información adicional del evento
        
    Returns:
        event: Evento sanitizado
    """
    try:
        # Sanitizar contexto extra
        if 'extra' in event:
            event['extra'] = _sanitize_dict(event['extra'])
        
        # Sanitizar request data
        if 'request' in event and 'data' in event['request']:
            event['request']['data'] = _sanitize_dict(event['request']['data'])
        
        # Sanitizar variables locales en stack traces
        if 'exception' in event and 'values' in event['exception']:
            for exception in event['exception']['values']:
                if 'stacktrace' in exception and 'frames' in exception['stacktrace']:
                    for frame in exception['stacktrace']['frames']:
                        if 'vars' in frame:
                            frame['vars'] = _sanitize_dict(frame['vars'])
        
        logger.debug("Datos sensibles sanitizados para Sentry")
        return event
        
    except Exception as e:
        logger.error(f"Error sanitizando datos para Sentry: {e}")
        # En caso de error, mejor enviar el evento sin sanitizar
        # que perder el reporte de error
        return event


def _sanitize_dict(data):
    """
    Sanitiza un diccionario recursivamente
    
    Args:
        data: Diccionario a sanitizar
        
    Returns:
        dict: Diccionario sanitizado
    """
    if not isinstance(data, dict):
        return data
    
    sanitized = {}
    for key, value in data.items():
        # Verificar si la clave contiene palabras sensibles
        if any(keyword in str(key).lower() for keyword in SENSITIVE_KEYWORDS):
            sanitized[key] = '[REDACTED]'
        elif isinstance(value, dict):
            # Recursión para diccionarios anidados
            sanitized[key] = _sanitize_dict(value)
        elif isinstance(value, list):
            # Sanitizar listas
            sanitized[key] = [
                _sanitize_dict(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            sanitized[key] = value
    
    return sanitized


def _sanitize_string(text):
    """
    Sanitiza strings que puedan contener datos sensibles
    
    Args:
        text: Texto a sanitizar
        
    Returns:
        str: Texto sanitizado
    """
    if not isinstance(text, str):
        return text
    
    # Patrones comunes de datos sensibles
    import re
    
    # Ocultar números de pasaporte (formato común: letra + 8 dígitos)
    text = re.sub(r'[A-Z]\d{8}', '[PASSPORT-REDACTED]', text)
    
    # Ocultar números de tarjeta de crédito
    text = re.sub(r'\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}', '[CARD-REDACTED]', text)
    
    # Ocultar emails parcialmente
    text = re.sub(r'([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', r'\1***@\2', text)
    
    return text
