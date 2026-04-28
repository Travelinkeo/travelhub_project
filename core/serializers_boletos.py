"""
Serializers para modelos de boletos
"""
from rest_framework import serializers
from core.models.historial_boletos import HistorialCambioBoleto
from core.models.anulaciones import AnulacionBoleto


class HistorialCambioBoletoSerializer(serializers.ModelSerializer):
    tipo_cambio_display = serializers.CharField(source='get_tipo_cambio_display', read_only=True)
    usuario_nombre = serializers.CharField(source='usuario.get_full_name', read_only=True)
    
    class Meta:
        model = HistorialCambioBoleto
        fields = '__all__'
        read_only_fields = ['fecha_cambio']


class AnulacionBoletoSerializer(serializers.ModelSerializer):
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    tipo_anulacion_display = serializers.CharField(source='get_tipo_anulacion_display', read_only=True)
    solicitado_por_nombre = serializers.CharField(source='solicitado_por.get_full_name', read_only=True)
    aprobado_por_nombre = serializers.CharField(source='aprobado_por.get_full_name', read_only=True)
    
    class Meta:
        model = AnulacionBoleto
        fields = '__all__'
        read_only_fields = ['fecha_solicitud', 'monto_reembolso']
