import os
import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

def upload_logo_to_telegram(file_obj, filename="logo.png"):
    """
    Subre un archivo a Telegram (Storage Channel) y devuelve el file_id.
    Este file_id se usa para recuperar la imagen sin ocupar espacio en DB.
    """
    token = getattr(settings, 'TELEGRAM_BOT_TOKEN', os.getenv('TELEGRAM_BOT_TOKEN'))
    # Canal de almacenamiento dedicado (TravelHub Storage)
    channel_id = getattr(settings, 'TELEGRAM_STORAGE_CHANNEL_ID', '-1003225870613')

    if not token or not channel_id:
        logger.error("Configuración de Telegram Storage incompleta.")
        return None

    url = f"https://api.telegram.org/bot{token}/sendPhoto"
    
    try:
        # Si es un objeto de archivo de Django, leerlo
        if hasattr(file_obj, 'read'):
            file_obj.seek(0)
            files = {'photo': (filename, file_obj.read())}
        else:
            files = {'photo': (filename, file_obj)}

        data = {'chat_id': channel_id, 'caption': f"Storage: {filename}"}
        
        response = requests.post(url, data=data, files=files, timeout=30)
        result = response.json()

        if result.get('ok'):
            # Telegram devuelve una lista de fotos en diferentes tamaños, la última es la original
            photo_data = result['result']['photo'][-1]
            file_id = photo_data['file_id']
            logger.info(f"✅ Logo subido a Telegram Storage. FileID: {file_id}")
            return file_id
        else:
            logger.error(f"❌ Error subiendo a Telegram: {result.get('description')}")
            return None

    except Exception as e:
        logger.error(f"💥 Fallo crítico en telegram_storage: {e}")
        return None

def get_telegram_file_url(file_id):
    """
    Genera una URL para que el frontend pueda mostrar la imagen.
    Nota: Telegram no da URLs directas permanentes, pero podemos usar el proxy de la API
    o simplemente guardar el file_id para que el backend lo sirva.
    """
    token = getattr(settings, 'TELEGRAM_BOT_TOKEN', os.getenv('TELEGRAM_BOT_TOKEN'))
    if not token or not file_id:
        return None
    
    # Esta es la URL para descargar vía API (requiere token, por lo que el frontend no la usa directa)
    # El servidor deberá actuar de proxy o usaremos Cloudinary si está habilitado.
    return f"https://api.telegram.org/bot{token}/getFile?file_id={file_id}"
