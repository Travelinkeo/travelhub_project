from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from django.db import models as django_models
from .models import Cliente, Pasajero, PasaporteEscaneado

class ClienteSerializer(serializers.ModelSerializer):
    get_nombre_completo = serializers.CharField(read_only=True)
    id_cliente = serializers.IntegerField(source='id', read_only=True)

    class Meta:
        model = Cliente
        fields = [
            'id_cliente', 'tipo_cliente', 'nombres', 'apellidos', 'cedula_identidad',
            'nombre_empresa', 'email', 'telefono_principal', 'fecha_nacimiento',
            'nacionalidad', 'numero_pasaporte', 'pais_emision_pasaporte',
            'fecha_expiracion_pasaporte', 'direccion', 'ciudad', 'puntos_fidelidad',
            'es_cliente_frecuente', 'get_nombre_completo'
        ]

class PasajeroSerializer(serializers.ModelSerializer):
    nombre_completo = serializers.CharField(read_only=True)
    numero_documento = serializers.CharField(read_only=True)

    class Meta:
        model = Pasajero
        fields = '__all__'

class PasaporteEscaneadoSerializer(serializers.ModelSerializer):
    es_valido = serializers.ReadOnlyField()
    nombre_completo = serializers.ReadOnlyField()

    class Meta:
        model = PasaporteEscaneado
        fields = '__all__'
