from rest_framework import serializers
from .models import Cotizacion, ItemCotizacion


class ItemCotizacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemCotizacion
        fields = '__all__'


class CotizacionSerializer(serializers.ModelSerializer):
    items = ItemCotizacionSerializer(many=True, read_only=True)
    cliente_nombre = serializers.CharField(source='cliente.get_nombre_completo', read_only=True)
    consultor_nombre = serializers.CharField(source='consultor.get_full_name', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    
    class Meta:
        model = Cotizacion
        fields = '__all__'
        
    def create(self, validated_data):
        cotizacion = super().create(validated_data)
        cotizacion.calcular_total()
        return cotizacion