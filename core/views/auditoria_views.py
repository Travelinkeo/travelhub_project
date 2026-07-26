# core/views/auditoria_views.py
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.auth_helpers import internal_auth
from core.models.audit import AuditLog


@extend_schema(
    description="Obtiene el historial completo de auditoría para una venta específica, con timeline de eventos.",
    parameters=[
        {
            "name": "venta_id",
            "in": "path",
            "required": True,
            "schema": {"type": "integer"},
            "description": "ID de la venta a auditar",
        },
    ],
    responses={200: {"description": "Timeline de auditoría con todos los eventos registrados"}},
    tags=["Auditoría"],
)
@api_view(["GET"])
@internal_auth
@permission_classes([IsAuthenticated])
def historial_venta(request, venta_id):
    """
    Obtiene el historial completo de auditoría para una venta específica.
    """
    logs = AuditLog.objects.filter(venta_id=venta_id).order_by("-creado")

    timeline = []
    for log in logs:
        timeline.append(
            {
                "id": log.id_audit_log,
                "fecha": log.creado.isoformat(),
                "accion": log.accion,
                "modelo": log.modelo,
                "descripcion": log.descripcion,
                "datos_previos": log.datos_previos,
                "datos_nuevos": log.datos_nuevos,
                "metadata": log.metadata_extra,
            }
        )

    return Response({"venta_id": venta_id, "total_eventos": len(timeline), "timeline": timeline})


@extend_schema(
    description="Estadísticas generales de auditoría: distribución de acciones y modelos más auditados.",
    responses={200: {"description": "Estadísticas de auditoría con total de registros"}},
    tags=["Auditoría"],
)
@api_view(["GET"])
@internal_auth
@permission_classes([IsAuthenticated])
def estadisticas_auditoria(request):
    """
    Estadísticas generales de auditoría.
    """
    from django.db.models import Count

    por_accion = list(
        AuditLog.objects.values("accion").annotate(count=Count("id_audit_log")).order_by("-count")
    )

    por_modelo = list(
        AuditLog.objects.values("modelo").annotate(count=Count("id_audit_log")).order_by("-count")
    )

    return Response(
        {
            "por_accion": por_accion,
            "por_modelo": por_modelo,
            "total_registros": AuditLog.objects.count(),
        }
    )


@extend_schema(
    description="Obtiene los registros de auditoría filtrados por modelo y object_id.",
    parameters=[
        {
            "name": "modelo",
            "in": "query",
            "required": True,
            "schema": {"type": "string"},
            "description": "Nombre del modelo",
        },
        {
            "name": "object_id",
            "in": "query",
            "required": True,
            "schema": {"type": "string"},
            "description": "ID del objeto",
        },
    ],
    responses={200: {"description": "Lista de registros de auditoría"}},
    tags=["Auditoría"],
)
@api_view(["GET"])
@internal_auth
@permission_classes([IsAuthenticated])
def api_audit_logs(request):
    """api_audit_logs."""
    modelo = request.GET.get("modelo")
    object_id = request.GET.get("object_id")
    if not modelo or not object_id:
        return Response([])

    qs = AuditLog.objects.filter(modelo=modelo, object_id=str(object_id)).order_by("-creado")

    # Aplicar filtrado por la agencia activa del usuario
    from core.security import get_user_active_agency

    agencia = get_user_active_agency(request.user)
    if agencia:
        qs = qs.filter(agencia=agencia)

    data = []
    for log in qs:
        data.append(
            {
                "id_audit_log": log.id_audit_log,
                "modelo": log.modelo,
                "object_id": log.object_id,
                "accion": log.accion,
                "descripcion": log.descripcion,
                "datos_previos": log.datos_previos or {},
                "datos_nuevos": log.datos_nuevos or {},
                "metadata_extra": log.metadata_extra,
                "creado": log.creado.isoformat(),
            }
        )
    return Response(data)
