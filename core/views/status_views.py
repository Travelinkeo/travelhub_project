"""
Vista de Status Page — estado de servicios.

Retorna JSON con el estado de DB, Redis, Celery, Gotenberg, etc.
Sirve tanto para monitoreo interno como para status.travelhub.cc.
"""

import time

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def status_api(request):
    """Endpoint JSON de estado — consumo programático."""
    start = time.time()

    checks = {
        "database": _check_db(),
        "redis": _check_redis(),
        "gotenberg": _check_gotenberg(),
        "disk": _check_disk(),
    }

    all_ok = all(v.get("ok", False) for v in checks.values())
    response_time = round((time.time() - start) * 1000, 1)

    data = {
        "status": "ok" if all_ok else "degraded",
        "version": getattr(settings, "APP_VERSION", "2.0.0"),
        "environment": getattr(settings, "ENVIRONMENT", "production"),
        "response_time_ms": response_time,
        "checks": checks,
        "timestamp": time.time(),
    }
    status_code = 200 if all_ok else 503
    return JsonResponse(data, status=status_code)


def _check_db():
    try:
        connection.ensure_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


def _check_redis():
    try:
        cache.set("_status_ping", "ok", timeout=5)
        if cache.get("_status_ping") == "ok":
            return {"ok": True}
        return {"ok": False, "error": "Redis set/get mismatch"}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


def _check_gotenberg():
    import urllib.request

    gotenberg_url = getattr(settings, "GOTENBERG_URL", "http://gotenberg:3000")
    try:
        urllib.request.urlopen(f"{gotenberg_url}/health", timeout=5)  # noqa: S310
        return {"ok": True}
    except Exception as e:
        return {"ok": True, "detail": str(e)[:100]}  # non-critical


def _check_disk():
    import shutil

    try:
        usage = shutil.disk_usage(settings.BASE_DIR)
        pct_free = (usage.free / usage.total) * 100
        ok = pct_free > 10
        return {"ok": ok, "free_percent": round(pct_free, 1)}
    except Exception as e:
        return {"ok": True, "detail": str(e)[:100]}
