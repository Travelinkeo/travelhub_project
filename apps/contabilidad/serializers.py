"""Serializadores para la API de contabilidad.
"""

from rest_framework import serializers

from apps.contabilidad.models import (
    AsientoContable,
    MovimientoContable,
)
from apps.finance.serializers import MonedaSerializer


class MovimientoContableSerializer:
    """Serializador para movimientocontable. Uso: instanciar según necesidad del dominio.
    """
    cuenta_contable_codigo = serializers.CharField(
        source="cuenta_contable.codigo_cuenta", read_only=True
    )
    cuenta_contable_nombre = serializers.CharField(
        source="cuenta_contable.nombre_cuenta", read_only=True
    )

    class Meta:
        model = MovimientoContable
        fields = [
            "id_detalle_asiento",
            "linea",
            "cuenta_contable",
            "cuenta_contable_codigo",
            "cuenta_contable_nombre",
            "descripcion_linea",
            "debe",
            "haber",
        ]
        extra_kwargs = {"asiento": {"write_only": True, "required": False}}


class AsientoContableSerializer:
    """Serializador para asientocontable. Uso: instanciar según necesidad del dominio.
    """
    detalles_asiento = MovimientoContableSerializer(many=True)
    moneda_detalle = MonedaSerializer(source="moneda", read_only=True)
    estado_display = serializers.CharField(source="get_estado_display", read_only=True)
    tipo_asiento_display = serializers.CharField(source="get_tipo_asiento_display", read_only=True)
    esta_cuadrado = serializers.BooleanField(read_only=True)

    class Meta:
        model = AsientoContable
        fields = [
            "id_asiento",
            "id",
            "fecha_contable",
            "descripcion_general",
            "tipo_asiento",
            "tipo_asiento_display",
            "referencia_documento",
            "estado",
            "estado_display",
            "moneda",
            "moneda_detalle",
            "tasa_cambio_aplicada",
            "total_debe",
            "total_haber",
            "esta_cuadrado",
            "fecha_creacion",
            "detalles_asiento",
        ]
        read_only_fields = (
            "id",
            "total_debe",
            "total_haber",
            "fecha_creacion",
            "esta_cuadrado",
        )
        extra_kwargs = {"moneda": {"write_only": True, "allow_null": False, "required": True}}

    def create(self, validated_data):
        # create: Create. Args: según implementación. Returns: según implementación.
        detalles_data = validated_data.pop("detalles_asiento", [])
        asiento = AsientoContable.objects.create(**validated_data)

        detalles_to_create = [
            MovimientoContable(asiento=asiento, **detalle_data) for detalle_data in detalles_data
        ]
        if detalles_to_create:
            MovimientoContable.objects.bulk_create(detalles_to_create)

        asiento.calcular_totales()
        return asiento

    def update(self, instance, validated_data):
        # update: Update. Args: según implementación. Returns: según implementación.
        detalles_data = validated_data.pop("detalles_asiento", None)
        instance.fecha_contable = validated_data.get("fecha_contable", instance.fecha_contable)
        instance.descripcion_general = validated_data.get(
            "descripcion_general", instance.descripcion_general
        )
        instance.tipo_asiento = validated_data.get("tipo_asiento", instance.tipo_asiento)
        instance.moneda = validated_data.get("moneda", instance.moneda)
        instance.tasa_cambio_aplicada = validated_data.get(
            "tasa_cambio_aplicada", instance.tasa_cambio_aplicada
        )
        instance.referencia_documento = validated_data.get(
            "referencia_documento", instance.referencia_documento
        )
        instance.save()

        if detalles_data is not None:
            instance.detalles_asiento.all().delete()
            detalles_to_create = [
                MovimientoContable(asiento=instance, **detalle_data)
                for detalle_data in detalles_data
            ]
            if detalles_to_create:
                MovimientoContable.objects.bulk_create(detalles_to_create)

        instance.calcular_totales()
        return instance
