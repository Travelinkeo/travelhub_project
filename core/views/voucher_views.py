# core/views/voucher_views.py
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.http import HttpResponse

from core.models import Venta
from core.services.pdf_service import generar_pdf_voucher_unificado
from core.throttling import ReportesRateThrottle


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([ReportesRateThrottle])
def generar_voucher(request, venta_id):
    """
    Genera un voucher unificado en PDF para una venta específica.
    """
    try:
        venta = Venta.objects.get(pk=venta_id)
    except Venta.DoesNotExist:
        return Response({'error': 'Venta no encontrada'}, status=status.HTTP_404_NOT_FOUND)
    
    pdf_bytes, filename = generar_pdf_voucher_unificado(venta.pk)
    
    if pdf_bytes:
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    else:
        return Response(
            {'error': 'No se pudo generar el voucher'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
