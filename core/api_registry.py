# core/api_registry.py
"""
Sistema de registro automático de APIs REST para modelos registrados en Django Admin.

Este módulo escanea los modelos registrados en admin.site y genera automáticamente
Serializers y ViewSets para exponerlos como APIs REST.
"""

from django.apps import apps
from django.contrib import admin
from django.db import models
from rest_framework import serializers, viewsets, permissions
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


class AutoModelViewSet(viewsets.ModelViewSet):
    """
    ViewSet genérico para operaciones CRUD básicas.
    """
    serializer_class = None  # Se establece dinámicamente
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get_queryset(self):
        model = self.serializer_class.Meta.model
        return model.objects.all()

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
    Genera Serializer y ViewSet para un modelo dado.
    """
    # Custom fields for BoletoImportado
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
    print(f"Iniciando registro automático de APIs...")
    for model, admin_class in admin.site._registry.items():
        if model not in api_registry:
            try:
                serializer, viewset = generate_api_for_model(model)
                # Custom basename for BoletoImportado
                basename = 'boletos-importados' if model.__name__ == 'BoletoImportado' else model._meta.model_name
                api_registry[model] = {
                    'serializer': serializer,
                    'viewset': viewset,
                    'basename': basename
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