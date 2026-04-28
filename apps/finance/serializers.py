from rest_framework import serializers
from apps.finance.models.reconciliacion import (
    ReporteReconciliacion,
    LineaReporteReconciliacion,
    ConciliacionBoleto
)

class LineaReporteReconciliacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LineaReporteReconciliacion
        fields = '__all__'

class ConciliacionBoletoSerializer(serializers.ModelSerializer):
    linea_reporte = LineaReporteReconciliacionSerializer(read_only=True)
    boleto_local_display = serializers.SerializerMethodField()
    sugerencia_asiento_display = serializers.SerializerMethodField()

    class Meta:
        model = ConciliacionBoleto
        fields = '__all__'

    def get_boleto_local_display(self, obj):
        if obj.boleto_local:
            return f"Boleto {obj.boleto_local.id_boleto} ({obj.boleto_local.archivo_origen})"
        return None

    def get_sugerencia_asiento_display(self, obj):
        if obj.sugerencia_asiento:
            return f"Asiento {obj.sugerencia_asiento.id} - {obj.sugerencia_asiento.descripcion}"
        return None

class ReporteReconciliacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReporteReconciliacion
        fields = '__all__'
        read_only_fields = ('estado', 'datos_extraidos', 'resumen_conciliacion', 'error_log', 'proveedor')
