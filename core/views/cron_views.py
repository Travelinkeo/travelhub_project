"""
Endpoints para tareas programadas via HTTP (cron-job.org).
Reemplazo gratuito de Celery Beat.
"""

import logging

from django.core.management import call_command
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from core.models.cron_api_key import CronApiKey

logger = logging.getLogger(__name__)


def verificar_cron_token(request):
    """Verifica que el request tenga un CronApiKey valido y establece agency_context."""

    token = request.headers.get("X-Cron-Token") or request.GET.get("token")
    if not token:
        return False
    cron_key = CronApiKey.verify(token)
    if cron_key is None:
        return False
    if cron_key.agencia:
        request._cron_agency = cron_key.agencia
    else:
        request._cron_agency = "system"
    return True


def _get_cron_context_manager(request):
    """Retorna el context manager apropiado segÃºn el tipo de CronApiKey."""
    from core.middleware import agency_context, system_context

    agency = getattr(request, "_cron_agency", None)
    if agency == "system":
        return system_context()
    elif agency:
        return agency_context(agency)
    return system_context()


@extend_schema(exclude=True)
@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def sincronizar_bcv_cron(request):
    """
    Sincroniza tasa BCV.
    URL: https://travelhub.cc/api/cron/sincronizar-bcv/?token=YOUR_TOKEN
    """
    if not verificar_cron_token(request):
        return Response({"error": "Token invÃ¡lido"}, status=403)

    try:
        with _get_cron_context_manager(request):
            call_command("sincronizar_tasa_bcv")
            logger.info("Tasa BCV sincronizada exitosamente vÃ­a cron")
            return Response({"status": "success", "message": "Tasa BCV sincronizada"})
    except Exception as e:
        logger.error(f"Error sincronizando BCV: {e}")
        return Response({"status": "error", "message": "Error interno del servidor"}, status=500)


@extend_schema(exclude=True)
@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def enviar_recordatorios_cron(request):
    """
    EnvÃ­a recordatorios de pago.
    URL: https://travelhub.cc/api/cron/recordatorios-pago/?token=YOUR_TOKEN
    """
    if not verificar_cron_token(request):
        return Response({"error": "Token invÃ¡lido"}, status=403)

    try:
        with _get_cron_context_manager(request):
            from datetime import timedelta

            from django.utils import timezone

            from apps.bookings.models import Venta

            fecha_limite = timezone.now() - timedelta(days=3)
            ventas_pendientes = Venta.objects.filter(
                estado__in=["PEN", "PAR"], saldo_pendiente__gt=0, modificado__lte=fecha_limite
            ).count()

            logger.info(f"Recordatorios verificados: {ventas_pendientes} ventas pendientes")
            return Response(
                {
                    "status": "success",
                    "message": f"{ventas_pendientes} ventas con pago pendiente detectadas",
                    "note": "Modo verificaciÃ³n - configura EMAIL_HOST_USER para enviar emails",
                }
            )
    except Exception as e:
        logger.error(f"Error verificando recordatorios: {e}")
        return Response({"status": "error", "message": "Error interno del servidor"}, status=500)


@extend_schema(exclude=True)
@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def cierre_mensual_cron(request):
    """
    Ejecuta cierre contable mensual.
    URL: https://travelhub.cc/api/cron/cierre-mensual/?token=YOUR_TOKEN
    """
    if not verificar_cron_token(request):
        return Response({"error": "Token invÃ¡lido"}, status=403)

    try:
        with _get_cron_context_manager(request):
            from apps.contabilidad.management.commands.cierre_mensual import Command

            command = Command()
            command.handle()
            logger.info("Cierre mensual ejecutado exitosamente vÃ­a cron")
            return Response({"status": "success", "message": "Cierre mensual completado"})
    except Exception as e:
        logger.error(f"Error en cierre mensual: {e}")
        return Response({"status": "error", "message": "Error interno del servidor"}, status=500)


@extend_schema(exclude=True)
@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    """Health check para monitoreo (sin token requerido)."""
    return Response({"status": "ok"})


@extend_schema(exclude=True)
@api_view(["POST"])
@permission_classes([AllowAny])
@csrf_exempt  # CSRF exempt: secured by verificar_cron_token() check below
def cargar_catalogos_cron(request):
    """
    Carga catÃ¡logos iniciales (paÃ­ses, ciudades, monedas, aerolÃ­neas).
    URL: https://travelhub.cc/api/cron/cargar-catalogos/?token=YOUR_TOKEN
    """
    if not verificar_cron_token(request):
        return Response({"error": "Token invÃ¡lido"}, status=403)

    try:
        with _get_cron_context_manager(request):
            resultados = {}

            call_command("load_catalogs")
            resultados["catalogos"] = "PaÃ­ses, ciudades, monedas cargados"

            call_command("cargar_aerolineas")
            resultados["aerolineas"] = "25 aerolÃ­neas cargadas"

            logger.info("CatÃ¡logos cargados exitosamente vÃ­a cron")
            return Response(
                {
                    "status": "success",
                    "message": "CatÃ¡logos cargados correctamente",
                    "detalles": resultados,
                }
            )
    except Exception as e:
        logger.error(f"Error cargando catÃ¡logos: {e}")
        return Response({"status": "error", "message": "Error interno del servidor"}, status=500)
