from decimal import Decimal

from rest_framework import serializers

from apps.common.models import Moneda
from apps.crm.serializers import CoreClienteSerializer

from .models import Factura, ItemFactura, Pago


class MonedaSerializer(serializers.ModelSerializer):
    """MonedaSerializer."""

    class Meta:
        model = Moneda
        fields = ["id", "codigo_iso", "nombre", "simbolo", "es_moneda_local"]


class ItemFacturaSerializer(serializers.ModelSerializer):
    """ItemFacturaSerializer."""

    class Meta:
        model = ItemFactura
        fields = [
            "id",
            "factura",
            "descripcion",
            "cantidad",
            "precio_unitario_usd",
            "exento",
            "total_linea_usd",
        ]
        read_only_fields = ("total_linea_usd",)
        extra_kwargs = {"factura": {"write_only": True, "required": False}}


class FacturaSerializer(serializers.ModelSerializer):
    """FacturaSerializer."""

    items = ItemFacturaSerializer(many=True, required=False)
    cliente_detalle = CoreClienteSerializer(source="cliente", read_only=True)
    estado_display = serializers.CharField(source="get_estado_display", read_only=True)

    class Meta:
        model = Factura
        fields = [
            "id",
            "numero_control",
            "cliente",
            "cliente_detalle",
            "fecha_emision",
            "tasa_bcv_aplicada",
            "subtotal_usd",
            "subtotal_ves",
            "total_iva_usd",
            "total_iva_ves",
            "total_igtf_usd",
            "total_igtf_ves",
            "gran_total_usd",
            "gran_total_ves",
            "estado",
            "estado_display",
            "items",
        ]
        extra_kwargs = {
            "cliente": {"allow_null": True, "required": False},
        }

    def create(self, validated_data):
        """create."""
        items_data = validated_data.pop("items", [])
        factura = Factura.objects.create(**validated_data)

        items_to_create = []
        for item_data in items_data:
            item = ItemFactura(factura=factura, **item_data)
            item.total_linea_usd = (item.precio_unitario_usd * item.cantidad).quantize(
                Decimal("0.0001")
            )
            items_to_create.append(item)

        if items_to_create:
            ItemFactura.objects.bulk_create(items_to_create)

        return factura

    def update(self, instance, validated_data):
        """update."""
        items_data = validated_data.pop("items", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if items_data is not None:
            instance.items.all().delete()
            for item_data in items_data:
                item_data["total_linea_usd"] = (
                    item_data["precio_unitario_usd"] * item_data["cantidad"]
                ).quantize(Decimal("0.0001"))
                ItemFactura.objects.create(factura=instance, **item_data)

        return instance


class PagoSerializer(serializers.ModelSerializer):
    """PagoSerializer."""

    class Meta:
        model = Pago
        fields = [
            "id",
            "factura",
            "monto_usd",
            "monto_ves",
            "metodo_pago",
            "referencia",
            "fecha_pago",
        ]
