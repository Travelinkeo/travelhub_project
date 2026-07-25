"""
Serializers para modelos de boletos
"""

from rest_framework import serializers

from core.models.anulaciones import AnulacionBoleto
from core.models.historial_boletos import HistorialCambioBoleto


class HistorialCambioBoletoSerializer:
    """Serializer para el modelo correspondiente."""
    tipo_cambio_display = serializers.CharField(source="get_tipo_cambio_display", read_only=True)
    usuario_nombre = serializers.CharField(source="usuario.get_full_name", read_only=True)

    class Meta:
        model = HistorialCambioBoleto
        """Función: Meta."""
        fields = "__all__"
        read_only_fields = ["fecha_cambio"]


class AnulacionBoletoSerializer:
    """Serializer para el modelo correspondiente."""
    estado_display = serializers.CharField(source="get_estado_display", read_only=True)
    tipo_anulacion_display = serializers.CharField(
        source="get_tipo_anulacion_display", read_only=True
    )
    solicitado_por_nombre = serializers.CharField(
        source="solicitado_por.get_full_name", read_only=True
    )
    aprobado_por_nombre = serializers.CharField(source="aprobado_por.get_full_name", read_only=True)

    class Meta:
        """Configuración del modelo."""
        model = AnulacionBoleto
        fields = "__all__"
        read_only_fields = ["fecha_solicitud", "monto_reembolso"]
