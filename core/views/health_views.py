import logging
import os
import shutil
import time

from django.conf import settings
from django.core.cache import cache
from django.db import connections
from django.http import JsonResponse
from django.views.decorators.http import require_GET

logger = logging.getLogger(__name__)


def _check_database():
    """_check_database."""
    try:
        conn = connections["default"]
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1")
        return {"ok": True}
    except Exception as e:
        logger.error(f"Health check DB failed: {e}")
        return {"ok": False, "error": str(e)[:200]}


def _check_redis():
    """_check_redis."""
    try:
        cache.set("health_check", "ok", timeout=10)
        if cache.get("health_check") == "ok":
            return {"ok": True}
        return {"ok": False, "error": "Redis set/get mismatch"}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


def _check_celery():
    """_check_celery."""
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


def _check_weasyprint():
    """
    Verifica que WeasyPrint (generador de PDF local) esté instalado.
    Reemplaza a _check_gotenberg() eliminado en Fase 5.
    """
    try:
        import weasyprint  # noqa: F401

        return {"ok": True, "engine": "weasyprint"}
    except ImportError:
        return {"ok": False, "error": "weasyprint no instalado"}


def _check_disk():
    """_check_disk."""
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


def _check_celery_queue_depth():
    """_check_celery_queue_depth."""
    from core.metrics import QUEUES

    try:
        from django_redis import get_redis_connection

        r = get_redis_connection("default")
        warnings = {}
        for queue in QUEUES:
            try:
                depth = r.llen(queue)
                warnings[queue] = depth
            except Exception as e:
                logger.debug("Ignored exception reading queue depth: %s", e)
        high = {q: d for q, d in warnings.items() if d > 1000}
        if high:
            return {"ok": False, "queues": high, "detail": f"Queues over 1000: {high}"}
        return {"ok": True, "queues": warnings}
    except Exception as e:
        return {"ok": True, "detail": str(e)[:200]}


def _check_db_pool():
    """_check_db_pool."""
    from django.db import connection

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM pg_stat_activity WHERE state = 'active'")
            active = cursor.fetchone()[0]
        with connection.cursor() as cursor:
            cursor.execute("SHOW max_connections")
            max_conn = int(cursor.fetchone()[0])
        pct = (active / max_conn * 100) if max_conn else 0
        ok = pct < 80
        return {
            "ok": ok,
            "active": active,
            "max": max_conn,
            "used_pct": round(pct, 1),
        }
    except Exception as e:
        return {"ok": True, "detail": str(e)[:200]}


@require_GET
def health_check(request):
    """
    Health check unificado para monitoreo externo (endpoint público).
    Verifica: DB, Redis, Celery, PDF engine, Disco, Celery queue depth, DB pool.
    Las dependencias críticas (database, redis, disk, db_pool) determinan el
    estado 200/503. Los servicios externos opcionales (celery, pdf_engine,
    celery_queue_depth) se reportan pero no degradan el endpoint, para no
    provocar reinicios de pods por caídas parciales de servicios satélite.
    """
    checks = {
        "database": _check_database(),
        "redis": _check_redis(),
        "celery": _check_celery(),
        "pdf_engine": _check_weasyprint(),
        "disk": _check_disk(),
        "celery_queue_depth": _check_celery_queue_depth(),
        "db_pool": _check_db_pool(),
    }

    critical_checks = ("database", "redis", "disk", "db_pool")
    all_ok = all(checks[name].get("ok") for name in critical_checks)
    status_code = 200 if all_ok else 503

    response = {
        "status": "healthy" if all_ok else "degraded",
        "timestamp": time.time(),
        "checks": checks,
    }

    return JsonResponse(response, status=status_code)
