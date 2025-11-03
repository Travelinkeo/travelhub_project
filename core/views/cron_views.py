"""
Endpoints para tareas programadas vía HTTP (cron-job.org).
Reemplazo gratuito de Celery Beat.
"""
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.core.management import call_command
import logging

logger = logging.getLogger(__name__)

# Token secreto para autenticar cron jobs
CRON_SECRET = settings.SECRET_KEY[:32]  # Primeros 32 caracteres del SECRET_KEY


def verificar_cron_token(request):
    """Verifica que el request venga de cron-job.org con token correcto."""
    token = request.headers.get('X-Cron-Token') or request.GET.get('token')
    return token == CRON_SECRET


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
        # Ejecutar en modo dry-run para evitar errores de email no configurado
        call_command('enviar_recordatorios_pago', '--dry-run')
        logger.info("Recordatorios verificados exitosamente vía cron (dry-run)")
        return Response({
            'status': 'success', 
            'message': 'Recordatorios verificados (dry-run mode)',
            'note': 'Configura EMAIL_HOST_USER en Render para enviar emails reales'
        })
    except Exception as e:
        logger.error(f"Error verificando recordatorios: {e}")
        return Response({'status': 'error', 'message': str(e)}, status=500)


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
        from contabilidad.management.commands.cierre_mensual import Command
        command = Command()
        command.handle()
        logger.info("Cierre mensual ejecutado exitosamente vía cron")
        return Response({'status': 'success', 'message': 'Cierre mensual completado'})
    except Exception as e:
        logger.error(f"Error en cierre mensual: {e}")
        return Response({'status': 'error', 'message': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """Health check para monitoreo (sin token requerido)."""
    return Response({'status': 'ok', 'service': 'travelhub'})
