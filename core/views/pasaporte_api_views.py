# core/views/pasaporte_api_views.py
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.crm.models import Cliente, PasaporteEscaneado
from core.api.mixins.tenant import TenantViewSetMixin
from core.auth_helpers import InternalAPIAuthMixin
from core.serializers import PasaporteEscaneadoSerializer


@extend_schema_view(
    list=extend_schema(description="Listar todos los pasaportes escaneados por OCR."),
    retrieve=extend_schema(description="Obtener detalle de un pasaporte escaneado."),
    create=extend_schema(description="Registrar un nuevo pasaporte escaneado."),
    update=extend_schema(description="Actualizar datos de un pasaporte."),
    partial_update=extend_schema(description="Actualizar parcialmente datos de un pasaporte."),
    destroy=extend_schema(description="Eliminar un registro de pasaporte."),
    verificar=extend_schema(
        description="Marcar un pasaporte como verificado manualmente.",
        responses={200: {"description": "Pasaporte verificado exitosamente"}},
    ),
    crear_cliente=extend_schema(
        description="Crear o actualizar un cliente desde los datos del pasaporte escaneado.",
        responses={
            201: {"description": "Cliente creado exitosamente"},
            200: {"description": "Cliente actualizado exitosamente"},
        },
    ),
    pendientes=extend_schema(
        description="Listar pasaportes sin cliente asociado.",
        responses={200: PasaporteEscaneadoSerializer(many=True)},
    ),
    baja_confianza=extend_schema(
        description="Listar pasaportes con baja confianza OCR que requieren revisión manual.",
        responses={200: PasaporteEscaneadoSerializer(many=True)},
    ),
)
class PasaporteEscaneadoViewSet(InternalAPIAuthMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = PasaporteEscaneado.objects.all().select_related("cliente")
    serializer_class = PasaporteEscaneadoSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["verificado_manualmente", "nacionalidad", "confianza_ocr"]
    search_fields = ["numero_pasaporte", "nombres", "apellidos"]
    ordering_fields = ["fecha_procesamiento", "confianza_ocr"]
    ordering = ["-fecha_procesamiento"]

    @action(detail=True, methods=["post"])
    def verificar(self, request, pk=None):
        """Marcar pasaporte como verificado manualmente"""
        pasaporte = self.get_object()
        pasaporte.verificado_manualmente = True
        pasaporte.save()
        return Response({"status": "Pasaporte verificado"})

    @action(detail=True, methods=["post"])
    def crear_cliente(self, request, pk=None):
        """Crear o actualizar cliente desde datos del pasaporte"""
        pasaporte = self.get_object()

        if not pasaporte.es_valido:
            return Response(
                {"error": "Pasaporte no válido para crear cliente"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Buscar cliente existente
        cliente_existente = Cliente.objects.filter(
            numero_pasaporte=pasaporte.numero_pasaporte
        ).first()

        client_data = pasaporte.to_cliente_data()

        if cliente_existente:
            for key, value in client_data.items():
                if value:
                    setattr(cliente_existente, key, value)
            cliente_existente.save()
            pasaporte.cliente = cliente_existente
            pasaporte.save()
            return Response(
                {"status": "Cliente actualizado", "cliente_id": cliente_existente.id_cliente}
            )
        else:
            nuevo_cliente = Cliente.objects.create(**client_data)
            pasaporte.cliente = nuevo_cliente
            pasaporte.save()
            return Response(
                {"status": "Cliente creado", "cliente_id": nuevo_cliente.id_cliente},
                status=status.HTTP_201_CREATED,
            )

    @action(detail=False, methods=["get"])
    def pendientes(self, request):
        """Pasaportes sin cliente asociado"""
        pasaportes = self.queryset.filter(cliente__isnull=True, es_valido=True)
        serializer = self.get_serializer(pasaportes, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def baja_confianza(self, request):
        """Pasaportes con baja confianza OCR que requieren revisión"""
        umbral = float(request.query_params.get("umbral", 0.7))
        pasaportes = self.queryset.filter(confianza_ocr__lt=umbral, verificado_manualmente=False)
        serializer = self.get_serializer(pasaportes, many=True)
        return Response(serializer.data)
