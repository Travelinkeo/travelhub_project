import logging
import secrets

from django.conf import settings as dj_settings
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)


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
                "frame-ancestors": "'self'",
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
            response["X-Frame-Options"] = "SAMEORIGIN"
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
