# core/api_registry.py
"""
Sistema de registro automático de APIs REST para modelos registrados en Django Admin.

Este módulo escanea los modelos registrados en admin.site y genera automáticamente
Serializers y ViewSets para exponerlos como APIs REST.
"""

from django.contrib import admin
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import permissions, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

# Registry global para almacenar las APIs generadas
api_registry = {}


class AutoModelSerializer(serializers.ModelSerializer):
    """
    Serializer genérico que usa todos los campos del modelo.
    """

    class Meta:
        model = None  # Se establece dinámicamente
        fields = '__all__'


@extend_schema_view(
    list=extend_schema(description="Listar todos los registros del modelo"),
    retrieve=extend_schema(description="Obtener un registro específico por ID"),
    create=extend_schema(description="Crear un nuevo registro"),
    update=extend_schema(description="Actualizar completamente un registro"),
    partial_update=extend_schema(description="Actualizar parcialmente un registro"),
    destroy=extend_schema(description="Eliminar un registro"),
)
class AutoModelViewSet(viewsets.ModelViewSet):
    """
    ViewSet genérico para operaciones CRUD básicas.
    """
    serializer_class = None  # Se establece dinámicamente

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated(), permissions.IsAdminUser()]

    def get_queryset(self):
        model = self.serializer_class.Meta.model
        return model.objects.all()

    @extend_schema(description="Obtener el conteo total de registros")
    @action(detail=False, methods=['get'])
    def count(self, request):
        """
        Endpoint para obtener el conteo total de registros.
        """
        queryset = self.get_queryset()
        count = queryset.count()
        return Response({'count': count})


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
        if model.__name__ == 'BoletoImportado':
            fields = ['id_boleto_importado', 'numero_boleto', 'nombre_pasajero_completo', 'total_boleto', 'fecha_subida', 'estado_parseo']
        else:
            fields = '__all__'

        # Crear Serializer dinámicamente
        serializer_name = f"{model.__name__}Serializer"
        serializer_attrs = {
            'Meta': type('Meta', (), {'model': model, 'fields': fields})
        }
        SerializerClass = type(serializer_name, (AutoModelSerializer,), serializer_attrs)

    # Crear ViewSet dinámicamente
    viewset_name = f"{model.__name__}ViewSet"
    viewset_attrs = {
        'serializer_class': SerializerClass,
        'queryset': model.objects.all(),
    }
    ViewSetClass = type(viewset_name, (AutoModelViewSet,), viewset_attrs)

    return SerializerClass, ViewSetClass


def register_auto_apis():
    """
    Escanea admin.site y registra APIs para todos los modelos registrados.
    """
    print(f"Modelos en admin.site._registry: {[model.__name__ for model in admin.site._registry.keys()]}")
    print("Iniciando registro automático de APIs...")
    for model, _admin_class in admin.site._registry.items():
        if model not in api_registry:
            try:
                serializer, viewset = generate_api_for_model(model)
                # Mapping for consistent basenames (matching tests)
                # Format: 'ModelName': ('singular-basename', 'plural-path')
                BASENAME_MAP = {
                    'AlquilerAutoReserva': ('alquiler-auto', 'alquileres-autos'),
                    'EventoServicio': ('evento-servicio', 'eventos-servicios'),
                    'CircuitoTuristico': ('circuito-turistico', 'circuitos-turisticos'),
                    'CircuitoDia': ('circuito-dia', 'circuitos-dias'),
                    'PaqueteAereo': ('paquete-aereo', 'paquetes-aereos'),
                    'ServicioAdicionalDetalle': ('servicio-adicional-detalle', 'servicios-adicionales'),
                    'Venta': ('venta', 'ventas'),
                    'BoletoImportado': ('boletos-importados', 'boletos-importados'),
                    'SegmentoVuelo': ('segmento-vuelo', 'segmentos-vuelo'),
                    'FeeVenta': ('fee-venta', 'fees-venta'),
                    'PagoVenta': ('pago-venta', 'pagos-venta'),
                }
                
                if model.__name__ in BASENAME_MAP:
                    basename, path = BASENAME_MAP[model.__name__]
                else:
                    basename = model._meta.model_name
                    path = model._meta.model_name + "s" # Default pluralization
                
                api_registry[model] = {
                    'serializer': serializer,
                    'viewset': viewset,
                    'basename': basename,
                    'path': path
                }
                print(f"API registrada para {model.__name__} con basename: {basename}")
            except Exception as e:
                print(f"Error generando API para {model.__name__}: {e}")
    print(f"Total APIs en registry: {len(api_registry)}")
    print(f"Basenames registrados: {[api['basename'] for api in api_registry.values()]}")


def get_registered_apis():
    """
    Retorna un diccionario con todas las APIs registradas.
    """
    return api_registry