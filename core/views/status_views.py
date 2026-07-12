"""
Vista de Status Page — estado de servicios (HTML + JSON).

Rutas:
  GET /status/       → Página HTML pública visual
  GET /status/api/   → JSON programático (para Uptime Robot, etc.)
"""

import time

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

# --------------------------------------------------------------------------
# Checks individuales
# --------------------------------------------------------------------------


def _check_db():
    t0 = time.time()
    try:
        connection.ensure_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return {"ok": True, "latency_ms": round((time.time() - t0) * 1000, 1)}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200], "latency_ms": None}


def _check_redis():
    t0 = time.time()
    try:
        cache.set("_status_ping", "ok", timeout=5)
        if cache.get("_status_ping") == "ok":
            return {"ok": True, "latency_ms": round((time.time() - t0) * 1000, 1)}
        return {"ok": False, "error": "Redis set/get mismatch", "latency_ms": None}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200], "latency_ms": None}


def _check_celery():
    try:
        from travelhub.celery import app as celery_app

        inspect = celery_app.control.inspect(timeout=2.0)
        stats = inspect.stats()
        if stats:
            workers = list(stats.keys())
            return {"ok": True, "workers": len(workers), "worker_names": workers[:3]}
        return {"ok": False, "error": "No workers responding", "workers": 0}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


def _check_storage():
    import shutil

    try:
        usage = shutil.disk_usage(settings.BASE_DIR)
        pct_free = (usage.free / usage.total) * 100
        ok = pct_free > 10
        return {
            "ok": ok,
            "free_percent": round(pct_free, 1),
            "total_gb": round(usage.total / 1e9, 1),
            "free_gb": round(usage.free / 1e9, 1),
        }
    except Exception as e:
        return {"ok": True, "detail": str(e)[:100]}


def _check_gotenberg():
    import urllib.request

    gotenberg_url = getattr(settings, "GOTENBERG_URL", "")
    if not gotenberg_url:
        return {"ok": True, "detail": "Not configured"}
    try:
        urllib.request.urlopen(f"{gotenberg_url}/health", timeout=3)  # noqa: S310
        return {"ok": True}
    except Exception as e:
        return {"ok": True, "detail": str(e)[:100]}  # non-critical


# --------------------------------------------------------------------------
# Labels para la UI
# --------------------------------------------------------------------------

SERVICE_META = {
    "database": {"label": "Base de Datos", "icon": "🗄️", "critical": True},
    "cache": {"label": "Cache / Redis", "icon": "⚡", "critical": True},
    "celery": {"label": "Workers Celery", "icon": "⚙️", "critical": False},
    "storage": {"label": "Almacenamiento", "icon": "💾", "critical": False},
    "pdf": {"label": "Generador PDF", "icon": "📄", "critical": False},
}


def _run_checks():
    checks = {
        "database": _check_db(),
        "cache": _check_redis(),
        "celery": _check_celery(),
        "storage": _check_storage(),
        "pdf": _check_gotenberg(),
    }
    # Adjuntar metadata de UI
    for key, meta in SERVICE_META.items():
        if key in checks:
            checks[key].update(meta)

    return checks


# --------------------------------------------------------------------------
# Vistas
# --------------------------------------------------------------------------


@require_GET
def status_page(request):
    """Página HTML pública del estado del sistema."""
    t0 = time.time()
    checks = _run_checks()
    elapsed = round((time.time() - t0) * 1000, 1)

    # Calcular estado global
    critical_ok = all(
        v.get("ok", False)
        for k, v in checks.items()
        if SERVICE_META.get(k, {}).get("critical", False)
    )
    all_ok = all(v.get("ok", False) for v in checks.values())

    if all_ok:
        overall = "operational"
        overall_label = "Todos los sistemas operativos"
        overall_color = "green"
    elif critical_ok:
        overall = "degraded"
        overall_label = "Servicio degradado"
        overall_color = "yellow"
    else:
        overall = "outage"
        overall_label = "Interrupción del servicio"
        overall_color = "red"

    context = {
        "checks": checks,
        "overall": overall,
        "overall_label": overall_label,
        "overall_color": overall_color,
        "elapsed_ms": elapsed,
        "app_version": getattr(settings, "APP_VERSION", "2.0.0"),
        "environment": getattr(settings, "SENTRY_ENVIRONMENT", "production"),
    }
    return render(request, "status/status_page.html", context)


@require_GET
def status_api(request):
    """Endpoint JSON — consumo programático (Uptime Robot, k8s probes, etc.)."""
    t0 = time.time()
    checks = _run_checks()
    elapsed = round((time.time() - t0) * 1000, 1)

    all_ok = all(v.get("ok", False) for v in checks.values())

    data = {
        "status": "ok" if all_ok else "degraded",
        "version": getattr(settings, "APP_VERSION", "2.0.0"),
        "environment": getattr(settings, "SENTRY_ENVIRONMENT", "production"),
        "response_time_ms": elapsed,
        "services": {
            k: {"ok": v.get("ok"), "latency_ms": v.get("latency_ms")} for k, v in checks.items()
        },
        "timestamp": time.time(),
    }
    return JsonResponse(data, status=200 if all_ok else 503)
