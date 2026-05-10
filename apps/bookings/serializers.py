# apps/bookings/serializers.py
from rest_framework import serializers
from .models import TarifarioProveedor, HotelTarifario, TipoHabitacion, TarifaHabitacion
from decimal import Decimal


class TarifaHabitacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TarifaHabitacion
        fields = ['id', 'fecha_inicio', 'fecha_fin', 'nombre_temporada',
                  'tarifa_sgl', 'tarifa_dbl', 'tarifa_tpl', 'tarifa_cpl',
                  'tarifa_nino']


class TipoHabitacionSerializer(serializers.ModelSerializer):
    tarifas = TarifaHabitacionSerializer(many=True, read_only=True)
    
    class Meta:
        model = TipoHabitacion
        fields = ['id', 'nombre', 'capacidad_adultos', 'capacidad_ninos',
                  'capacidad_total', 'descripcion', 'tarifas']


class HotelTarifarioSerializer(serializers.ModelSerializer):
    tipos_habitacion = TipoHabitacionSerializer(many=True, read_only=True)
    regimen_display = serializers.CharField(source='get_regimen_default_display', read_only=True)
    
    class Meta:
        model = HotelTarifario
        fields = ['id', 'nombre', 'slug', 'destino',
                  'regimen_default', 'regimen_display', 'comision',
                  'check_in', 'check_out', 'activo', 'tipos_habitacion']


class TarifarioProveedorSerializer(serializers.ModelSerializer):
    proveedor_nombre = serializers.CharField(source='proveedor.nombre', read_only=True)
    
    class Meta:
        model = TarifarioProveedor
        fields = ['id', 'proveedor', 'proveedor_nombre', 'nombre',
                  'fecha_vigencia_inicio', 'fecha_vigencia_fin', 'comision_estandar',
                  'activo', 'fecha_carga']


class CotizacionHotelSerializer(serializers.Serializer):
    """Serializer para request de cotización"""
    destino = serializers.CharField(required=True)
    fecha_entrada = serializers.DateField(required=True)
    fecha_salida = serializers.DateField(required=True)
    habitaciones = serializers.ListField(
        child=serializers.DictField(),
        required=True,
        help_text='Lista de habitaciones: [{"tipo": "DBL", "adultos": 2, "ninos": 0}]'
    )


class ResultadoCotizacionSerializer(serializers.Serializer):
    """Serializer para response de cotización"""
    hotel = serializers.CharField()
    destino = serializers.CharField()
    regimen = serializers.CharField()
    comision = serializers.DecimalField(max_digits=5, decimal_places=2)
    total_sin_comision = serializers.DecimalField(max_digits=10, decimal_places=2)
    comision_monto = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_neto = serializers.DecimalField(max_digits=10, decimal_places=2)
    desglose = serializers.ListField()
