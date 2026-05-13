import base64
import logging

import requests

logger = logging.getLogger(__name__)

def get_image_as_base64(image_source):
    """
    Convierte una imagen (URL, ImageField, o path local) a una cadena Base64.
    Útil para inyectar imágenes en plantillas HTML antes de generar PDFs.
    
    Args:
        image_source: Puede ser un objeto FieldFile (ImageField), una URL string, o un path.
        
    Returns:
        str: La cadena data URI en base64 (e.g., "data:image/png;base64,...") o None si falla.
    """
    if not image_source:
        return None

    try:
        content_type = "image/png"  # Default
        image_data = None

        # 1. Caso: URL remota
        if isinstance(image_source, str) and (image_source.startswith('http://') or image_source.startswith('https://')):
            response = requests.get(image_source, timeout=10)
            response.raise_for_status()
            image_data = response.content
            content_type = response.headers.get('Content-Type', 'image/png')

        # 2. Caso: Django ImageField / FileField
        elif hasattr(image_source, 'url'):
            try:
                # Intentamos abrirlo desde el storage directamente
                with image_source.open('rb') as f:
                    image_data = f.read()
                
                # Intentar determinar el content type si es posible
                import mimetypes
                content_type, _ = mimetypes.guess_type(image_source.name)
                if not content_type:
                    content_type = "image/png"
            except Exception as e:
                logger.warning(f"No se pudo abrir ImageField directamente: {e}. Reintentando via URL.")
                # Fallback a URL si el storage es remoto (R2, S3)
                return get_image_as_base64(image_source.url)

        # 3. Caso: Path local (string)
        elif isinstance(image_source, str):
            with open(image_source, 'rb') as f:
                image_data = f.read()
            import mimetypes
            content_type, _ = mimetypes.guess_type(image_source)

        if image_data:
            base64_encoded = base64.b64encode(image_data).decode('utf-8')
            return f"data:{content_type};base64,{base64_encoded}"

    except Exception as e:
        logger.error(f"Error al convertir imagen a Base64: {e}", exc_info=True)
    
    return None


def get_agencia_logo_b64(agencia, is_dark_bg=True):
    """
    Obtiene el logo de la agencia en Base64 de forma dinámica.
    Prioriza los archivos físicos (FileField) o URLs sobre cualquier otro campo.
    
    Args:
        agencia: Objeto Agencia.
        is_dark_bg: Boolean, si el fondo donde se pondrá el logo es oscuro.
    """
    if not agencia:
        return None
        
    # Lógica de selección de logo según el fondo y disponibilidad
    logo_source = None
    
    if is_dark_bg:
        # Para fondos oscuros, preferimos logo_dark
        logo_source = (getattr(agencia, 'logo_dark', None) or 
                       getattr(agencia, 'logo', None) or 
                       getattr(agencia, 'logo_telegram_url', None))
    else:
        # Para fondos claros, preferimos logo_light
        logo_source = (getattr(agencia, 'logo_light', None) or 
                       getattr(agencia, 'logo', None) or 
                       getattr(agencia, 'logo_telegram_url', None))
        
    if not logo_source:
        return None
        
    return get_image_as_base64(logo_source)
