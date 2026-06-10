from decimal import Decimal

from rest_framework import serializers

from apps.crm.serializers import CoreClienteSerializer
from apps.finance.models import (
    DocumentoExportacionConsolidado,
    Factura,
    FacturaConsolidada,
    ItemFactura,
    ItemFacturaConsolidada,
    PropuestaTransaccionIA,
)
from apps.finance.models.currencies import Moneda, TipoCambio
from apps.finance.models.reconciliacion import (
    ConciliacionBoleto,
    LineaReporteReconciliacion,
    ReporteReconciliacion,
)


class MonedaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Moneda
        fields = ["id_moneda", "nombre", "codigo_iso", "simbolo", "es_moneda_local"]


class TipoCambioSerializer(serializers.ModelSerializer):
    moneda_origen_detalle = MonedaSerializer(source="moneda_origen", read_only=True)
    moneda_destino_detalle = MonedaSerializer(source="moneda_destino", read_only=True)

    class Meta:
        model = TipoCambio
        fields = [
            "id_tipo_cambio",
            "moneda_origen",
            "moneda_destino",
            "fecha_efectiva",
            "tasa_conversion",
            "moneda_origen_detalle",
            "moneda_destino_detalle",
        ]


class ItemFacturaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemFactura
        fields = ["id_item_factura", "descripcion", "cantidad", "precio_unitario", "subtotal_item"]
        read_only_fields = ("subtotal_item",)
        extra_kwargs = {"factura": {"write_only": True, "required": False}}


class FacturaSerializer(serializers.ModelSerializer):
    items_factura = ItemFacturaSerializer(many=True)
    cliente_detalle = CoreClienteSerializer(source="cliente", read_only=True)
    moneda_detalle = MonedaSerializer(source="moneda", read_only=True)
    venta_asociada_numero = serializers.CharField(
        source="venta_asociada.localizador", read_only=True, allow_null=True
    )
    estado_display = serializers.CharField(source="get_estado_display", read_only=True)

    class Meta:
        model = Factura
        fields = [
            "id_factura",
            "numero_factura",
            "venta_asociada",
            "venta_asociada_numero",
            "cliente",
            "cliente_detalle",
            "fecha_emision",
            "fecha_vencimiento",
            "moneda",
            "moneda_detalle",
            "subtotal",
            "monto_impuestos",
            "monto_total",
            "saldo_pendiente",
            "estado",
            "estado_display",
            "asiento_contable_factura",
            "notas",
            "items_factura",
            "archivo_pdf",
        ]
        read_only_fields = ("numero_factura", "monto_total", "saldo_pendiente")
        extra_kwargs = {
            "cliente": {"write_only": True, "allow_null": False, "required": True},
            "moneda": {"write_only": True, "allow_null": False, "required": True},
            "venta_asociada": {"allow_null": True, "required": False},
            "asiento_contable_factura": {"allow_null": True, "required": False},
        }

    def create(self, validated_data):
        items_data = validated_data.pop("items_factura", [])
        factura = Factura.objects.create(**validated_data)

        # Bulk create items with pre-calculated subtotal
        items_to_create = []
        for item_data in items_data:
            item = ItemFactura(factura=factura, **item_data)
            item.subtotal_item = (item.precio_unitario * item.cantidad).quantize(Decimal("0.01"))
            items_to_create.append(item)

        if items_to_create:
            ItemFactura.objects.bulk_create(items_to_create)
            # Recalculate taxes once after all items created
            if hasattr(factura, "calcular_impuestos_venezuela"):
                factura.calcular_impuestos_venezuela()
            else:
                factura.recalcular_totales()
                factura.save()

        return factura

    def update(self, instance, validated_data):
        items_data = validated_data.pop("items_factura", None)
        instance.venta_asociada = validated_data.get("venta_asociada", instance.venta_asociada)
        instance.cliente = validated_data.get("cliente", instance.cliente)
        instance.fecha_emision = validated_data.get("fecha_emision", instance.fecha_emision)
        instance.fecha_vencimiento = validated_data.get(
            "fecha_vencimiento", instance.fecha_vencimiento
        )
        instance.moneda = validated_data.get("moneda", instance.moneda)
        instance.subtotal = validated_data.get("subtotal", instance.subtotal)
        instance.monto_impuestos = validated_data.get("monto_impuestos", instance.monto_impuestos)
        instance.estado = validated_data.get("estado", instance.estado)
        instance.asiento_contable_factura = validated_data.get(
            "asiento_contable_factura", instance.asiento_contable_factura
        )
        instance.notas = validated_data.get("notas", instance.notas)
        instance.save()

        if items_data is not None:
            instance.items_factura.all().delete()
            for item_data in items_data:
                ItemFactura.objects.create(factura=instance, **item_data)

        return instance


class LineaReporteReconciliacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LineaReporteReconciliacion
        fields = [
            "id_linea",
            "reporte",
            "numero_boleto_reportado",
            "tarifa_base_cobrada",
            "impuestos_cobrados",
            "comision_cedida",
            "total_cobrado",
            "raw_data",
            "agencia",
            "is_deleted",
            "deleted_at",
        ]
        read_only_fields = ["agencia", "is_deleted", "deleted_at"]


class ConciliacionBoletoSerializer(serializers.ModelSerializer):
    linea_reporte = LineaReporteReconciliacionSerializer(read_only=True)
    boleto_local_display = serializers.SerializerMethodField()
    sugerencia_asiento_display = serializers.SerializerMethodField()

    class Meta:
        model = ConciliacionBoleto
        fields = [
            "id_conciliacion",
            "reporte",
            "linea_reporte",
            "boleto_local",
            "estado",
            "diferencia_tarifa",
            "diferencia_impuestos",
            "diferencia_total",
            "sugerencia_asiento",
            "ia_razonamiento",
            "resolucion_notas",
            "boleto_local_display",
            "sugerencia_asiento_display",
            "agencia",
            "is_deleted",
            "deleted_at",
        ]
        read_only_fields = ["agencia", "is_deleted", "deleted_at", "estado"]

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
        fields = [
            "id_reporte",
            "archivo",
            "fecha_subida",
            "proveedor",
            "periodo_inicio",
            "periodo_fin",
            "estado",
            "datos_extraidos",
            "resumen_conciliacion",
            "error_log",
            "agencia",
            "is_deleted",
            "deleted_at",
        ]
        read_only_fields = (
            "estado",
            "datos_extraidos",
            "resumen_conciliacion",
            "error_log",
            "proveedor",
            "agencia",
            "is_deleted",
            "deleted_at",
        )


# =======================================================
# FACTURACIÓN CONSOLIDADA (MIGRADO DE CORE)
# =======================================================


class ItemFacturaConsolidadaSerializer(serializers.ModelSerializer):
    """Serializer para items de factura consolidada"""

    class Meta:
        model = ItemFacturaConsolidada
        fields = [
            "id_item_factura",
            "descripcion",
            "cantidad",
            "precio_unitario",
            "subtotal_item",
            "tipo_servicio",
            "es_gravado",
            "alicuota_iva",
            "nombre_pasajero",
            "numero_boleto",
            "itinerario",
            "codigo_aerolinea",
        ]
        read_only_fields = ("subtotal_item",)


class DocumentoExportacionConsolidadoSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentoExportacionConsolidado
        fields = ["id", "factura", "tipo_documento", "numero_documento", "archivo", "fecha_subida"]
        read_only_fields = ["fecha_subida"]


class FacturaConsolidadaSerializer(serializers.ModelSerializer):
    """Serializer para factura consolidada con normativa venezolana"""

    items_factura = ItemFacturaConsolidadaSerializer(many=True, required=False)
    documentos_exportacion = DocumentoExportacionConsolidadoSerializer(many=True, read_only=True)
    cliente_detalle = CoreClienteSerializer(source="cliente", read_only=True)
    moneda_detalle = MonedaSerializer(source="moneda", read_only=True)
    venta_asociada_numero = serializers.CharField(
        source="venta_asociada.localizador", read_only=True, allow_null=True
    )
    estado_display = serializers.CharField(source="get_estado_display", read_only=True)
    tipo_operacion_display = serializers.CharField(
        source="get_tipo_operacion_display", read_only=True
    )
    moneda_operacion_display = serializers.CharField(
        source="get_moneda_operacion_display", read_only=True
    )

    class Meta:
        model = FacturaConsolidada
        fields = [
            # IDs y referencias
            "id_factura",
            "numero_factura",
            "numero_control",
            "venta_asociada",
            "venta_asociada_numero",
            "cliente",
            "cliente_detalle",
            # Fechas
            "fecha_emision",
            "fecha_vencimiento",
            # Emisor (agencia)
            "emisor_rif",
            "emisor_razon_social",
            "emisor_direccion_fiscal",
            "es_sujeto_pasivo_especial",
            "esta_inscrita_rtn",
            # Cliente
            "cliente_es_residente",
            "cliente_identificacion",
            "cliente_direccion",
            # Tipo de operación
            "tipo_operacion",
            "tipo_operacion_display",
            # Moneda y cambio
            "moneda",
            "moneda_detalle",
            "moneda_operacion",
            "moneda_operacion_display",
            "tasa_cambio_bcv",
            # Bases imponibles (USD)
            "subtotal_base_gravada",
            "subtotal_exento",
            "subtotal_exportacion",
            # Impuestos (USD)
            "monto_iva_16",
            "monto_iva_adicional",
            "monto_igtf",
            # Totales (USD)
            "subtotal",
            "monto_total",
            "saldo_pendiente",
            # Equivalentes en Bolívares
            "subtotal_base_gravada_bs",
            "subtotal_exento_bs",
            "monto_iva_16_bs",
            "monto_igtf_bs",
            "monto_total_bs",
            # Intermediación
            "tercero_rif",
            "tercero_razon_social",
            # Digital
            "modalidad_emision",
            "firma_digital",
            # Estado
            "estado",
            "estado_display",
            # Archivos
            "archivo_pdf",
            # Contabilidad
            "asiento_contable_factura",
            # Notas
            "notas",
            # Items y documentos
            "items_factura",
            "documentos_exportacion",
        ]
        read_only_fields = (
            "numero_factura",
            "subtotal",
            "monto_total",
            "saldo_pendiente",
            "subtotal_base_gravada_bs",
            "subtotal_exento_bs",
            "monto_iva_16_bs",
            "monto_igtf_bs",
            "monto_total_bs",
        )

    def create(self, validated_data):
        """Crear factura con items usando bulk_create"""
        items_data = validated_data.pop("items_factura", [])
        factura = FacturaConsolidada.objects.create(**validated_data)

        items_to_create = [
            ItemFacturaConsolidada(factura=factura, **item_data) for item_data in items_data
        ]
        if items_to_create:
            ItemFacturaConsolidada.objects.bulk_create(items_to_create)

        return factura

    def update(self, instance, validated_data):
        """Actualizar factura con items usando bulk_create"""
        items_data = validated_data.pop("items_factura", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if items_data is not None:
            instance.items_factura.all().delete()
            items_to_create = [
                ItemFacturaConsolidada(factura=instance, **item_data) for item_data in items_data
            ]
            if items_to_create:
                ItemFacturaConsolidada.objects.bulk_create(items_to_create)

        return instance


class PropuestaTransaccionIASerializer(serializers.ModelSerializer):
    estado_display = serializers.CharField(source="get_estado_display", read_only=True)
    usuario_resolutor_display = serializers.CharField(
        source="usuario_resolutor.username", read_only=True, allow_null=True
    )

    class Meta:
        model = PropuestaTransaccionIA
        fields = [
            "id_propuesta",
            "modulo_objetivo",
            "accion_tipo",
            "payload_datos",
            "ia_justificacion",
            "estado",
            "estado_display",
            "fecha_creacion",
            "fecha_resolucion",
            "usuario_resolutor",
            "usuario_resolutor_display",
            "comentarios_resolucion",
        ]
        read_only_fields = [
            "id_propuesta",
            "fecha_creacion",
            "fecha_resolucion",
            "usuario_resolutor",
        ]
