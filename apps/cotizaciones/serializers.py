from rest_framework import serializers

from .models import Cotizacion, ItemCotizacion


class ItemCotizacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemCotizacion
        fields = [
            "id_item_cotizacion",
            "cotizacion",
            "tipo_item",
            "producto_servicio",
            "descripcion",
            "descripcion_personalizada",
            "cantidad",
            "precio_unitario",
            "subtotal_item",
            "total_item",
            "impuestos_item",
            "detalles_json",
            "costo",
            "agencia",
        ]
        read_only_fields = ["agencia"]


class CotizacionSerializer(serializers.ModelSerializer):
    items = ItemCotizacionSerializer(many=True, read_only=True)
    cliente_nombre = serializers.CharField(source="cliente.get_nombre_completo", read_only=True)
    consultor_nombre = serializers.CharField(source="consultor.get_full_name", read_only=True)
    estado_display = serializers.CharField(source="get_estado_display", read_only=True)

    class Meta:
        model = Cotizacion
        fields = [
            "id_cotizacion",
            "uuid",
            "numero_cotizacion",
            "cliente",
            "nombre_cliente_manual",
            "moneda",
            "descripcion_general",
            "destino",
            "consultor",
            "numero_pasajeros",
            "fecha_emision",
            "fecha_vencimiento",
            "total_cotizado",
            "subtotal",
            "impuestos",
            "estado",
            "estado_display",
            "terminos_pago",
            "terminos_cancelacion",
            "condiciones_comerciales",
            "notas_internas",
            "fecha_validez",
            "notas",
            "archivo_pdf",
            "gds_raw_text",
            "image_url",
            "metadata_ia",
            "agency_fee",
            "fecha_envio",
            "fecha_vista",
            "fecha_respuesta",
            "email_enviado",
            "venta_generada",
            "agencia",
            "items",
            "cliente_nombre",
            "consultor_nombre",
        ]
        read_only_fields = ["agencia", "uuid", "numero_cotizacion", "estado"]

    def create(self, validated_data):
        cotizacion = super().create(validated_data)
        cotizacion.calcular_total()
        return cotizacion
