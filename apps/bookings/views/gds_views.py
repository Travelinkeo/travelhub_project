import json
import logging

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from ..services.pnr_parser_service import PNRParserService

logger = logging.getLogger(__name__)


@csrf_exempt
@login_required
def api_ingest_pnr_view(request):
    """
    Endpoint de ingesta rápida para procesar bloques crudos de texto de terminales GDS.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Método no permitido"}, status=405)

    try:
        # Soportamos tanto cargas de JSON nativo como formularios planos
        if request.content_type == "application/json":
            try:
                body = json.loads(request.body.decode("utf-8"))
                raw_pnr = body.get("raw_pnr", "")
            except json.JSONDecodeError:
                return JsonResponse({"error": "JSON inválido o malformado."}, status=400)
        else:
            raw_pnr = request.POST.get("raw_pnr", "")

        if not raw_pnr or not raw_pnr.strip():
            return JsonResponse(
                {"error": "El bloque de texto PNR no puede estar vacío."}, status=400
            )

        # Invocamos el servicio pasando el contexto multi-tenant del usuario logueado
        # request.user.agencia está protegida; recuperamos de request.user.agencias
        usuario_agencia = request.user.agencias.filter(activo=True).first()
        if not usuario_agencia:
            return JsonResponse(
                {"error": "El usuario no tiene una agencia activa asociada."}, status=400
            )

        agencia = usuario_agencia.agencia

        with transaction.atomic():
            venta = PNRParserService.ingerir_pnr_en_db(raw_pnr, agencia, request.user)

        return JsonResponse(
            {
                "status": "success",
                "message": "PNR procesado e indexado de manera exitosa.",
                "data": {
                    "localizador": venta.localizador,
                    "venta_id": venta.pk,
                    "pasajeros_contabilizados": venta.pasajeros.count(),
                },
            },
            status=201,
        )

    except ValueError as ve:
        logger.warning(f"Error de validación al ingerir PNR: {ve}")
        return JsonResponse({"error": str(ve)}, status=422)
    except Exception as e:
        logger.exception(f"Error interno del servidor al procesar la estructura del PNR: {e}")
        return JsonResponse(
            {"error": "Error interno del servidor al procesar la estructura del PNR."}, status=500
        )
