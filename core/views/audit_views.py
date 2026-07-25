from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.auth_helpers import InternalAPIAuthMixin

from ..models import AuditLog
from ..serializers import AuditLogSerializer


@extend_schema(
    description="Consultar logs de auditoría filtrados por modelo, ID de objeto o venta.",
    parameters=[
        {
            "name": "modelo",
            "in": "query",
            "required": False,
            "schema": {"type": "string"},
            "description": "Filtrar por nombre del modelo",
        },
        {
            "name": "object_id",
            "in": "query",
            "required": False,
            "schema": {"type": "string"},
            "description": "Filtrar por ID del objeto auditado",
        },
        {
            "name": "venta_id",
            "in": "query",
            "required": False,
            "schema": {"type": "integer"},
            "description": "Filtrar por ID de venta",
        },
    ],
    responses={200: AuditLogSerializer(many=True)},
    tags=["Auditoría"],
)
class AuditLogListView(InternalAPIAuthMixin, APIView):
    """
    Vista para consultar los logs de auditoría filtrados por modelo y ID de objeto.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Método: get."""
        modelo = request.query_params.get("modelo")
        object_id = request.query_params.get("object_id")
        venta_id = request.query_params.get("venta_id")

        logs = AuditLog.objects.all().order_by("-creado")

        if modelo:
            logs = logs.filter(modelo=modelo)
        if object_id:
            logs = logs.filter(object_id=str(object_id))
        if venta_id:
            logs = logs.filter(venta_id=venta_id)

        serializer = AuditLogSerializer(logs[:100], many=True)
        return Response(serializer.data)
