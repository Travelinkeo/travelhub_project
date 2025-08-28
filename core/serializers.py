# Archivo: core/serializers.py
from rest_framework import serializers
from .models import (
    Pais, Ciudad, Moneda, Cliente, Proveedor, ProductoServicio,
    Cotizacion, ItemCotizacion,
    PlanContable, AsientoContable, DetalleAsiento,
    Venta, ItemVenta, Factura, ItemFactura,
    BoletoImportado,
    SegmentoVuelo, AlojamientoReserva, TrasladoServicio, ActividadServicio,
    FeeVenta, PagoVenta
)
from django.utils.translation import gettext_lazy as _

# --- Serializadores de Modelos Compartidos/Básicos (para anidamiento o consulta) ---

class PaisSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pais
        fields = ['id_pais', 'nombre', 'codigo_iso_2', 'codigo_iso_3']

class CiudadSerializer(serializers.ModelSerializer):
    pais_detalle = PaisSerializer(source='pais', read_only=True)
    class Meta:
        model = Ciudad
        fields = ['id_ciudad', 'nombre', 'pais', 'pais_detalle', 'region_estado']
        extra_kwargs = {
            'pais': {'write_only': True}
        }

class MonedaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Moneda
        fields = ['id_moneda', 'nombre', 'codigo_iso', 'simbolo', 'es_moneda_local']

class ClienteSerializer(serializers.ModelSerializer):
    get_nombre_completo = serializers.CharField(read_only=True)
    class Meta:
        model = Cliente
        fields = ['id_cliente', 'get_nombre_completo', 'email', 'nombre_empresa']

class ProductoServicioSerializer(serializers.ModelSerializer):
    tipo_producto_display = serializers.CharField(source='get_tipo_producto_display', read_only=True)
    class Meta:
        model = ProductoServicio
        fields = ['id_producto_servicio', 'nombre', 'codigo_interno', 'tipo_producto', 'tipo_producto_display']

# --- Serializadores para ERP (API Principal) ---

class DetalleAsientoSerializer(serializers.ModelSerializer):
    cuenta_contable_codigo = serializers.CharField(source='cuenta_contable.codigo_cuenta', read_only=True)
    cuenta_contable_nombre = serializers.CharField(source='cuenta_contable.nombre_cuenta', read_only=True)

    class Meta:
        model = DetalleAsiento
        fields = [
            'id_detalle_asiento', 'linea', 'cuenta_contable', 
            'cuenta_contable_codigo', 'cuenta_contable_nombre',
            'descripcion_linea', 'debe', 'haber'
        ]
        extra_kwargs = {
            'asiento': {'write_only': True, 'required': False}
        }

class AsientoContableSerializer(serializers.ModelSerializer):
    detalles_asiento = DetalleAsientoSerializer(many=True)
    moneda_detalle = MonedaSerializer(source='moneda', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    tipo_asiento_display = serializers.CharField(source='get_tipo_asiento_display', read_only=True)
    esta_cuadrado = serializers.BooleanField(read_only=True)

    class Meta:
        model = AsientoContable
        fields = [
            'id_asiento', 'numero_asiento', 'fecha_contable', 'descripcion_general',
            'tipo_asiento', 'tipo_asiento_display', 'referencia_documento', 'estado', 'estado_display',
            'moneda', 'moneda_detalle', 'tasa_cambio_aplicada',
            'total_debe', 'total_haber', 'esta_cuadrado',
            'fecha_creacion', 'detalles_asiento'
        ]
        read_only_fields = ('numero_asiento', 'total_debe', 'total_haber', 'fecha_creacion', 'esta_cuadrado')
        extra_kwargs = {
            'moneda': {'write_only': True, 'allow_null': False, 'required': True}
        }

    def create(self, validated_data):
        detalles_data = validated_data.pop('detalles_asiento', [])
        asiento = AsientoContable.objects.create(**validated_data)
        for detalle_data in detalles_data:
            DetalleAsiento.objects.create(asiento=asiento, **detalle_data)
        asiento.calcular_totales()
        return asiento

    def update(self, instance, validated_data):
        detalles_data = validated_data.pop('detalles_asiento', None)
        instance.fecha_contable = validated_data.get('fecha_contable', instance.fecha_contable)
        instance.descripcion_general = validated_data.get('descripcion_general', instance.descripcion_general)
        instance.tipo_asiento = validated_data.get('tipo_asiento', instance.tipo_asiento)
        instance.moneda = validated_data.get('moneda', instance.moneda)
        instance.tasa_cambio_aplicada = validated_data.get('tasa_cambio_aplicada', instance.tasa_cambio_aplicada)
        instance.referencia_documento = validated_data.get('referencia_documento', instance.referencia_documento)
        instance.save()

        if detalles_data is not None:
            instance.detalles_asiento.all().delete()
            for detalle_data in detalles_data:
                DetalleAsiento.objects.create(asiento=instance, **detalle_data)
        
        instance.calcular_totales()
        return instance

class ItemVentaSerializer(serializers.ModelSerializer):
    producto_servicio_detalle = ProductoServicioSerializer(source='producto_servicio', read_only=True)
    proveedor_servicio_detalle = serializers.StringRelatedField(source='proveedor_servicio', read_only=True)
    estado_item_display = serializers.CharField(source='get_estado_item_display', read_only=True)

    class Meta:
        model = ItemVenta
        fields = [
            'id_item_venta', 'producto_servicio', 'producto_servicio_detalle',
            'descripcion_personalizada', 'cantidad', 'precio_unitario_venta',
            'costo_unitario_referencial', 'impuestos_item_venta',
            'subtotal_item_venta', 'total_item_venta',
            'fecha_inicio_servicio', 'fecha_fin_servicio', 'codigo_reserva_proveedor',
            'proveedor_servicio', 'proveedor_servicio_detalle', 'estado_item', 'estado_item_display', 'notas_item'
        ]
        read_only_fields = ('subtotal_item_venta', 'total_item_venta')
        extra_kwargs = {
            'venta': {'write_only': True, 'required': False},
            'producto_servicio': {'write_only': True, 'allow_null': False, 'required': True},
            'proveedor_servicio': {'allow_null': True, 'required': False},
        }

# --- Serializadores nuevos componentes de Venta (Phase 1) ---

class SegmentoVueloSerializer(serializers.ModelSerializer):
    origen_detalle = CiudadSerializer(source='origen', read_only=True)
    destino_detalle = CiudadSerializer(source='destino', read_only=True)
    class Meta:
        model = SegmentoVuelo
        fields = [
            'id_segmento_vuelo', 'venta', 'origen', 'origen_detalle', 'destino', 'destino_detalle',
            'aerolinea', 'numero_vuelo', 'fecha_salida', 'fecha_llegada',
            'clase_reserva', 'cabina', 'notas'
        ]
        extra_kwargs = {
            'venta': {'write_only': True, 'required': True}
        }

class AlojamientoReservaSerializer(serializers.ModelSerializer):
    ciudad_detalle = CiudadSerializer(source='ciudad', read_only=True)
    proveedor_detalle = serializers.StringRelatedField(source='proveedor', read_only=True)
    class Meta:
        model = AlojamientoReserva
        fields = [
            'id_alojamiento_reserva', 'venta', 'proveedor', 'proveedor_detalle', 'ciudad', 'ciudad_detalle',
            'nombre_establecimiento', 'check_in', 'check_out', 'regimen_alimentacion', 'habitaciones', 'notas'
        ]
        extra_kwargs = {
            'venta': {'write_only': True, 'required': True}
        }

class TrasladoServicioSerializer(serializers.ModelSerializer):
    proveedor_detalle = serializers.StringRelatedField(source='proveedor', read_only=True)
    tipo_traslado_display = serializers.CharField(source='get_tipo_traslado_display', read_only=True)
    class Meta:
        model = TrasladoServicio
        fields = [
            'id_traslado_servicio', 'venta', 'tipo_traslado', 'tipo_traslado_display', 'origen', 'destino',
            'fecha_hora', 'proveedor', 'proveedor_detalle', 'pasajeros', 'notas'
        ]
        extra_kwargs = {
            'venta': {'write_only': True, 'required': True}
        }

class ActividadServicioSerializer(serializers.ModelSerializer):
    proveedor_detalle = serializers.StringRelatedField(source='proveedor', read_only=True)
    class Meta:
        model = ActividadServicio
        fields = [
            'id_actividad_servicio', 'venta', 'nombre', 'fecha', 'duracion_horas', 'incluye', 'no_incluye',
            'proveedor', 'proveedor_detalle', 'notas'
        ]
        extra_kwargs = {
            'venta': {'write_only': True, 'required': True}
        }

class FeeVentaSerializer(serializers.ModelSerializer):
    tipo_fee_display = serializers.CharField(source='get_tipo_fee_display', read_only=True)
    moneda_detalle = MonedaSerializer(source='moneda', read_only=True)
    class Meta:
        model = FeeVenta
        fields = [
            'id_fee_venta', 'venta', 'tipo_fee', 'tipo_fee_display', 'descripcion', 'monto', 'moneda', 'moneda_detalle',
            'es_comision_agencia', 'taxable', 'creado'
        ]
        read_only_fields = ('creado',)
        extra_kwargs = {
            'venta': {'write_only': True, 'required': True},
            'moneda': {'write_only': True, 'required': True}
        }

class PagoVentaSerializer(serializers.ModelSerializer):
    metodo_display = serializers.CharField(source='get_metodo_display', read_only=True)
    moneda_detalle = MonedaSerializer(source='moneda', read_only=True)
    class Meta:
        model = PagoVenta
        fields = [
            'id_pago_venta', 'venta', 'fecha_pago', 'monto', 'moneda', 'moneda_detalle', 'metodo', 'metodo_display',
            'referencia', 'confirmado', 'notas', 'creado'
        ]
        read_only_fields = ('creado',)
        extra_kwargs = {
            'venta': {'write_only': True, 'required': True},
            'moneda': {'write_only': True, 'required': True}
        }

class VentaSerializer(serializers.ModelSerializer):
    items_venta = ItemVentaSerializer(many=True)
    segmentos_vuelo = SegmentoVueloSerializer(many=True, read_only=True)
    alojamientos = AlojamientoReservaSerializer(many=True, read_only=True)
    traslados = TrasladoServicioSerializer(many=True, read_only=True)
    actividades = ActividadServicioSerializer(many=True, read_only=True)
    fees_venta = FeeVentaSerializer(many=True, read_only=True)
    pagos_venta = PagoVentaSerializer(many=True, read_only=True)
    cliente_detalle = ClienteSerializer(source='cliente', read_only=True)
    moneda_detalle = MonedaSerializer(source='moneda', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    tipo_venta_display = serializers.CharField(source='get_tipo_venta_display', read_only=True)
    canal_origen_display = serializers.CharField(source='get_canal_origen_display', read_only=True)
    puntos_fidelidad_asignados = serializers.BooleanField(read_only=True)

    class Meta:
        model = Venta
        fields = [
            'id_venta', 'localizador', 'cliente', 'cliente_detalle', 'cotizacion_origen',
            'fecha_venta', 'descripcion_general', 'moneda', 'moneda_detalle',
            'tipo_venta', 'tipo_venta_display', 'canal_origen', 'canal_origen_display',
            'subtotal', 'impuestos', 'total_venta', 'monto_pagado', 'saldo_pendiente',
            'margen_estimado', 'co2_estimado_kg',
            'estado', 'estado_display', 'asiento_contable_venta', 'notas',
            'items_venta', 'segmentos_vuelo', 'alojamientos', 'traslados', 'actividades', 'fees_venta', 'pagos_venta',
            'puntos_fidelidad_asignados'
        ]
        read_only_fields = (
            'localizador', 'total_venta', 'saldo_pendiente', 'fecha_venta',
            'segmentos_vuelo', 'alojamientos', 'traslados', 'actividades', 'fees_venta', 'pagos_venta'
        )
        extra_kwargs = {
            'cliente': {'write_only': True, 'allow_null': False, 'required': True},
            'moneda': {'write_only': True, 'allow_null': False, 'required': True},
            'cotizacion_origen': {'allow_null': True, 'required': False},
            'asiento_contable_venta': {'allow_null': True, 'required': False},
        }

    def create(self, validated_data):
        items_data = validated_data.pop('items_venta', [])
        venta = Venta.objects.create(**validated_data)
        for item_data in items_data:
            ItemVenta.objects.create(venta=venta, **item_data)
        return venta

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items_venta', None)
        for attr in [
            'cliente', 'cotizacion_origen', 'descripcion_general', 'moneda',
            'subtotal', 'impuestos', 'monto_pagado', 'estado', 'asiento_contable_venta',
            'notas', 'tipo_venta', 'canal_origen', 'margen_estimado', 'co2_estimado_kg'
        ]:
            if attr in validated_data:
                setattr(instance, attr, validated_data[attr])
        instance.save()

        if items_data is not None:
            instance.items_venta.all().delete()
            for item_data in items_data:
                ItemVenta.objects.create(venta=instance, **item_data)
        return instance

class ItemFacturaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemFactura
        fields = [
            'id_item_factura', 'descripcion', 'cantidad', 
            'precio_unitario', 'subtotal_item'
        ]
        read_only_fields = ('subtotal_item',)
        extra_kwargs = {
            'factura': {'write_only': True, 'required': False}
        }

class FacturaSerializer(serializers.ModelSerializer):
    items_factura = ItemFacturaSerializer(many=True)
    cliente_detalle = ClienteSerializer(source='cliente', read_only=True)
    moneda_detalle = MonedaSerializer(source='moneda', read_only=True)
    venta_asociada_numero = serializers.CharField(source='venta_asociada.numero_venta', read_only=True, allow_null=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)

    class Meta:
        model = Factura
        fields = [
            'id_factura', 'numero_factura', 'venta_asociada', 'venta_asociada_numero',
            'cliente', 'cliente_detalle', 'fecha_emision', 'fecha_vencimiento',
            'moneda', 'moneda_detalle', 'subtotal', 'monto_impuestos', 'monto_total',
            'saldo_pendiente', 'estado', 'estado_display', 'asiento_contable_factura',
            'notas', 'items_factura'
        ]
        read_only_fields = ('numero_factura', 'monto_total', 'saldo_pendiente')
        extra_kwargs = {
            'cliente': {'write_only': True, 'allow_null': False, 'required': True},
            'moneda': {'write_only': True, 'allow_null': False, 'required': True},
            'venta_asociada': {'allow_null': True, 'required': False},
            'asiento_contable_factura': {'allow_null': True, 'required': False},
        }

    def create(self, validated_data):
        items_data = validated_data.pop('items_factura', [])
        factura = Factura.objects.create(**validated_data)
        for item_data in items_data:
            ItemFactura.objects.create(factura=factura, **item_data)
        return factura

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items_factura', None)
        instance.venta_asociada = validated_data.get('venta_asociada', instance.venta_asociada)
        instance.cliente = validated_data.get('cliente', instance.cliente)
        instance.fecha_emision = validated_data.get('fecha_emision', instance.fecha_emision)
        instance.fecha_vencimiento = validated_data.get('fecha_vencimiento', instance.fecha_vencimiento)
        instance.moneda = validated_data.get('moneda', instance.moneda)
        instance.subtotal = validated_data.get('subtotal', instance.subtotal)
        instance.monto_impuestos = validated_data.get('monto_impuestos', instance.monto_impuestos)
        instance.estado = validated_data.get('estado', instance.estado)
        instance.asiento_contable_factura = validated_data.get('asiento_contable_factura', instance.asiento_contable_factura)
        instance.notas = validated_data.get('notas', instance.notas)
        instance.save()

        if items_data is not None:
            instance.items_factura.all().delete()
            for item_data in items_data:
                ItemFactura.objects.create(factura=instance, **item_data)
        
        return instance
