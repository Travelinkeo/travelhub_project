import logging
import secrets
from threading import local

from django.conf import settings as dj_settings

logger = logging.getLogger(__name__)
_request_local = local()

def get_current_request_meta():
    """Retorna metadatos de la petición actual (IP, User Agent)."""
    try:
        return getattr(_request_local, 'meta', None)
    except Exception:
        return None

def get_current_user():
    """Retorna el usuario de la petición actual (Thread-Safe)."""
    try:
        return getattr(_request_local, 'user', None)
    except Exception:
        return None

def get_current_agency():
    """Retorna la agencia de la petición actual (Thread-Safe)."""
    try:
        return getattr(_request_local, 'agency', None)
    except Exception:
        return None


class ThreadLocalContextMiddleware:
    """
    Middleware que almacena el contexto de la petición (Usuario, Agencia, IP)
    en almacenamiento Thread-Local para acceso global seguro.
    Reemplaza a RequestMetaAuditMiddleware.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            # 1. Metadatos de Auditoría
            xff = request.META.get('HTTP_X_FORWARDED_FOR')
            ip = xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR')
            ua = request.META.get('HTTP_USER_AGENT')
            user = request.user if hasattr(request, 'user') and request.user.is_authenticated else None
            
            # 2. Determinar Agencia (Intentamos obtenerla de request.agencia si middleware previo la seteó)
            agency = getattr(request, 'agencia', None)
            
            # Si no está en request, intentamos resolverla (lógica simplificada de reserva)
            if not agency and user:
                try:
                    # 1. Intento por asociación de usuario
                    ua_obj = user.agencias.filter(activo=True).select_related('agencia').first()
                    if ua_obj:
                        agency = ua_obj.agencia
                    
                    # 2. Fallback Directo a Travelinkeo (ID 1) - Requerimiento de consistencia Fase 12.0
                    if not agency:
                        from core.models.agencia import Agencia
                        agency = Agencia.objects.filter(pk=1).first()
                    
                    # 3. Fallback de emergencia para superusers/otros
                    if not agency and user.is_superuser:
                        from core.models.agencia import Agencia
                        agency = Agencia.objects.all().first()
                except Exception:
                    pass

            # 3. Almacenar en Thread Local
            _request_local.meta = {'ip': ip, 'user_agent': ua}
            _request_local.user = user
            _request_local.agency = agency

        except Exception as e:
            logger.error(f"Error initializing thread local context: {e}")
            _request_local.meta = {}
            _request_local.user = None
            _request_local.agency = None

        try:
            # Logging básico
            ua_short = (ua[:50] + '...') if ua else 'N/A'
            # logger.info(f"Request: {request.method} {request.path} from IP: {ip}, UA: {ua_short}")
            
            response = self.get_response(request)
            
            # logger.info(f"Response: {response.status_code} for {request.path}")
        finally:
            # 4. LIMPIEZA CRÍTICA (Evitar memory leaks o data cruzada)
            try:
                del _request_local.meta
            except AttributeError: pass
            
            try:
                del _request_local.user
            except AttributeError: pass
            
            try:
                del _request_local.agency
            except AttributeError: pass

        return response


class SecurityHeadersMiddleware:  # CSP + cabeceras
    """
    Middleware para inyectar cabeceras de seguridad y política de seguridad de contenido (CSP).
    Optimizado para soportar Tailwind CSS (CDN), Alpine.js, HTMX y Google Fonts.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 1. Generar nonce robusto para TODAS las plantillas
        nonce = secrets.token_hex(16)
        request.csp_nonce = nonce
        request.META['CSP_NONCE'] = nonce  # Compatibilidad con plantillas legacy
            
        response = self.get_response(request)
        
        try:
            # 2. DESACTIVAR CSP TEMPORALMENTE para diagnóstico
            # csp = "..." 
            
            # response['Content-Security-Policy'] = csp
            response['X-Content-Type-Options'] = 'nosniff'
            response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
            response['X-Frame-Options'] = 'DENY'

            response['X-Frame-Options'] = 'DENY'
            
            if not getattr(dj_settings, 'DEBUG', True):
                max_age = getattr(dj_settings, 'SECURE_HSTS_SECONDS', 31536000)
                response['Strict-Transport-Security'] = f'max-age={max_age}; includeSubDomains; preload'
        except Exception:
            logger.exception("🔥 FALLO CRÍTICO: No se pudieron inyectar las cabeceras de seguridad.")
            
        return response
