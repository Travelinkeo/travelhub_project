# core/api_registry.py
"""
Sistema de registro automático de APIs REST para modelos registrados en Django Admin.

Este módulo escanea los modelos registrados en admin.site y genera automáticamente
Serializers y ViewSets para exponerlos como APIs REST.
"""

import logging

from django.contrib import admin
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import permissions, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.auth_helpers import InternalAPIAuthMixin

logger = logging.getLogger(__name__)

# Registry global para almacenar las APIs generadas
api_registry = {}


class AutoModelSerializer(serializers.ModelSerializer):
    """
    Serializer genérico que usa todos los campos del modelo.
    Campos sensibles (agencia, is_deleted, deleted_at, record_hash, estado) son read-only por defecto.
    """

    class Meta:
        model = None
        fields = "__all__"
        read_only_fields = ("agencia", "is_deleted", "deleted_at", "record_hash", "estado")


@extend_schema_view(
    list=extend_schema(description="Listar todos los registros del modelo"),
    retrieve=extend_schema(description="Obtener un registro específico por ID"),
    create=extend_schema(description="Crear un nuevo registro"),
    update=extend_schema(description="Actualizar completamente un registro"),
    partial_update=extend_schema(description="Actualizar parcialmente un registro"),
    destroy=extend_schema(description="Eliminar un registro"),
)
class AutoModelViewSet(InternalAPIAuthMixin, viewsets.ModelViewSet):
    """
    ViewSet genérico para operaciones CRUD básicas.
    """

    serializer_class = None  # Se establece dinámicamente

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated(), permissions.IsAdminUser()]

    def get_queryset(self):
        from core.middleware import get_current_agency

        model = self.serializer_class.Meta.model
        agency = get_current_agency()
        qs = model.objects.all()
        if agency and hasattr(model, "agencia"):
            qs = qs.filter(agencia=agency)
        elif agency and hasattr(model, "agency"):
            qs = qs.filter(agency=agency)
        return qs

    @extend_schema(description="Obtener el conteo total de registros")
    @action(detail=False, methods=["get"])
    def count(self, request):
        """
        Endpoint para obtener el conteo total de registros.
        """
        queryset = self.get_queryset()
        count = queryset.count()
        return Response({"count": count})


def generate_api_for_model(model):
    """
    Genera Serializer y ViewSet para un modelo dado, prefiriendo uno existente si existe.
    """
    import core.serializers as core_serializers

    # Intentar buscar un serializer existente
    existing_serializer_name = f"{model.__name__}Serializer"
    SerializerClass = getattr(core_serializers, existing_serializer_name, None)

    if SerializerClass is None:
        # Custom fields for BoletoImportado si es dinámico
        if model.__name__ == "BoletoImportado":
            fields = [
                "id_boleto_importado",
                "numero_boleto",
                "nombre_pasajero_completo",
                "total_boleto",
                "fecha_subida",
                "estado_parseo",
            ]
        else:
            fields = "__all__"

        # Crear Serializer dinámicamente
        serializer_name = f"{model.__name__}Serializer"
        serializer_attrs = {
            "Meta": type(
                "Meta",
                (),
                {
                    "model": model,
                    "fields": fields,
                    "read_only_fields": (
                        "agencia",
                        "is_deleted",
                        "deleted_at",
                        "record_hash",
                        "estado",
                    ),
                },
            )
        }
        SerializerClass = type(serializer_name, (AutoModelSerializer,), serializer_attrs)

    # Crear ViewSet dinámicamente
    viewset_name = f"{model.__name__}ViewSet"
    viewset_attrs = {
        "serializer_class": SerializerClass,
    }
    ViewSetClass = type(viewset_name, (AutoModelViewSet,), viewset_attrs)

    return SerializerClass, ViewSetClass


def register_auto_apis():
    """
    Escanea admin.site y registra APIs para todos los modelos registrados.
    """
    logger.debug(
        f"Modelos en admin.site._registry: {[model.__name__ for model in admin.site._registry.keys()]}"
    )
    logger.info("Iniciando registro automático de APIs...")
    WHITELIST = {
        "AlquilerAutoReserva",
        "EventoServicio",
        "CircuitoTuristico",
        "CircuitoDia",
        "PaqueteAereo",
        "ServicioAdicionalDetalle",
        "Venta",
        "BoletoImportado",
        "SegmentoVuelo",
        "FeeVenta",
        "PagoVenta",
    }
    for model, _admin_class in admin.site._registry.items():
        # Endurecimiento de Seguridad: Solo exponer modelos autorizados
        if not getattr(model, "api_expose", False) and model.__name__ not in WHITELIST:
            logger.debug(
                f"🛡️ Seguridad: Omitiendo auto-registro de API para el modelo {model.__name__} (sin api_expose=True)."
            )
            continue

        if model not in api_registry:
            try:
                serializer, viewset = generate_api_for_model(model)
                # Mapping for consistent basenames (matching tests)
                # Format: 'ModelName': ('singular-basename', 'plural-path')
                BASENAME_MAP = {
                    "AlquilerAutoReserva": ("alquiler-auto", "alquileres-autos"),
                    "EventoServicio": ("evento-servicio", "eventos-servicios"),
                    "CircuitoTuristico": ("circuito-turistico", "circuitos-turisticos"),
                    "CircuitoDia": ("circuito-dia", "circuitos-dias"),
                    "PaqueteAereo": ("paquete-aereo", "paquetes-aereos"),
                    "ServicioAdicionalDetalle": (
                        "servicio-adicional-detalle",
                        "servicios-adicionales",
                    ),
                    "Venta": ("venta", "ventas"),
                    "BoletoImportado": ("boletos-importados", "boletos-importados"),
                    "SegmentoVuelo": ("segmento-vuelo", "segmentos-vuelo"),
                    "FeeVenta": ("fee-venta", "fees-venta"),
                    "PagoVenta": ("pago-venta", "pagos-venta"),
                }

                if model.__name__ in BASENAME_MAP:
                    basename, path = BASENAME_MAP[model.__name__]
                else:
                    basename = model._meta.model_name
                    path = model._meta.model_name + "s"  # Default pluralization

                api_registry[model] = {
                    "serializer": serializer,
                    "viewset": viewset,
                    "basename": basename,
                    "path": path,
                }
                logger.info(f"API registrada para {model.__name__} con basename: {basename}")
            except Exception as e:
                logger.error(f"Error generando API para {model.__name__}: {e}")
    logger.info(f"Total APIs en registry: {len(api_registry)}")
    logger.debug(f"Basenames registrados: {[api['basename'] for api in api_registry.values()]}")


def get_registered_apis():
    """
    Retorna un diccionario con todas las APIs registradas.
    """
    return api_registry
