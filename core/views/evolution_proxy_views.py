"""
Proxy inverso para Evolution Manager UI.
Intencionalmente sync: debe relajar la respuesta HTTP de Evolution Manager
de vuelta al cliente en el mismo request-response cycle de Django.
No es posible async-ificar esto en WSGI (no soporta streaming reverso).
"""

import logging
import re

import requests
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseServerError
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from apps.communications.services.evolution_api_service import EvolutionService

logger = logging.getLogger(__name__)

# Patrón seguro para instance_name: solo alfanuméricos, guiones y guiones bajos
INSTANCE_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")


@login_required  # CSRF exempt: secured by @login_required + instance_name + agency validation
@csrf_exempt
@require_http_methods(["GET", "POST"])
def evolution_manager_proxy(request, instance_name):
    """
    Proxy reverso para el Evolution Manager UI.
    Sirve la pagina de QR del Evolution Manager como si fuera parte del portal,
    evitando problemas de CORS/origen cruzado con iframes.

    GET /whatsapp/qr/{instance_name}/ → Evolution Manager QR page
    GET /whatsapp/qr/{instance_name}/assets/... → Evolution static assets
    """
    # FIX SEGURIDAD: Validar instance_name contra SSRF
    if not INSTANCE_NAME_PATTERN.match(instance_name):
        logger.warning(f"Instance name inválido rechazado: {instance_name}")
        return HttpResponse("Nombre de instancia inválido", status=400)

    # Seguridad: validar que el instance_name corresponde a la agencia del usuario
    agencia = getattr(request, "agencia", None)
    if agencia and not request.user.is_superuser:
        expected_slug = (
            agencia.subdominio_slug
            if hasattr(agencia, "subdominio_slug")
            else agencia.nombre.lower().replace(" ", "-")
        )
        if instance_name != expected_slug:
            logger.warning(
                f"Intento de acceso no autorizado al WhatsApp instance {instance_name} por usuario de agencia {agencia.nombre}"
            )
            return HttpResponse("No autorizado", status=403)

    base_url = EvolutionService._get_base_url()

    # Extraer el path de forma robusta ignorando cualquier prefijo como /system/
    marker = f"/whatsapp/qr/{instance_name}"
    idx = request.path.find(marker)
    if idx != -1:
        path = request.path[idx + len(marker) :]
    else:
        path = "/"
    if not path:
        path = "/"

    target_url = f"{base_url}/manager/qr/{instance_name}{path}"

    if request.META.get("QUERY_STRING"):
        from urllib.parse import parse_qs, urlencode

        allowed_params = [
            k for k in parse_qs(request.META["QUERY_STRING"]) if k in ("refresh", "reconnect")
        ]
        if allowed_params:
            target_url += "?" + urlencode(
                [
                    (k, v)
                    for k, v in parse_qs(request.META["QUERY_STRING"]).items()
                    if k in allowed_params
                ]
            )

    headers = EvolutionService._get_headers()
    del headers["Content-Type"]

    try:
        if request.method == "GET":
            resp = requests.get(target_url, headers=headers, timeout=15, allow_redirects=True)
        elif request.method == "POST":
            body = request.body
            resp = requests.post(
                target_url, data=body, headers=headers, timeout=15, allow_redirects=True
            )
        else:
            return HttpResponse(status=405)

        content = resp.content
        content_type = resp.headers.get("Content-Type", "text/html")

        if "text/html" in content_type:
            text = resp.text

            # Obtener el prefijo del proxy de forma dinámica usando reverse
            try:
                from django.urls import reverse

                prefix_url = reverse(
                    "core:evolution_qr_proxy", kwargs={"instance_name": instance_name}
                )
            except Exception as e:
                logger.warning("No se pudo resolver reverse para %s: %s", instance_name, e)
                prefix_url = f"/system/whatsapp/qr/{instance_name}/"

            if not prefix_url.endswith("/"):
                prefix_url += "/"

            text = text.replace("/assets/", f"{prefix_url}assets/")
            text = text.replace("/evolution/", f"{prefix_url}evolution/")
            content = text.encode("utf-8")

        response = HttpResponse(content, status=resp.status_code, content_type=content_type)

        for header in ["Cache-Control", "ETag", "Last-Modified"]:
            if header in resp.headers:
                response[header] = resp.headers[header]

        return response

    except requests.RequestException as e:
        logger.error(f"Evolution proxy error: {e}")
        return HttpResponseServerError("Evolution Manager no disponible")
