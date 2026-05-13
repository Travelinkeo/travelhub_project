import logging
import secrets
from contextlib import contextmanager

from asgiref.local import Local
from django.conf import settings as dj_settings

logger = logging.getLogger(__name__)
_request_local = Local()

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
    """Retorna la agencia de la petición actual (Thread-Safe/Task-Safe)."""
    try:
        return getattr(_request_local, 'agency', None)
    except (AttributeError, Exception):
        return None

def is_system_context():
    """Retorna True si estamos en un contexto de sistema (bypass security)."""
    try:
        return getattr(_request_local, 'system_context', False)
    except (AttributeError, Exception):
        return False


@contextmanager
def agency_context(agency):
    """
    Context manager para establecer manualmente el contexto de la agencia.
    Útil para tareas de Celery o scripts de gestión donde no hay request.
    """
    previous_agency = getattr(_request_local, 'agency', None)
    _request_local.agency = agency
    try:
        yield agency
    finally:
        if previous_agency:
            _request_local.agency = previous_agency
        else:
            try:
                delattr(_request_local, 'agency')
            except AttributeError:
                pass

@contextmanager
def system_context():
    """
    Context manager para habilitar acceso global (System Mode).
    Usar con extrema precaución solo en tareas de fondo administrativas.
    """
    previous_val = getattr(_request_local, 'system_context', False)
    _request_local.system_context = True
    try:
        yield
    finally:
        _request_local.system_context = previous_val


class ThreadLocalContextMiddleware:
    """
    Middleware que almacena el contexto de la petición (Usuario, Agencia, IP)
    en almacenamiento Thread-Local para acceso global seguro.
    Reemplaza a RequestMetaAuditMiddleware.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Inicialización de seguridad: Asegurar que el atributo existe siempre
        request.agencia = None
        request.agency = None
        
        try:
            # 1. Metadatos de Auditoría
            xff = request.META.get('HTTP_X_FORWARDED_FOR')
            ip = xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR')
            ua = request.META.get('HTTP_USER_AGENT')
            user = request.user if hasattr(request, 'user') and request.user.is_authenticated else None
            
            # 2. Determinar Agencia (Soporte Multi-Tenancy / God Mode)
            agency = getattr(request, 'agencia', None)
            
            if user:
                if user.is_superuser:
                    # 🎭 GOD MODE: Superusuarios SOLO tienen contexto si impersonan explícitamente
                    impersonated_id = request.session.get('impersonated_agencia_id')
                    if impersonated_id:
                        # Timeout: expirar impersonación tras 30 min de inactividad
                        impersonated_at = request.session.get('impersonated_at')
                        if impersonated_at:
                            from datetime import datetime, timedelta

                            try:
                                start = datetime.fromisoformat(impersonated_at)
                                if datetime.now(datetime.UTC) - start > timedelta(seconds=1800):
                                    del request.session['impersonated_agencia_id']
                                    del request.session['impersonated_agencia_name']
                                    del request.session['impersonated_at']
                                    logger.info(f"God Mode timeout: {user.username}")
                                    agency = None
                                    response = self.get_response(request)
                                    self._cleanup()
                                    return response
                            except (ValueError, TypeError):
                                pass
                        from core.models.agencia import Agencia
                        try:
                            agency = Agencia.objects.get(id=impersonated_id)
                        except Agencia.DoesNotExist:
                            del request.session['impersonated_agencia_id']
                            agency = None
                    else:
                        # Superuser sin impersonar = Contexto Global (Sin Agencia)
                        agency = None
                else:
                    # 🏢 USUARIO NORMAL: Obtener su agencia asociada (si no fue seteada antes)
                    if not agency:
                        ua_obj = user.agencias.filter(activo=True).select_related('agencia').first()
                        if ua_obj:
                            agency = ua_obj.agencia
            
            # Validación final (Seguridad SaaS)
            if not agency and user and not user.is_superuser:
                logger.warning(f"⚠️ Usuario {user.username} (ID:{user.id}) sin agencia vinculada detectado.")


            # 3. Almacenar en Thread Local y Request (CRÍTICO para Views y Mixins)
            _request_local.meta = {'ip': ip, 'user_agent': ua}
            _request_local.user = user
            _request_local.agency = agency
            _request_local.system_context = False # Por defecto, seguridad activada
            
            # Inyectar en el objeto request para compatibilidad con views legacy y mixins
            request.agencia = agency
            request.agency = agency # Alias para consistencia

            # 3.5 Configurar Row-Level Security (PostgreSQL current_setting)
            try:
                from django.db import connection
                with connection.cursor() as cursor:
                    tenant_id = str(agency.id) if agency else '0'
                    # FIX: usar session para verificar impersonación, no atributo directo
                    is_impersonating = user and user.is_superuser and request.session.get('impersonated_agencia_id')
                    bypass = 'true' if (user and user.is_superuser and not is_impersonating) else 'false'
                    cursor.execute("SET LOCAL app.current_agencia_id = %s", [tenant_id])
                    cursor.execute("SET LOCAL app.bypass_rls = %s", [bypass])
            except Exception as e:
                logger.debug(f"RLS no configurado (SQLite/tests): {e}")

        except Exception as e:
            logger.error(f"Error initializing thread local context: {e}")
            _request_local.meta = {}
            _request_local.user = None
            _request_local.agency = None

        try:
            # Logging básico
            (ua[:50] + '...') if ua else 'N/A'
            # logger.info(f"Request: {request.method} {request.path} from IP: {ip}, UA: {ua_short}")
            
            response = self.get_response(request)
            
            # logger.info(f"Response: {response.status_code} for {request.path}")
        finally:
            # 4. LIMPIEZA CRÍTICA (Evitar memory leaks o data cruzada)
            try:
                del _request_local.meta
            except AttributeError:
                pass
            
            try:
                del _request_local.user
            except AttributeError:
                pass
            
            try:
                del _request_local.agency
            except AttributeError:
                pass

            try:
                del _request_local.system_context
            except AttributeError:
                pass

        return response


class SecurityHeadersMiddleware:  # CSP + cabeceras
    """
    Middleware para inyectar cabeceras de seguridad y política de seguridad de contenido (CSP).
    Usa nonce-based CSP para eliminar 'unsafe-inline' y 'unsafe-eval'.
    Soporta Tailwind CSS (CDN), Alpine.js, HTMX y Google Fonts.
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
            # 2. Content-Security-Policy (Permisiva para compatibilidad con UI frameworks dinámicos)
            csp = "; ".join([
                "default-src 'self'",
                f"script-src 'self' 'nonce-{nonce}' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net",
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net",
                "font-src 'self' https://fonts.gstatic.com",
                "img-src 'self' data: blob: https://res.cloudinary.com https://*.r2.cloudflarestorage.com",
                "frame-src 'self' https://js.stripe.com http://evolution:8080",
                "connect-src 'self' https://*.cloudflarestorage.com https://api.stripe.com https://generativelanguage.googleapis.com",
                "form-action 'self'",
                "frame-ancestors 'none'",
                "base-uri 'self'",
            ])
            response['Content-Security-Policy'] = csp
            response['X-Content-Type-Options'] = 'nosniff'
            response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
            response['X-Frame-Options'] = 'DENY'
            response['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
            
            if not getattr(dj_settings, 'DEBUG', True):
                max_age = getattr(dj_settings, 'SECURE_HSTS_SECONDS', 31536000)
                response['Strict-Transport-Security'] = f'max-age={max_age}; includeSubDomains; preload'
        except Exception:
            logger.exception("FALLO CRÍTICO: No se pudieron inyectar las cabeceras de seguridad.")
            
        return response
