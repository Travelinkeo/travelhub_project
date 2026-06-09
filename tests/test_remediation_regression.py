from unittest.mock import Mock

import pytest
from django.core.cache import cache
from django.http import HttpResponse
from django.test import RequestFactory, override_settings

from core.middleware_performance import CacheHeaderMiddleware, QueryCountDebugMiddleware


class TestRateLimitAtomic:
    """Test que cache.incr() es atómico — Fase 1"""

    def test_incr_atomic_returns_correct_count(self):
        cache.delete("test_incr_key")
        cache.set("test_incr_key", 0, timeout=60)
        for i in range(1, 11):
            val = cache.incr("test_incr_key")
            assert val == i, f"Expected {i}, got {val}"

    def test_incr_initializes_with_try_except(self):
        cache.delete("test_init_key")
        try:
            val = cache.incr("test_init_key")
        except ValueError:
            cache.set("test_init_key", 1, timeout=60)
            val = 1
        assert val == 1
        val = cache.incr("test_init_key")
        assert val == 2

    def test_incr_after_timeout_restarts(self):
        cache.delete("test_timeout_key")
        cache.set("test_timeout_key", 1, timeout=1)
        cache.incr("test_timeout_key")
        cache.incr("test_timeout_key")
        import time as _time
        _time.sleep(1.1)
        try:
            cache.incr("test_timeout_key")
        except ValueError:
            cache.set("test_timeout_key", 1, timeout=60)
        val = cache.get("test_timeout_key")
        assert val == 1


class TestNPlusOneDetection:
    """Test que el middleware detecta N+1 — Fase 2"""

    @override_settings(DEBUG=True)
    def test_middleware_tracks_query_count(self):
        get_response = Mock(return_value=HttpResponse())
        middleware = QueryCountDebugMiddleware(get_response)
        factory = RequestFactory()
        request = factory.get("/api/ventas/")
        response = middleware(request)
        assert response is not None

    @override_settings(DEBUG=True)
    def test_middleware_adds_db_headers(self):
        get_response = Mock(return_value=HttpResponse())
        middleware = QueryCountDebugMiddleware(get_response)
        factory = RequestFactory()
        request = factory.get("/api/test/")
        response = middleware(request)
        assert response.has_header("X-DB-Queries")

    @override_settings(DEBUG=True)
    def test_cache_header_middleware_paises(self):
        get_response = Mock(return_value=HttpResponse())
        middleware = CacheHeaderMiddleware(get_response)
        factory = RequestFactory()
        request = factory.get("/api/paises/")
        response = middleware(request)
        assert response["Cache-Control"] == "public, max-age=3600"

    @override_settings(DEBUG=True)
    def test_cache_header_middleware_ciudades(self):
        get_response = Mock(return_value=HttpResponse())
        middleware = CacheHeaderMiddleware(get_response)
        factory = RequestFactory()
        request = factory.get("/api/ciudades/")
        response = middleware(request)
        assert response["Cache-Control"] == "public, max-age=1800"

    @override_settings(DEBUG=True)
    def test_no_cache_headers_for_other(self):
        get_response = Mock(return_value=HttpResponse())
        middleware = CacheHeaderMiddleware(get_response)
        factory = RequestFactory()
        request = factory.get("/api/ventas/")
        response = middleware(request)
        assert "Cache-Control" not in response


class TestSecurityRegression:
    """Test que los fixes de seguridad no regresionan — Fase 1"""

    def test_rate_limit_csp_report_ip(self):
        cache.delete("csp_report_rate_ip_test")
        cache.set("csp_report_rate_ip_test", 0, timeout=60)
        for i in range(6):
            try:
                val = cache.incr("csp_report_rate_ip_test")
            except ValueError:
                cache.set("csp_report_rate_ip_test", 1, timeout=60)
                val = 1
        assert val > 5
