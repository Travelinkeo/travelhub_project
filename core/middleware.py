import logging
import secrets
from threading import local

from django.conf import settings as dj_settings

logger = logging.getLogger(__name__)
_request_local = local()

def get_current_request_meta():  # util usado por auditoría
    try:
        return getattr(_request_local, 'meta', None)
    except Exception:
        return None


class RequestMetaAuditMiddleware:  # Middleware para auditoría IP/UA
    def __init__(self, get_response):
        self.get_response = get_response
    def __call__(self, request):
        try:
            xff = request.META.get('HTTP_X_FORWARDED_FOR')
            ip = xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR')
            ua = request.META.get('HTTP_USER_AGENT')
            _request_local.meta = {'ip': ip, 'user_agent': ua}
        except Exception:
            _request_local.meta = {}
        try:
            logger.info(f"Request: {request.method} {request.path} from IP: {ip}, UA: {ua[:50]}...")
            response = self.get_response(request)
            logger.info(f"Response: {response.status_code} for {request.path}, Location: {getattr(response, 'get', lambda k: None)('Location')}")
        finally:  # limpieza
            try:
                del _request_local.meta
            except AttributeError:
                pass
        return response


class SecurityHeadersMiddleware:  # CSP + cabeceras
    def __init__(self, get_response):
        self.get_response = get_response
    def __call__(self, request):
        try:
            nonce = secrets.token_urlsafe(16)
            request.META['CSP_NONCE'] = nonce
        except Exception:
            nonce = 'unsafe-fallback'
        response = self.get_response(request)
        try:
            report_path = '/csp-report/'
            csp = (
                "default-src 'self'; "
                f"script-src 'self' 'nonce-{nonce}'; "
                "style-src 'self'; img-src 'self' data:; font-src 'self' data:; "
                "connect-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'self'; form-action 'self'; "
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
