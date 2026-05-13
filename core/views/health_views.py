import logging
import os
import shutil
import time

from django.conf import settings
from django.core.cache import cache
from django.db import connections
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger(__name__)


def _check_database():
    try:
        conn = connections["default"]
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1")
        return {"ok": True}
    except Exception as e:
        logger.error(f"Health check DB failed: {e}")
        return {"ok": False, "error": str(e)[:200]}


def _check_redis():
    try:
        cache.set("health_check", "ok", timeout=10)
        if cache.get("health_check") == "ok":
            return {"ok": True}
        return {"ok": False, "error": "Redis set/get mismatch"}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


def _check_celery():
    try:
        from travelhub.celery import app as celery_app

        insp = celery_app.control.inspect(timeout=3)
        stats = insp.stats()
        if stats:
            workers = len(stats)
            return {"ok": True, "workers": workers}
        return {"ok": False, "error": "No Celery workers responding"}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


def _check_gotenberg():
    gotenberg_url = getattr(settings, "GOTENBERG_URL", None)
    if not gotenberg_url:
        return {"ok": True, "note": "Gotenberg not configured, skipping"}
    try:
        import urllib.request

        req = urllib.request.Request(f"{gotenberg_url}/health", method="GET")  # noqa: S310
        with urllib.request.urlopen(req, timeout=5) as resp:  # noqa: S310
            return {"ok": resp.status == 200}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


def _check_disk():
    try:
        media_path = settings.MEDIA_ROOT or os.path.join(settings.BASE_DIR, "media")
        stat = shutil.disk_usage(media_path)
        total_gb = stat.total / (1024**3)
        free_gb = stat.free / (1024**3)
        used_pct = (stat.used / stat.total) * 100
        ok = free_gb > 1  # Al menos 1 GB libre
        return {
            "ok": ok,
            "total_gb": round(total_gb, 1),
            "free_gb": round(free_gb, 1),
            "used_pct": round(used_pct, 1),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


@csrf_exempt
def health_check(request):
    """
    Health check unificado para monitoreo externo.
    Verifica: DB, Redis, Celery, Gotenberg, Disco.
    Retorna 200 si todo OK, 503 si algo degradado.
    """
    checks = {
        "database": _check_database(),
        "redis": _check_redis(),
        "celery": _check_celery(),
        "gotenberg": _check_gotenberg(),
        "disk": _check_disk(),
    }

    all_ok = all(v.get("ok") for v in checks.values())
    status_code = 200 if all_ok else 503

    response = {
        "status": "ok" if all_ok else "degraded",
        "timestamp": time.time(),
        "checks": checks,
    }

    return JsonResponse(response, status=status_code)
