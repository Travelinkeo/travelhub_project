"""
Views para monitoreo de correos de boletos
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.core.management import call_command
from io import StringIO


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def procesar_correos_boletos(request):
    """
    Endpoint para procesar correos de boletos manualmente.
    
    POST /api/procesar-correos-boletos/
    
    Ejecuta el comando monitor_tickets_email y retorna el resultado.
    """
    try:
        # Capturar output del comando
        out = StringIO()
        call_command('monitor_tickets_email', stdout=out)
        output = out.getvalue()
        
        return Response({
            'success': True,
            'message': 'Correos procesados exitosamente',
            'output': output
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
