import contextvars
import logging
import os
import secrets
import time
from contextlib import contextmanager
from datetime import datetime, timedelta

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
def agency_context(agency, reason: str = "unspecified"):
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
def system_context(reason: str = "unspecified", max_seconds: float = 60.0):
    """
    Context manager para habilitar acceso global sin filtro de tenant (System Mode).

    ⚠️  PRECAUCIÓN EXTREMA — SOLO PARA TAREAS DE FONDO ADMINISTRATIVAS.
    Deshabilita TODOS los filtros de multi-tenancy durante el bloque.

    Args:
        reason:      Descripción obligatoria del motivo (registrada en logs de auditoría).
        max_seconds: Alerta si el bloque tarda más de este tiempo (default: 60s).

    Uso correcto:
        with system_context(reason="retry_queued_boletos"):
            BoletoImportado.all_objects.filter(...).update(...)
    """
    # 1. Requerir variable de entorno para permitir system_context (opt-in safety)
    import os

    if os.environ.get("ALLOW_SYSTEM_CONTEXT", "").lower() not in ("1", "true", "yes"):
        audit_logger = logging.getLogger("core.security.audit")
        audit_logger.critical(
            f"🚨 [SYSTEM_CONTEXT BLOCKED] reason={reason!r} caller={_get_caller_info()} — "
            "ALLOW_SYSTEM_CONTEXT env var no está configurada. "
            "system_context() SOLO permitido con ALLOW_SYSTEM_CONTEXT=1"
        )
        raise PermissionError(
            "system_context() requiere ALLOW_SYSTEM_CONTEXT=1 en variables de entorno. "
            "Esto es una medida de seguridad para evitar bypasses accidentales de multi-tenancy."
        )

    audit_logger = logging.getLogger("core.security.audit")
    audit_logger.warning(f" [SYSTEM_CONTEXT OPEN] reason={reason!r} caller={_get_caller_info()}")
    token = system_context_var.set(True)
    start = time.monotonic()
    try:
        yield
    finally:
        elapsed = time.monotonic() - start
        system_context_var.reset(token)
        if elapsed > max_seconds:
            audit_logger.error(
                f"⚠️  [SYSTEM_CONTEXT EXCEEDED] reason={reason!r} "
                f"elapsed={elapsed:.2f}s limit={max_seconds}s — "
                f"Posible fuga de bypass de seguridad."
            )
        else:
            audit_logger.info(
                f"🔒 [SYSTEM_CONTEXT CLOSED] reason={reason!r} elapsed={elapsed:.2f}s"
            )

        # 2. Enviar alerta a Sentry si está disponible (auditoría de uso)
        try:
            import sentry_sdk

            with sentry_sdk.push_scope() as scope:
                scope.set_tag("component", "system_context")
                scope.set_tag("reason", reason)
                scope.set_extra("elapsed_seconds", elapsed)
                scope.set_extra("caller", _get_caller_info())
                sentry_sdk.capture_message(
                    f"system_context used: {reason} ({elapsed:.2f}s)",
                    level="warning",
                )
        except Exception:  # noqa: S110
            # Sentry no disponible, silencioso
            pass


def _get_caller_info() -> str:
    """Retorna module:lineno del llamador de system_context para auditoría."""
    import traceback

    stack = traceback.extract_stack()
    # El índice [-3] suele ser el código que llama 'with system_context(...)'
    if len(stack) >= 3:
        frame = stack[-3]
        return f"{frame.filename.split('/')[-1]}:{frame.lineno}"
    return "unknown"


# =========================================================================================
# 🏢 EXPLICACIÓN PARA TODO PÚBLICO (Inversores y No Programadores)
# Imagine que TravelHub es un gran hotel de lujo multi-inquilino. Cada agencia es un huésped
# diferente hospedado en una suite privada. Esta clase es el "Conserje de Seguridad" del hotel.
# Su única y vital misión es garantizar que la Agencia A nunca pueda ver lo que hay dentro
# de la habitación de la Agencia B.
#
# Para lograr esto, antes de que cualquier request proceda, el conserje toma el pasaporte del
# usuario, identifica a qué "agencia" pertenece y coloca esa etiqueta en una caja fuerte sellada
# temporalmente para ese hilo de ejecución. Nadie puede falsificar o alterar esa etiqueta mientras
# dure la petición. Así, la base de datos sabe exactamente a quién mostrarle la información.
#
# 💻 EXPLICACIÓN PARA PROGRAMADORES (Technical Specs)
# ThreadLocalContextMiddleware centraliza el ciclo de vida del Tenant Context utilizando
# ContextVars de Python para garantizar seguridad Thread-Safe y Task-Safe (para flujos asíncronos).
# En cada request, inicializa y limpia el contexto para evitar fugas de memoria o contaminación cruzada.
# Luego, define variables de sesión e IP y configura los parámetros de sesión RLS (Row Level Security)
# directo en PostgreSQL mediante `SET LOCAL app.current_agencia_id` y `SET LOCAL app.bypass_rls`,
# blindando la base de datos contra accesos no autorizados a nivel de fila.
# =========================================================================================
class ThreadLocalContextMiddleware:
    """
    Middleware que almacena el contexto de la petición (Usuario, Agencia, IP)
    en almacenamiento Thread-Local / Task-Local (ContextVars) para acceso global seguro.
    Garantiza aislamiento absoluto contra la reutilización de hilos y conexiones.
    """

    def __init__(self, get_response):
        """__init__."""
        self.get_response = get_response

    def __call__(self, request):
        request.agencia = None
        request.agency = None
        request.is_impersonating = False
        request.impersonator = None

        # Inicialización preventiva de tokens de ContextVar a None
        t_meta = None
        t_user = None
        t_agency = None
        t_system = None
        t_is_impersonating = None
        t_impersonator = None

        try:
            # 1. Reset preemptivo de variables en el hilo actual antes de procesar
            meta_var.set(None)
            user_var.set(None)
            agency_var.set(None)
            system_context_var.set(False)
            is_impersonating_var.set(False)
            impersonator_var.set(None)

            # 2. Extracción de metadatos e IP segura
            ip = request.META.get("HTTP_CF_CONNECTING_IP") or request.META.get("HTTP_X_REAL_IP")
            if not ip:
                xff = request.META.get("HTTP_X_FORWARDED_FOR")
                if xff:
                    ip = [p.strip() for p in xff.split(",")][0]
                else:
                    ip = request.META.get("REMOTE_ADDR")
            ua = request.META.get("HTTP_USER_AGENT")
            user = (
                request.user if hasattr(request, "user") and request.user.is_authenticated else None
            )

            agency = getattr(request, "agencia", None)
            is_impersonating_flag = False
            impersonator = None

            # 3. Lógica de Impersonación y Resolución de Agencia
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

            # 4. Establecer las variables de contexto y guardar tokens
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

            # 5. Establecer contexto RLS en la base de datos
            try:
                from django.db import connection

                if connection.connection is not None:
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
                            if (
                                user
                                and user.is_superuser
                                and is_admin_path
                                and not is_impersonating_val
                            )
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

        # 6. Procesar petición y asegurar limpieza absoluta en bloque finally
        try:
            response = self.get_response(request)
        finally:
            # Reseteo seguro de ContextVars
            for _var, _token in [
                (meta_var, t_meta),
                (user_var, t_user),
                (agency_var, t_agency),
                (system_context_var, t_system),
                (is_impersonating_var, t_is_impersonating),
                (impersonator_var, t_impersonator),
            ]:
                if _token is not None:
                    try:
                        _var.reset(_token)
                    except Exception as e:
                        logger.error(f"Error resetting context var {_var.name}: {e}")

            # Reseteo seguro de variables de sesión en Base de Datos
            try:
                from django.db import connection

                if connection.connection is not None:
                    with connection.cursor() as cursor:
                        cursor.execute("SET LOCAL app.current_agencia_id = '0'")
                        cursor.execute("SET LOCAL app.bypass_rls = 'false'")
            except Exception as e:
                logger.debug(f"Error resetting database RLS context: {e}")

        return response


class SecurityHeadersMiddleware:
    """
    Middleware CSP Dinámico y Seguro.
    Ajustado para interactividad completa de TravelHub.
    """

    def __init__(self, get_response):
        """__init__."""
        self.get_response = get_response

    def __call__(self, request):
        nonce = secrets.token_hex(16)
        request.csp_nonce = nonce
        request.META["CSP_NONCE"] = nonce

        response = self.get_response(request)

        # Skip CSP injection for Evolution API Proxy to allow its own UI to load without strict-dynamic blocks
        if request.path_info.startswith("/system/whatsapp/qr/"):
            if "X-Frame-Options" in response:
                del response["X-Frame-Options"]
            if "Content-Security-Policy" in response:
                del response["Content-Security-Policy"]
            return response

        try:
            static_domain = getattr(dj_settings, "AWS_S3_CUSTOM_DOMAIN", "")
            static_origin = f"https://{static_domain}" if static_domain else ""
            r2_wildcard = "https://*.r2.cloudflarestorage.com"
            is_debug = getattr(dj_settings, "DEBUG", True)

            # Alpine.js (v2/v3) y HTMX requieren 'unsafe-eval' y 'unsafe-inline' para evaluar expresiones inline y scripts dinamicos de HTMX/Unfold
            script_src = (
                f"'self' 'nonce-{nonce}' 'unsafe-eval' 'unsafe-inline' "
                f"{static_origin} https://cdn.jsdelivr.net https://cdn.tailwindcss.com "
                f"https://unpkg.com https://static.cloudflareinsights.com"
            )
            if is_debug:
                script_src += " http://localhost:3000 ws://localhost:3000"
            csp_dict = {
                "default-src": "'self' data: blob:",
                "script-src": script_src,
                "style-src": (
                    f"'self' 'unsafe-inline' {static_origin} "
                    "https://fonts.googleapis.com https://cdn.jsdelivr.net "
                    "https://cdn.tailwindcss.com https://unpkg.com"
                ),
                "font-src": f"'self' {static_origin} https://fonts.gstatic.com data:",
                "img-src": (
                    f"'self' data: blob: "
                    f"{static_origin} https://res.cloudinary.com {r2_wildcard} "
                    "https://images.unsplash.com https://pics.avs.io "
                    "https://ui-avatars.com https://placehold.co"
                ),
                "frame-src": "'self' https://js.stripe.com http://evolution:8080",
                "connect-src": (
                    f"'self' "
                    f"{static_origin} https://*.cloudflarestorage.com "
                    "https://api.stripe.com https://generativelanguage.googleapis.com "
                    "https://cloudflareinsights.com https://cdn.jsdelivr.net"
                ),
                "form-action": "'self'",
                "frame-ancestors": "'none'",
                "base-uri": "'self'",
            }

            # Fusionar directivas CSP específicas de la agencia (White Label)
            agencia = getattr(request, "agencia", None)
            if agencia:
                try:
                    extra_csp = agencia.configuracion_v2.csp_directives or {}
                    if isinstance(extra_csp, dict):
                        for directive, values in extra_csp.items():
                            if directive in csp_dict:
                                existing = csp_dict[directive]
                                if isinstance(values, list):
                                    extra = " ".join(values)
                                    csp_dict[directive] = f"{existing} {extra}"
                                elif isinstance(values, str) and values:
                                    csp_dict[directive] = f"{existing} {values}"
                            elif isinstance(values, list | str):
                                val = " ".join(values) if isinstance(values, list) else values
                                csp_dict[directive] = val
                except Exception:
                    logger.warning(f"Error al aplicar CSP específico para agencia {agencia.id}")

            csp = "; ".join(f"{k} {v}" for k, v in csp_dict.items())

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


@csrf_exempt  # CSRF exempt: read-only CSP report collector, no session needed
@require_POST
def csp_report_view(request):
    """Endpoint para recibir reportes de violaciones de CSP."""
    import json

    from django.core.cache import cache
    from django.http import JsonResponse

    max_length = 10 * 1024
    try:
        content_length = int(request.META.get("CONTENT_LENGTH") or 0)
    except (ValueError, TypeError):
        content_length = 0

    if content_length > max_length:
        return JsonResponse({"error": "payload too large"}, status=413)

    ip = request.META.get("HTTP_CF_CONNECTING_IP") or request.META.get("HTTP_X_REAL_IP")
    if not ip:
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        if xff:
            ip = [p.strip() for p in xff.split(",")][0]
        else:
            ip = request.META.get("REMOTE_ADDR")

    if ip:
        cache_key = f"csp_report_rate_ip_{ip}"
        try:
            ip_request_count = cache.incr(cache_key)
        except ValueError:
            cache.set(cache_key, 1, timeout=60)
            ip_request_count = 1
        if ip_request_count > 5:
            return JsonResponse({"error": "rate limit exceeded"}, status=429)

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
        """__init__."""
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

        if not agencia:
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
