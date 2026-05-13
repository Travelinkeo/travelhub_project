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
    """Verifica que el request tenga un CronApiKey valido."""
    token = request.headers.get("X-Cron-Token") or request.GET.get("token")
    if not token:
        return False
    return CronApiKey.verify(token) is not None


@extend_schema(exclude=True)
@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def sincronizar_bcv_cron(request):
    """
    Sincroniza tasa BCV.
    URL: https://travelhub-project.onrender.com/api/cron/sincronizar-bcv/?token=YOUR_TOKEN
    """
    if not verificar_cron_token(request):
        return Response({'error': 'Token inválido'}, status=403)
    
    try:
        call_command('sincronizar_tasa_bcv')
        logger.info("Tasa BCV sincronizada exitosamente vía cron")
        return Response({'status': 'success', 'message': 'Tasa BCV sincronizada'})
    except Exception as e:
        logger.error(f"Error sincronizando BCV: {e}")
        return Response({'status': 'error', 'message': str(e)}, status=500)


@extend_schema(exclude=True)
@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def enviar_recordatorios_cron(request):
    """
    Envía recordatorios de pago.
    URL: https://travelhub-project.onrender.com/api/cron/recordatorios-pago/?token=YOUR_TOKEN
    """
    if not verificar_cron_token(request):
        return Response({'error': 'Token inválido'}, status=403)
    
    try:
        from datetime import timedelta

        from django.utils import timezone

        from apps.bookings.models import Venta
        
        # Contar ventas pendientes sin ejecutar el comando completo
        fecha_limite = timezone.now() - timedelta(days=3)
        ventas_pendientes = Venta.objects.filter(
            estado__in=['PEN', 'PAR'],
            saldo_pendiente__gt=0,
            modificado__lte=fecha_limite
        ).count()
        
        logger.info(f"Recordatorios verificados: {ventas_pendientes} ventas pendientes")
        return Response({
            'status': 'success', 
            'message': f'{ventas_pendientes} ventas con pago pendiente detectadas',
            'note': 'Modo verificación - configura EMAIL_HOST_USER para enviar emails'
        })
    except Exception as e:
        logger.error(f"Error verificando recordatorios: {e}")
        return Response({'status': 'error', 'message': str(e)}, status=500)


@extend_schema(exclude=True)
@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def cierre_mensual_cron(request):
    """
    Ejecuta cierre contable mensual.
    URL: https://travelhub-project.onrender.com/api/cron/cierre-mensual/?token=YOUR_TOKEN
    """
    if not verificar_cron_token(request):
        return Response({'error': 'Token inválido'}, status=403)
    
    try:
        from apps.contabilidad.management.commands.cierre_mensual import Command
        command = Command()
        command.handle()
        logger.info("Cierre mensual ejecutado exitosamente vía cron")
        return Response({'status': 'success', 'message': 'Cierre mensual completado'})
    except Exception as e:
        logger.error(f"Error en cierre mensual: {e}")
        return Response({'status': 'error', 'message': str(e)}, status=500)


@extend_schema(exclude=True)
@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """Health check para monitoreo (sin token requerido)."""
    return Response({'status': 'ok', 'service': 'travelhub'})


@extend_schema(exclude=True)
@api_view(['POST'])
@permission_classes([AllowAny])
@csrf_exempt
def cargar_catalogos_cron(request):
    """
    Carga catálogos iniciales (países, ciudades, monedas, aerolíneas).
    URL: https://travelhub-project.onrender.com/api/cron/cargar-catalogos/?token=YOUR_TOKEN
    """
    if not verificar_cron_token(request):
        return Response({'error': 'Token inválido'}, status=403)
    
    try:
        resultados = {}
        
        # Cargar catálogos básicos
        call_command('load_catalogs')
        resultados['catalogos'] = 'Países, ciudades, monedas cargados'
        
        # Cargar aerolíneas
        call_command('cargar_aerolineas')
        resultados['aerolineas'] = '25 aerolíneas cargadas'
        
        logger.info("Catálogos cargados exitosamente vía cron")
        return Response({
            'status': 'success',
            'message': 'Catálogos cargados correctamente',
            'detalles': resultados
        })
    except Exception as e:
        logger.error(f"Error cargando catálogos: {e}")
        return Response({'status': 'error', 'message': str(e)}, status=500)
