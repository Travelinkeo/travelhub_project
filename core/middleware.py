import contextvars
import logging
import os
import secrets
from datetime import datetime, timedelta
from contextlib import contextmanager

from django.conf import settings as dj_settings
from django.http import Http404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)

meta_var = contextvars.ContextVar("meta", default=None)
user_var = contextvars.ContextVar("user", default=None)
agency_var = contextvars.ContextVar("agency", default=None)
system_context_var = contextvars.ContextVar("system_context", default=False)
is_impersonating_var = contextvars.ContextVar("is_impersonating", default=False)
impersonator_var = contextvars.ContextVar("impersonator", default=None)


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
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.agencia = None
        request.agency = None

        try:
            ip = request.META.get("HTTP_CF_CONNECTING_IP") or request.META.get("HTTP_X_REAL_IP")
            if not ip:
                xff = request.META.get("HTTP_X_FORWARDED_FOR")
                if xff:
                    ip = [p.strip() for p in xff.split(",")][-1]
                else:
                    ip = request.META.get("REMOTE_ADDR")
            ua = request.META.get("HTTP_USER_AGENT")
            user = (
                request.user if hasattr(request, "user") and request.user.is_authenticated else None
            )

            agency = getattr(request, "agencia", None)
            is_impersonating_flag = False
            impersonator = None

            if user:
                if user.is_superuser:
                    impersonated_id = request.session.get("impersonated_agencia_id")
                    if impersonated_id:
                        is_impersonating_flag = True
                        impersonator = user
                        impersonated_at = request.session.get("impersonated_at")
                        if impersonated_at:
                            try:
                                start = datetime.fromisoformat(impersonated_at)
                                if dj_settings.USE_TZ and not timezone.is_aware(start):
                                    start = timezone.make_aware(start, timezone.utc)
                                
                                if timezone.now() - start > timedelta(seconds=1800):
                                    del request.session["impersonated_agencia_id"]
                                    del request.session["impersonated_agencia_name"]
                                    del request.session["impersonated_at"]
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
                            del request.session["impersonated_agencia_id"]
                            agency = None
                            is_impersonating_flag = False
                            impersonator = None
                    else:
                        agency = None
                else:
                    if not agency:
                        preferred_id = request.session.get("active_agencia_id")
                        if preferred_id:
                            from core.models.agencia import Agencia
                            ua_obj = (
                                user.agencias.filter(
                                    activo=True, agencia__id=preferred_id, agencia__activa=True
                                )
                                .select_related("agencia")
                                .first()
                            )
                            if ua_obj:
                                agency = ua_obj.agencia
                        if not agency:
                            ua_obj = (
                                user.agencias.filter(activo=True).select_related("agencia").first()
                            )
                            if ua_obj:
                                agency = ua_obj.agencia

            if not agency and user and not user.is_superuser:
                logger.warning(
                    f"⚠️ Usuario {user.username} (ID:{user.id}) sin agencia vinculada detectado."
                )

            t_meta = meta_var.set({"ip": ip, "user_agent": ua})
            t_user = user_var.set(user)
            t_agency = agency_var.set(agency)
            t_system = system_context_var.set(False)
            t_is_impersonating = is_impersonating_var.set(is_impersonating_flag)
            t_impersonator = impersonator_var.set(impersonator)

            request.agencia = agency
            request.agency = agency
            request.is_impersonating = is_impersonating_flag
            request.impersonator = impersonator

            try:
                from django.db import connection
                with connection.cursor() as cursor:
                    tenant_id = str(agency.id) if agency else "0"
                    is_impersonating_val = (
                        user
                        and user.is_superuser
                        and request.session.get("impersonated_agencia_id")
                    )
                    is_admin_path = str(request.path).startswith("/admin/")
                    bypass = (
                        "true"
                        if (user and user.is_superuser and is_admin_path and not is_impersonating_val)
                        else "false"
                    )
                    cursor.execute("SET LOCAL app.current_agencia_id = %s", [tenant_id])
                    cursor.execute("SET LOCAL app.bypass_rls = %s", [bypass])
            except Exception as e:
                logger.debug(f"RLS no configurado: {e}")

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
            for _var, _token in [
                (meta_var, t_meta),
                (user_var, t_user),
                (agency_var, t_agency),
                (system_context_var, t_system),
                (is_impersonating_var, t_is_impersonating),
                (impersonator_var, t_impersonator),
            ]:
                try:
                    _var.reset(_token)
                except Exception:
                    pass

        return response


class SecurityHeadersMiddleware:
    """
    Middleware CSP Dinámico y Seguro.
    Ajustado para interactividad completa de TravelHub.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        nonce = secrets.token_hex(16)
        request.csp_nonce = nonce
        request.META["CSP_NONCE"] = nonce

        response = self.get_response(request)

        try:
            static_domain = getattr(dj_settings, "AWS_S3_CUSTOM_DOMAIN", "")
            static_origin = f"https://{static_domain}" if static_domain else ""
            r2_wildcard = "https://*.r2.cloudflarestorage.com"
            is_debug = getattr(dj_settings, "DEBUG", True)
            is_admin_path = request.path.startswith("/admin/") or request.path.startswith("/system/")

            if is_debug or is_admin_path:
                csp = "; ".join(
                    [
                        "default-src 'self' 'unsafe-inline' 'unsafe-eval' data: blob:",
                        f"script-src 'self' 'unsafe-inline' 'unsafe-eval' blob: {static_origin} https://cdn.jsdelivr.net https://cdn.tailwindcss.com https://unpkg.com https://static.cloudflareinsights.com",
                        f"style-src 'self' 'unsafe-inline' 'unsafe-eval' {static_origin} https://fonts.googleapis.com https://cdn.jsdelivr.net https://cdn.tailwindcss.com https://unpkg.com",
                        f"font-src 'self' {static_origin} https://fonts.gstatic.com data:",
                        f"img-src 'self' data: blob: {static_origin} https://res.cloudinary.com {r2_wildcard} https://images.unsplash.com",
                        "frame-src 'self' https://js.stripe.com http://evolution:8080",
                        f"connect-src 'self' {static_origin} https://*.cloudflarestorage.com https://api.stripe.com https://generativelanguage.googleapis.com https://cloudflareinsights.com https://cdn.jsdelivr.net",
                        "form-action 'self'",
                        "frame-ancestors 'none'",
                        "base-uri 'self'",
                    ]
                )
            else:
                csp = "; ".join(
                    [
                        "default-src 'self' data: blob:",
                        f"script-src 'self' 'unsafe-inline' 'unsafe-eval' blob: {static_origin} https://static.cloudflareinsights.com https://cdn.jsdelivr.net https://cdn.tailwindcss.com https://unpkg.com",
                        f"style-src 'self' 'unsafe-inline' {static_origin} https://fonts.googleapis.com https://cdn.jsdelivr.net https://cdn.tailwindcss.com https://unpkg.com",
                        f"font-src 'self' {static_origin} https://fonts.gstatic.com data:",
                        f"img-src 'self' data: blob: {static_origin} https://res.cloudinary.com {r2_wildcard} https://images.unsplash.com",
                        "frame-src 'self' https://js.stripe.com https://evolution:8080",
                        f"connect-src 'self' {static_origin} https://*.cloudflarestorage.com https://api.stripe.com https://generativelanguage.googleapis.com https://cloudflareinsights.com https://cdn.jsdelivr.net",
                        "form-action 'self'",
                        "frame-ancestors 'none'",
                        "base-uri 'self'",
                        "report-uri /csp-report/",
                    ]
                )

            response["Content-Security-Policy"] = csp
            response["X-Content-Type-Options"] = "nosniff"
            response["Referrer-Policy"] = "strict-origin-when-cross-origin"
            response["X-Frame-Options"] = "DENY"
            response["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"

            if not is_debug:
                max_age = getattr(dj_settings, "SECURE_HSTS_SECONDS", 31536000)
                response["Strict-Transport-Security"] = (
                    f"max-age={max_age}; includeSubDomains; preload"
                )
        except Exception:
            logger.exception("FALLO CRÍTICO: No se pudieron inyectar las cabeceras de seguridad.")

        return response


@csrf_exempt
@require_POST
def csp_report_view(request):
    """Endpoint para recibir reportes de violaciones de CSP."""
    import json
    from django.http import JsonResponse
    from django.core.cache import cache

    max_length = 10 * 1024
    try:
        content_length = int(request.META.get('CONTENT_LENGTH') or 0)
    except (ValueError, TypeError):
        content_length = 0

    if content_length > max_length:
        return JsonResponse({"error": "payload too large"}, status=413)

    ip = request.META.get("HTTP_CF_CONNECTING_IP") or request.META.get("HTTP_X_REAL_IP")
    if not ip:
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        if xff:
            ip = [p.strip() for p in xff.split(",")][-1]
        else:
            ip = request.META.get("REMOTE_ADDR")

    if ip:
        cache_key = f"csp_report_rate_ip_{ip}"
        ip_request_count = cache.get(cache_key, 0)
        if ip_request_count >= 5:
            return JsonResponse({"error": "rate limit exceeded"}, status=429)
        cache.set(cache_key, ip_request_count + 1, timeout=60)

    try:
        body = request.body
        if len(body) > max_length:
            return JsonResponse({"error": "payload too large"}, status=413)

        report = json.loads(body.decode("utf-8"))
        logger.warning(f"CSP Violation: {json.dumps(report, indent=2)}")
        return JsonResponse({"status": "ok"})
    except Exception as e:
        logger.error(f"Error procesando CSP report: {e}")
        return JsonResponse({"error": "invalid format"}, status=400)


class MultiTenantDomainMiddleware:
    """Middleware de enrutamiento avanzado para resolver inquilinos (tenants)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host().split(":")[0].lower()
        main_domain = os.getenv("MAIN_DOMAIN", "travelhub.cc").lower()

        global_hosts = ["localhost", "127.0.0.1", "testserver", main_domain, f"www.{main_domain}"]
        if host in global_hosts:
            request.agencia = None
            request.agency = None
            return self.get_response(request)

        from core.models.agencia import Agencia

        agencia = Agencia.objects.filter(dominio_personalizado=host, activa=True).first()

        if not awoke_agency:
            subdomain = None
            if host.endswith(f".{main_domain}"):
                subdomain = host.replace(f".{main_domain}", "")
            elif host.endswith(".localhost"):
                subdomain = host.replace(".localhost", "")

            if subdomain:
                agencia = Agencia.objects.filter(
                    configuracion_v2__subdominio_slug=subdomain, activa=True
                ).first()

        if agencia:
            request.agencia = agencia
            request.agency = agencia
            return self.get_response(request)

        raise Http404(
            "La plataforma solicitada no existe, no está activa o tiene problemas de configuración."
        )