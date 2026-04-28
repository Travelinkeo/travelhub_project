import hmac
import hashlib
from django.conf import settings

def generate_blind_index(value: str) -> str:
    """
    TRACCIÓN 4X4: Genera un Blind Index (HMAC determinístico) para búsquedas sobre campos cifrados.
    Permite buscar por documento sin descifrar toda la base de datos (O(1) search).
    """
    if not value:
        return ""
    
    # Normalizamos el valor (quitar espacios, mayúsculas) para que la búsqueda sea consistente
    clean_value = str(value).strip().upper()
    
    # Usamos HMAC-SHA256 con el SECRET_KEY como sal
    key = settings.SECRET_KEY.encode('utf-8')
    msg = clean_value.encode('utf-8')
    
    return hmac.new(key, msg, hashlib.sha256).hexdigest()
