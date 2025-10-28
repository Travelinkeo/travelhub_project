from rest_framework import serializers
from core.models import TarifarioProveedor, HotelTarifario, TipoHabitacion, TarifaHabitacion
from decimal import Decimal


class TarifaHabitacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TarifaHabitacion
        fields = ['id_tarifa_habitacion', 'fecha_inicio', 'fecha_fin', 'nombre_temporada',
                  'tarifa_sgl', 'tarifa_dbl', 'tarifa_tpl', 'tarifa_cdp', 'tarifa_qpl',
                  'tarifa_sex_pax', 'tarifa_pax_adicional', 'tarifa_nino_4_10']


class TipoHabitacionSerializer(serializers.ModelSerializer):
    tarifas = TarifaHabitacionSerializer(many=True, read_only=True)
    
    class Meta:
        model = TipoHabitacion
        fields = ['id_tipo_habitacion', 'nombre', 'capacidad_adultos', 'capacidad_ninos',
                  'capacidad_total', 'descripcion', 'tarifas']


class HotelTarifarioSerializer(serializers.ModelSerializer):
    tipos_habitacion = TipoHabitacionSerializer(many=True, read_only=True)
    regimen_display = serializers.CharField(source='get_regimen_display', read_only=True)
    
    class Meta:
        model = HotelTarifario
        fields = ['id_hotel_tarifario', 'nombre', 'destino', 'ubicacion_descripcion',
                  'regimen', 'regimen_display', 'comision', 'politica_ninos',
                  'check_in', 'check_out', 'minimo_noches_temporada_baja',
                  'minimo_noches_temporada_alta', 'activo', 'tipos_habitacion']


class TarifarioProveedorSerializer(serializers.ModelSerializer):
    proveedor_nombre = serializers.CharField(source='proveedor.nombre', read_only=True)
    
    class Meta:
        model = TarifarioProveedor
        fields = ['id_tarifario_proveedor', 'proveedor', 'proveedor_nombre', 'nombre',
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
