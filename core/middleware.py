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
                    # Intento seguro de obtener agencia activa
                    ua_obj = user.agencias.filter(activo=True).select_related('agencia').first()
                    if ua_obj:
                        agency = ua_obj.agencia
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
    def __init__(self, get_response):
        self.get_response = get_response
    def __call__(self, request):
        try:
            nonce = secrets.token_urlsafe(16)
            request.META['CSP_NONCE'] = nonce
            request.csp_nonce = nonce
        except Exception:
            nonce = 'unsafe-fallback'
        response = self.get_response(request)
        try:
            report_path = '/csp-report/'
            csp = (
                "default-src 'self' https://cdn.tailwindcss.com https://unpkg.com https://cdn.jsdelivr.net; "
                f"script-src 'self' 'nonce-{nonce}' 'unsafe-eval' 'unsafe-inline' https://cdn.tailwindcss.com https://unpkg.com https://cdn.jsdelivr.net https://telegram.org; "
                "style-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://fonts.googleapis.com; "
                "img-src 'self' data: https:; font-src 'self' data: https://fonts.gstatic.com; "
                "connect-src 'self' https://unpkg.com https://cdn.jsdelivr.net; "
                f"report-uri {report_path}; report-to csp-endpoint;"
            )
            response.setdefault('Content-Security-Policy', csp)
            response.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
            response.setdefault('Permissions-Policy', 'geolocation=(), microphone=(), camera=()')
            response.setdefault('X-Frame-Options', 'DENY')
            if not getattr(dj_settings, 'DEBUG', True):
                max_age = getattr(dj_settings, 'SECURE_HSTS_SECONDS', 31536000)
                response.setdefault('Strict-Transport-Security', f'max-age={max_age}; includeSubDomains; preload')
        except Exception:
            logger.exception("Failed to set security headers")
        return response
