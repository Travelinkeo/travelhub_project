# Archivo: core/serializers.py
from rest_framework import serializers

from .models import (
    ActividadServicio,
    AlojamientoReserva,
    AlquilerAutoReserva,
    AsientoContable,
    AuditLog,
    BoletoImportado,
    CircuitoDia,
    CircuitoTuristico,
    Ciudad,
    Cliente,
    DetalleAsiento,
    EventoServicio,
    Factura,
    FeeVenta,
    ItemFactura,
    ItemVenta,
    Moneda,
    PagoVenta,
    Pais,
    PaqueteAereo,
    SegmentoVuelo,
    ServicioAdicionalDetalle,
    TrasladoServicio,
    Venta,
    VentaParseMetadata,
)

# Evitar import circular: importar catálogos ligeros directamente
from .models_catalogos import ProductoServicio, Proveedor, TipoCambio

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

class TipoCambioSerializer(serializers.ModelSerializer):
    moneda_origen_detalle = MonedaSerializer(source='moneda_origen', read_only=True)
    moneda_destino_detalle = MonedaSerializer(source='moneda_destino', read_only=True)
    class Meta:
        model = TipoCambio
        fields = [
            'id_tipo_cambio', 'moneda_origen', 'moneda_origen_detalle', 'moneda_destino', 'moneda_destino_detalle',
            'fecha_efectiva', 'tasa_conversion'
        ]

class ClienteSerializer(serializers.ModelSerializer):
    get_nombre_completo = serializers.ReadOnlyField()
    class Meta:
        model = Cliente
        fields = ['id_cliente', 'get_nombre_completo', 'email', 'nombre_empresa']

class ProveedorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Proveedor
        fields = [
            'id_proveedor', 'nombre', 'tipo_proveedor', 'nivel_proveedor',
            'contacto_nombre', 'contacto_email', 'contacto_telefono', 
            'direccion', 'ciudad', 'notas', 'iata', 'activo'
        ]


class ProductoServicioSerializer(serializers.ModelSerializer):
    tipo_producto_display = serializers.CharField(source='get_tipo_producto_display', read_only=True)
    class Meta:
        model = ProductoServicio
        fields = ['id_producto_servicio', 'nombre', 'codigo_interno', 'tipo_producto', 'tipo_producto_display']

class BoletoImportadoSerializer(serializers.ModelSerializer):
    formato_detectado_display = serializers.CharField(source='get_formato_detectado_display', read_only=True)
    estado_parseo_display = serializers.CharField(source='get_estado_parseo_display', read_only=True)
    class Meta:
        model = BoletoImportado
        fields = [
            'id_boleto_importado', 'archivo_boleto', 'fecha_subida', 'formato_detectado',
            'formato_detectado_display', 'estado_parseo', 'estado_parseo_display',
            'datos_parseados', 'archivo_pdf_generado', 'numero_boleto', 'nombre_pasajero_procesado',
            'localizador_pnr', 'aerolinea_emisora', 'tarifa_base', 'total_boleto'
        ]

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

# --- Serializadores nuevos componentes de Venta (Phase 1) ---

class AlojamientoReservaSerializer(serializers.ModelSerializer):
    ciudad_detalle = CiudadSerializer(source='ciudad', read_only=True)
    proveedor_detalle = serializers.StringRelatedField(source='proveedor', read_only=True)
    class Meta:
        model = AlojamientoReserva
        fields = [
            'id_alojamiento_reserva', 'venta', 'item_venta', 'proveedor', 'proveedor_detalle', 'ciudad', 'ciudad_detalle',
            'nombre_establecimiento', 'check_in', 'check_out', 'regimen_alimentacion', 'habitaciones', 'notas'
        ]
        extra_kwargs = {
            'venta': {'write_only': True, 'required': False},
            'item_venta': {'write_only': True, 'required': False}
        }

class ItemVentaSerializer(serializers.ModelSerializer):
    producto_servicio_detalle = ProductoServicioSerializer(source='producto_servicio', read_only=True)
    proveedor_servicio_detalle = serializers.StringRelatedField(source='proveedor_servicio', read_only=True)
    estado_item_display = serializers.CharField(source='get_estado_item_display', read_only=True)
    
    # Write-only fields for nested details
    alojamiento_details = AlojamientoReservaSerializer(write_only=True, required=False, allow_null=True)

    class Meta:
        model = ItemVenta
        fields = [
            'id_item_venta', 'producto_servicio', 'producto_servicio_detalle',
            'descripcion_personalizada', 'cantidad', 'precio_unitario_venta',
            'costo_unitario_referencial', 'impuestos_item_venta',
            'subtotal_item_venta', 'total_item_venta',
            'fecha_inicio_servicio', 'fecha_fin_servicio', 'codigo_reserva_proveedor',
            'proveedor_servicio', 'proveedor_servicio_detalle', 'estado_item', 'estado_item_display', 'notas_item',
            'alojamiento_details' # Add field
        ]
        read_only_fields = ('subtotal_item_venta', 'total_item_venta')
        extra_kwargs = {
            'venta': {'write_only': True, 'required': False},
            'producto_servicio': {'write_only': True, 'allow_null': False, 'required': True},
            'proveedor_servicio': {'allow_null': True, 'required': False},
        }

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

class AlquilerAutoReservaSerializer(serializers.ModelSerializer):
    margen_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    margen_pct = serializers.SerializerMethodField()
    class Meta:
        model = AlquilerAutoReserva
        fields = '__all__'
    def get_margen_pct(self, obj):
        return float(obj.margen_pct) if obj.margen_pct is not None else None

class EventoServicioSerializer(serializers.ModelSerializer):
    margen_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    margen_pct = serializers.SerializerMethodField()
    class Meta:
        model = EventoServicio
        fields = '__all__'
    def get_margen_pct(self, obj):
        return float(obj.margen_pct) if obj.margen_pct is not None else None

class CircuitoDiaSerializer(serializers.ModelSerializer):
    class Meta:
        model = CircuitoDia
        fields = '__all__'

class CircuitoTuristicoSerializer(serializers.ModelSerializer):
    dias = CircuitoDiaSerializer(many=True, read_only=True)
    margen_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    margen_pct = serializers.SerializerMethodField()
    class Meta:
        model = CircuitoTuristico
        fields = '__all__'
    def get_margen_pct(self, obj):
        return float(obj.margen_pct) if obj.margen_pct is not None else None

class PaqueteAereoSerializer(serializers.ModelSerializer):
    margen_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    margen_pct = serializers.SerializerMethodField()
    class Meta:
        model = PaqueteAereo
        fields = '__all__'
    def get_margen_pct(self, obj):
        return float(obj.margen_pct) if obj.margen_pct is not None else None

class ServicioAdicionalDetalleSerializer(serializers.ModelSerializer):
    margen_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    margen_pct = serializers.SerializerMethodField()
    class Meta:
        model = ServicioAdicionalDetalle
        fields = '__all__'
    def get_margen_pct(self, obj):
        return float(obj.margen_pct) if obj.margen_pct is not None else None

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
    alquileres_autos = AlquilerAutoReservaSerializer(many=True, read_only=True)
    eventos_servicios = EventoServicioSerializer(many=True, read_only=True)
    circuitos_turisticos = CircuitoTuristicoSerializer(many=True, read_only=True)
    paquetes_aereos = PaqueteAereoSerializer(many=True, read_only=True)
    servicios_adicionales = ServicioAdicionalDetalleSerializer(many=True, read_only=True)
    fees_venta = FeeVentaSerializer(many=True, read_only=True)
    pagos_venta = PagoVentaSerializer(many=True, read_only=True)
    cliente_detalle = ClienteSerializer(source='cliente', read_only=True)
    moneda_detalle = MonedaSerializer(source='moneda', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    tipo_venta_display = serializers.CharField(source='get_tipo_venta_display', read_only=True)
    canal_origen_display = serializers.CharField(source='get_canal_origen_display', read_only=True)
    puntos_fidelidad_asignados = serializers.BooleanField(read_only=True)
    # Campos de consistencia monetaria provenientes del parseo de boletos (cuando existan)
    amount_consistency = serializers.CharField(read_only=True, required=False, allow_null=True)
    amount_difference = serializers.CharField(read_only=True, required=False, allow_null=True)
    taxes_amount_expected = serializers.CharField(read_only=True, required=False, allow_null=True)
    taxes_difference = serializers.CharField(read_only=True, required=False, allow_null=True)

    class Meta:
        model = Venta
        fields = [
            'id_venta', 'localizador', 'cliente', 'cliente_detalle', 'cotizacion_origen',
            'fecha_venta', 'descripcion_general', 'moneda', 'moneda_detalle',
            'tipo_venta', 'tipo_venta_display', 'canal_origen', 'canal_origen_display',
            'subtotal', 'impuestos', 'total_venta', 'monto_pagado', 'saldo_pendiente',
            'margen_estimado', 'co2_estimado_kg',
            'estado', 'estado_display', 'asiento_contable_venta', 'notas', 'creado_por',
            'items_venta', 'segmentos_vuelo', 'alojamientos', 'traslados', 'actividades', 'fees_venta', 'pagos_venta',
            'alquileres_autos', 'eventos_servicios', 'circuitos_turisticos', 'paquetes_aereos', 'servicios_adicionales',
            'puntos_fidelidad_asignados',
            'amount_consistency', 'amount_difference', 'taxes_amount_expected', 'taxes_difference'
        ]
        read_only_fields = (
            'localizador', 'total_venta', 'saldo_pendiente', 'fecha_venta', 'creado_por',
            'segmentos_vuelo', 'alojamientos', 'traslados', 'actividades', 'fees_venta', 'pagos_venta',
            'alquileres_autos', 'eventos_servicios', 'circuitos_turisticos', 'paquetes_aereos', 'servicios_adicionales'
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
            # Extraer datos anidados antes de crear el item
            alojamiento_data = item_data.pop('alojamiento_details', None)
            
            # Crear el item de venta
            item_venta = ItemVenta.objects.create(venta=venta, **item_data)
            
            # Crear alojamiento si se proporcionaron datos
            if alojamiento_data:
                AlojamientoReserva.objects.create(
                    venta=venta, 
                    item_venta=item_venta, 
                    **alojamiento_data
                )
        
        return venta

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items_venta', None)
        
        # Actualizar campos básicos de la venta
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Actualizar items si se proporcionaron
        if items_data is not None:
            # Eliminar items existentes y recrear (enfoque simple)
            instance.items_venta.all().delete()
            
            for item_data in items_data:
                alojamiento_data = item_data.pop('alojamiento_details', None)
                item_venta = ItemVenta.objects.create(venta=instance, **item_data)
                
                if alojamiento_data:
                    AlojamientoReserva.objects.create(
                        venta=instance, 
                        item_venta=item_venta, 
                        **alojamiento_data
                    )
        
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
    venta_asociada_numero = serializers.CharField(source='venta_asociada.localizador', read_only=True, allow_null=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)

    class Meta:
        model = Factura
        fields = [
            'id_factura', 'numero_factura', 'venta_asociada', 'venta_asociada_numero',
            'cliente', 'cliente_detalle', 'fecha_emision', 'fecha_vencimiento',
            'moneda', 'moneda_detalle', 'subtotal', 'monto_impuestos', 'monto_total',
            'saldo_pendiente', 'estado', 'estado_display', 'asiento_contable_factura',
            'notas', 'items_factura', 'archivo_pdf'
        ]
        read_only_fields = ('numero_factura', 'monto_total', 'saldo_pendiente', 'archivo_pdf')
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

class VentaParseMetadataSerializer(serializers.ModelSerializer):
    class Meta:
        model = VentaParseMetadata
        fields = [
            'id_metadata','venta','fuente','currency','fare_amount','taxes_amount','total_amount',
            'amount_consistency','amount_difference','taxes_amount_expected','taxes_difference',
            'segments_json','raw_normalized_json','creado'
        ]
        read_only_fields = ('creado',)

# --- Serializadores para Integración con IA ---

class ItinerarioSegmentoSerializer(serializers.Serializer):
    origen_iata = serializers.CharField(max_length=3, required=False)
    destino_iata = serializers.CharField(max_length=3, required=False)
    numero_vuelo = serializers.CharField(max_length=10, required=False)
    fecha_salida = serializers.DateTimeField(required=False)

    class Meta:
        fields = ['origen_iata', 'destino_iata', 'numero_vuelo', 'fecha_salida']

class GeminiBoletoParseadoSerializer(serializers.Serializer):
    localizador_pnr = serializers.CharField(max_length=10)
    nombre_pasajero_completo = serializers.CharField(max_length=150)
    numero_boleto = serializers.CharField(max_length=50, required=False, allow_null=True)
    aerolinea_emisora = serializers.CharField(max_length=100, required=False, allow_null=True)
    tarifa_base = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)
    impuestos_total = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)
    total_boleto = serializers.DecimalField(max_digits=10, decimal_places=2)
    itinerario = ItinerarioSegmentoSerializer(many=True, required=False)

    def create(self, validated_data):
        # La lógica de creación se manejará en la vista que use este serializador.
        # Por ahora, solo devolvemos los datos validados.
        return validated_data


class AuditLogSerializer(serializers.ModelSerializer):
    venta_localizador = serializers.CharField(source='venta.localizador', read_only=True)
    class Meta:
        model = AuditLog
        fields = [
            'id_audit_log','modelo','object_id','venta','venta_localizador','accion','descripcion',
            'datos_previos','datos_nuevos','metadata_extra','creado'
        ]
        read_only_fields = fields