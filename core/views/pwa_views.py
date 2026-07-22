"""
Vistas para PWA (Progressive Web App).

Sirve manifest.json, service-worker.js y página offline.
"""

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET


@require_GET
@cache_control(max_age=3600, public=True)
def manifest(request):
    """Sirve el manifest.json de la PWA (raw, sin parseo JSON)."""
    manifest_path = settings.BASE_DIR / "core" / "templates" / "manifest.json"
    with open(manifest_path, encoding="utf-8") as f:
        content = f.read()
    return HttpResponse(
        content,
        content_type="application/manifest+json; charset=utf-8",
    )


@require_GET
@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
def service_worker(request):
    """Sirve el service-worker.js sin almacenamiento en cache."""
    sw_path = settings.BASE_DIR / "core" / "templates" / "service-worker.js"
    with open(sw_path, encoding="utf-8") as f:
        content = f.read()
    response = HttpResponse(
        content,
        content_type="application/javascript; charset=utf-8",
    )
    response["Service-Worker-Allowed"] = "/"
    return response


@require_GET
def offline(request):
    """Página offline mostrada cuando no hay conexión."""
    return render(request, "offline.html", status=200)
