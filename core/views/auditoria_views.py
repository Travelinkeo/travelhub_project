# core/views/auditoria_views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q

from core.models import AuditLog


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def historial_venta(request, venta_id):
    """
    Obtiene el historial completo de auditoría para una venta específica.
    """
    logs = AuditLog.objects.filter(venta_id=venta_id).order_by('-creado')
    
    timeline = []
    for log in logs:
        timeline.append({
            'id': log.id_audit_log,
            'fecha': log.creado.isoformat(),
            'accion': log.accion,
            'modelo': log.modelo,
            'descripcion': log.descripcion,
            'datos_previos': log.datos_previos,
            'datos_nuevos': log.datos_nuevos,
            'metadata': log.metadata_extra
        })
    
    return Response({
        'venta_id': venta_id,
        'total_eventos': len(timeline),
        'timeline': timeline
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def estadisticas_auditoria(request):
    """
    Estadísticas generales de auditoría.
    """
    from django.db.models import Count
    
    por_accion = list(AuditLog.objects.values('accion').annotate(
        count=Count('id_audit_log')
    ).order_by('-count'))
    
    por_modelo = list(AuditLog.objects.values('modelo').annotate(
        count=Count('id_audit_log')
    ).order_by('-count'))
    
    return Response({
        'por_accion': por_accion,
        'por_modelo': por_modelo,
        'total_registros': AuditLog.objects.count()
    })
