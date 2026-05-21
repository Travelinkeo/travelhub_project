import logging
import secrets
import contextvars
from contextlib import contextmanager

from django.conf import settings as dj_settings
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST


logger = logging.getLogger(__name__)

meta_var = contextvars.ContextVar('meta', default=None)
user_var = contextvars.ContextVar('user', default=None)
agency_var = contextvars.ContextVar('agency', default=None)
system_context_var = contextvars.ContextVar('system_context', default=False)
is_impersonating_var = contextvars.ContextVar('is_impersonating', default=False)
impersonator_var = contextvars.ContextVar('impersonator', default=None)

def get_current_request_meta():
    """Retorna metadatos de la petición actual (IP, User Agent)."""
    return meta_var.get()

def get_current_user():
    """Retorna el usuario de la petición actual (Thread-Safe)."""
    return user_var.get()

def get_current_agency():
    """Retorna la agencia de la petición actual (Thread-Safe/Task-Safe)."""
    return agency_var.get()

def is_system_context():
    """Retorna True si estamos en un contexto de sistema (bypass security)."""
    return system_context_var.get()

def is_impersonating():
    """Retorna True si el usuario actual está impersonando una agencia."""
    return is_impersonating_var.get()

def get_impersonator():
    """Retorna el usuario real que está realizando la impersonación."""
    return impersonator_var.get()


@contextmanager
def agency_context(agency):
    """
    Context manager para establecer manualmente el contexto de la agencia.
    Útil para tareas de Celery o scripts de gestión donde no hay request.
    """
    token = agency_var.set(agency)
    try:
        yield agency
    finally:
        agency_var.reset(token)

@contextmanager
def system_context():
    """
    Context manager para habilitar acceso global (System Mode).
    Usar con extrema precaución solo en tareas de fondo administrativas.
    """
    token = system_context_var.set(True)
    try:
        yield
    finally:
        system_context_var.reset(token)


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
            is_impersonating_flag = False
            impersonator = None
            
            if user:
                if user.is_superuser:
                    # 🎭 GOD MODE: Superusuarios SOLO tienen contexto si impersonan explícitamente
                    impersonated_id = request.session.get('impersonated_agencia_id')
                    if impersonated_id:
                        is_impersonating_flag = True
                        impersonator = user
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
                                    is_impersonating_flag = False
                                    impersonator = None
                                    response = self.get_response(request)
                                    
                                    return response
                            except (ValueError, TypeError):
                                pass
                        from core.models.agencia import Agencia
                        try:
                            agency = Agencia.objects.get(id=impersonated_id)
                        except Agencia.DoesNotExist:
                            del request.session['impersonated_agencia_id']
                            agency = None
                            is_impersonating_flag = False
                            impersonator = None
                    else:
                        # Superuser sin impersonar = Contexto Global (Sin Agencia)
                        agency = None
                else:
                    # 🏢 USUARIO NORMAL: Obtener su agencia asociada (si no fue seteada antes)
                    if not agency:
                        # Verificar si el usuario eligió una agencia activa en la sesión
                        preferred_id = request.session.get('active_agencia_id')
                        if preferred_id:
                            from core.models.agencia import Agencia
                            ua_obj = user.agencias.filter(
                                activo=True,
                                agencia__id=preferred_id,
                                agencia__activa=True
                            ).select_related('agencia').first()
                            if ua_obj:
                                agency = ua_obj.agencia
                        # Si no hay preferencia o no es válida, tomar la primera activa
                        if not agency:
                            ua_obj = user.agencias.filter(activo=True).select_related('agencia').first()
                            if ua_obj:
                                agency = ua_obj.agencia

            
            # Validación final (Seguridad SaaS)
            if not agency and user and not user.is_superuser:
                logger.warning(f"⚠️ Usuario {user.username} (ID:{user.id}) sin agencia vinculada detectado.")


            # 3. Almacenar en Thread Local y Request (CRÍTICO para Views y Mixins)
            t_meta = meta_var.set({'ip': ip, 'user_agent': ua})
            t_user = user_var.set(user)
            t_agency = agency_var.set(agency)
            t_system = system_context_var.set(False) # Por defecto, seguridad activada
            t_is_impersonating = is_impersonating_var.set(is_impersonating_flag)
            t_impersonator = impersonator_var.set(impersonator)
            
            # Inyectar en el objeto request para compatibilidad con views legacy y mixins
            request.agencia = agency
            request.agency = agency # Alias para consistencia
            request.is_impersonating = is_impersonating_flag
            request.impersonator = impersonator

            # 3.5 Configurar Row-Level Security (PostgreSQL current_setting)
            try:
                from django.db import connection
                with connection.cursor() as cursor:
                    tenant_id = str(agency.id) if agency else '0'
                    # FIX: usar session para verificar impersonación, no atributo directo
                    is_impersonating_val = user and user.is_superuser and request.session.get('impersonated_agencia_id')
                    bypass = 'true' if (user and user.is_superuser and not is_impersonating_val) else 'false'
                    cursor.execute("SET LOCAL app.current_agencia_id = %s", [tenant_id])
                    cursor.execute("SET LOCAL app.bypass_rls = %s", [bypass])
            except Exception as e:
                logger.debug(f"RLS no configurado (SQLite/tests): {e}")

        except Exception as e:
            logger.error(f"Error initializing contextvars: {e}")
            t_meta = meta_var.set({})
            t_user = user_var.set(None)
            t_agency = agency_var.set(None)
            t_system = system_context_var.set(False)
            t_is_impersonating = is_impersonating_var.set(False)
            t_impersonator = impersonator_var.set(None)

        try:
            response = self.get_response(request)
        finally:
            # 4. LIMPIEZA CRÍTICA (Evitar memory leaks o data cruzada)
            try: meta_var.reset(t_meta)
            except Exception: pass
            
            try: user_var.reset(t_user)
            except Exception: pass
            
            try: agency_var.reset(t_agency)
            except Exception: pass

            try: system_context_var.reset(t_system)
            except Exception: pass

            try: is_impersonating_var.reset(t_is_impersonating)
            except Exception: pass

            try: impersonator_var.reset(t_impersonator)
            except Exception: pass

        return response


class SecurityHeadersMiddleware:
    """
    Middleware CSP RELAJADO.
    Se ha deshabilitado la generación estricta de nonces para permitir
    que las peticiones asíncronas de HTMX y las clases de Tailwind funcionen
    libremente en el frontend.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Enviar un string vacío en lugar de un token para desactivar la regla estricta del navegador
        # Mantenemos las variables para no causar errores en templates que usan {{ request.csp_nonce }}
        request.csp_nonce = ""
        request.META['CSP_NONCE'] = ""
            
        response = self.get_response(request)
        
        try:
            # CSP Relajado: Permite unsafe-inline y unsafe-eval para frameworks modernos
            csp = "; ".join([
                "default-src 'self' 'unsafe-inline' 'unsafe-eval' data: blob:",
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' blob: https://cdn.jsdelivr.net https://cdn.tailwindcss.com https://unpkg.com https://static.cloudflareinsights.com",
                "style-src 'self' 'unsafe-inline' 'unsafe-eval' https://fonts.googleapis.com https://cdn.jsdelivr.net https://cdn.tailwindcss.com https://unpkg.com",
                "font-src 'self' https://fonts.gstatic.com data:",
                "img-src 'self' data: blob: https://res.cloudinary.com https://*.r2.cloudflarestorage.com",
                "frame-src 'self' https://js.stripe.com http://evolution:8080",
                "connect-src 'self' https://*.cloudflarestorage.com https://api.stripe.com https://generativelanguage.googleapis.com https://cloudflareinsights.com",
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


@csrf_exempt
@require_POST
def csp_report_view(request):
    """
    Endpoint para recibir reportes de violaciones de CSP.
    Útil para depurar reglas sin romper el sitio en producción.
    """
    import json
    from django.http import JsonResponse
    try:
        report = json.loads(request.body.decode('utf-8'))
        logger.warning(f"CSP Violation: {json.dumps(report, indent=2)}")
        return JsonResponse({'status': 'ok'})
    except Exception as e:
        logger.error(f"Error procesando CSP report: {e}")
        return JsonResponse({'error': 'invalid format'}, status=400)