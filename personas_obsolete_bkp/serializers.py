from rest_framework import serializers
from .models import Cliente, Pasajero

class ClienteSerializer(serializers.ModelSerializer):
    get_nombre_completo = serializers.ReadOnlyField()

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
    class Meta:
        model = Pasajero
        fields = '__all__'
