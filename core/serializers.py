# Archivo: core/serializers.py
from rest_framework import serializers

# Importar desde submódulos específicos
from core.models.agencia import Agencia, UsuarioAgencia
from core.models.boletos import BoletoImportado
from core.models.contabilidad import AsientoContable, DetalleAsiento, ItemLiquidacion, LiquidacionProveedor
from core.models.facturacion import Factura, ItemFactura
from core.models.ventas import (
    ActividadServicio,
    AlojamientoReserva,
    AlquilerAutoReserva,
    AuditLog,
    CircuitoDia,
    CircuitoTuristico,
    EventoServicio,
    FeeVenta,
    ItemVenta,
    PagoVenta,
    PaqueteAereo,
    SegmentoVuelo,
    ServicioAdicionalDetalle,
    TrasladoServicio,
    Venta,
    VentaParseMetadata,
)
from core.models_catalogos import Aerolinea, Ciudad, Moneda, Pais, ProductoServicio, Proveedor, TipoCambio
from personas.models import Cliente



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
        fields = '__all__'

class ClienteSerializer(serializers.ModelSerializer):
    get_nombre_completo = serializers.CharField(read_only=True)
    class Meta:
        model = Cliente
        fields = ['id_cliente', 'get_nombre_completo', 'email', 'nombre_empresa']

class ProveedorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Proveedor
        fields = '__all__'

class AerolineaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Aerolinea
        fields = ['id_aerolinea', 'codigo_iata', 'nombre', 'activa']


class ProductoServicioSerializer(serializers.ModelSerializer):
    tipo_producto_display = serializers.CharField(source='get_tipo_producto_display', read_only=True)
    class Meta:
        model = ProductoServicio
        fields = ['id_producto_servicio', 'nombre', 'codigo_interno', 'tipo_producto', 'tipo_producto_display']

class BoletoImportadoSerializer(serializers.ModelSerializer):
    formato_detectado_display = serializers.CharField(source='get_formato_detectado_display', read_only=True)
    estado_parseo_display = serializers.CharField(source='get_estado_parseo_display', read_only=True)
    archivo_pdf_generado = serializers.SerializerMethodField()
    
    class Meta:
        model = BoletoImportado
        fields = '__all__'
    
    def get_archivo_pdf_generado(self, obj):
        if obj.archivo_pdf_generado:
            return obj.archivo_pdf_generado.url
        return None
    
    def create(self, validated_data):
        # Si no hay archivo, es entrada manual - marcar como COMPLETADO
        if not validated_data.get('archivo_boleto'):
            validated_data['estado_parseo'] = BoletoImportado.EstadoParseo.COMPLETADO
            
            # Construir datos_parseados desde campos manuales para que el signal pueda crear la venta
            if not validated_data.get('datos_parseados'):
                validated_data['datos_parseados'] = {
                    'normalized': {
                        'reservation_code': validated_data.get('localizador_pnr', ''),
                        'ticket_number': validated_data.get('numero_boleto', ''),
                        'passenger_name': validated_data.get('nombre_pasajero_completo', ''),
                        'passenger_document': validated_data.get('foid_pasajero', ''),
                        'total_amount': str(validated_data.get('total_boleto', '0.00')),
                        'total_currency': 'USD',
                        'airline_name': validated_data.get('aerolinea_emisora', 'N/A'),
                    }
                }
        
        # Crear la instancia
        instance = super().create(validated_data)
        
        # Si es entrada manual y tiene datos, generar PDF
        if not instance.archivo_boleto and instance.datos_parseados:
            try:
                from core import ticket_parser
                from django.core.files.base import ContentFile
                
                pdf_bytes, pdf_filename = ticket_parser.generate_ticket(instance.datos_parseados)
                if pdf_bytes:
                    instance.archivo_pdf_generado.save(pdf_filename, ContentFile(pdf_bytes), save=True)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"No se pudo generar PDF para boleto manual {instance.id_boleto_importado}: {e}")
        
        return instance

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
    
    # Campos para detalles de servicios (write_only)
    alojamiento_details = serializers.JSONField(write_only=True, required=False, allow_null=True)
    alquiler_auto_details = serializers.JSONField(write_only=True, required=False, allow_null=True)
    traslado_details = serializers.JSONField(write_only=True, required=False, allow_null=True)
    tour_actividad_details = serializers.JSONField(write_only=True, required=False, allow_null=True)
    seguro_viaje_details = serializers.JSONField(write_only=True, required=False, allow_null=True)
    servicio_adicional_details = serializers.JSONField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = ItemVenta
        fields = [
            'id_item_venta', 'producto_servicio', 'producto_servicio_detalle',
            'descripcion_personalizada', 'cantidad', 'precio_unitario_venta',
            'costo_unitario_referencial', 'impuestos_item_venta',
            'subtotal_item_venta', 'total_item_venta',
            'fecha_inicio_servicio', 'fecha_fin_servicio', 'codigo_reserva_proveedor',
            'proveedor_servicio', 'proveedor_servicio_detalle', 'estado_item', 'estado_item_display', 'notas_item',
            'alojamiento_details', 'alquiler_auto_details', 'traslado_details',
            'tour_actividad_details', 'seguro_viaje_details', 'servicio_adicional_details'
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

class AlquilerAutoReservaSerializer(serializers.ModelSerializer):
    # source='margen_amount' es redundante porque el método @property ya coincide con el nombre del campo.
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
        import logging
        logger = logging.getLogger(__name__)
        
        items_data = validated_data.pop('items_venta', [])
        logger.info(f"[VENTA DEBUG] Creando venta con {len(items_data)} items")
        venta = Venta.objects.create(**validated_data)
        logger.info(f"[VENTA DEBUG] Venta creada con ID: {venta.id_venta}")
        
        for item_data in items_data:
            # Extraer detalles de servicios antes de crear el item
            alojamiento_details = item_data.pop('alojamiento_details', None)
            alquiler_auto_details = item_data.pop('alquiler_auto_details', None)
            traslado_details = item_data.pop('traslado_details', None)
            tour_actividad_details = item_data.pop('tour_actividad_details', None)
            seguro_viaje_details = item_data.pop('seguro_viaje_details', None)
            servicio_adicional_details = item_data.pop('servicio_adicional_details', None)
            
            # Crear el item de venta
            item = ItemVenta.objects.create(venta=venta, **item_data)
            
            # Crear registros relacionados según el tipo de servicio
            if alojamiento_details:
                # Convertir IDs a instancias
                if 'ciudad' in alojamiento_details and alojamiento_details['ciudad']:
                    alojamiento_details['ciudad_id'] = alojamiento_details.pop('ciudad')
                if 'proveedor' in alojamiento_details and alojamiento_details['proveedor']:
                    alojamiento_details['proveedor_id'] = alojamiento_details.pop('proveedor')
                AlojamientoReserva.objects.create(venta=venta, **alojamiento_details)
            
            if alquiler_auto_details:
                # Mapear campos del frontend a campos del modelo
                alquiler_data = {
                    'venta': venta,
                    'compania_rentadora': alquiler_auto_details.get('compania_rentadora'),
                    'categoria_auto': alquiler_auto_details.get('categoria_auto'),
                    'fecha_hora_retiro': f"{alquiler_auto_details.get('fecha_recogida')} {alquiler_auto_details.get('hora_recogida', '00:00')}" if alquiler_auto_details.get('fecha_recogida') else None,
                    'fecha_hora_devolucion': f"{alquiler_auto_details.get('fecha_devolucion')} {alquiler_auto_details.get('hora_devolucion', '00:00')}" if alquiler_auto_details.get('fecha_devolucion') else None,
                    'ciudad_retiro_id': alquiler_auto_details.get('ciudad_retiro'),
                    'ciudad_devolucion_id': alquiler_auto_details.get('ciudad_devolucion'),
                    'incluye_seguro': alquiler_auto_details.get('incluye_seguro', False),
                    'numero_confirmacion': alquiler_auto_details.get('numero_confirmacion'),
                    'proveedor_id': alquiler_auto_details.get('proveedor'),
                    'notas': alquiler_auto_details.get('notas'),
                }
                AlquilerAutoReserva.objects.create(**alquiler_data)
            
            if traslado_details:
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"[TRASLADO DEBUG] traslado_details recibido: {traslado_details}")
                
                # traslado_details contiene: {traslados: [...], pasajeros, proveedor, notas}
                traslados_list = traslado_details.get('traslados', [])
                pasajeros = traslado_details.get('pasajeros', 1)
                proveedor_id = traslado_details.get('proveedor')
                notas = traslado_details.get('notas')
                
                logger.info(f"[TRASLADO DEBUG] traslados_list: {traslados_list}, pasajeros: {pasajeros}")
                
                # Crear un TrasladoServicio por cada traslado en la lista
                for traslado_item in traslados_list:
                    fecha_hora_str = None
                    if traslado_item.get('fecha_hora') and traslado_item.get('hora'):
                        fecha_hora_str = f"{traslado_item.get('fecha_hora')} {traslado_item.get('hora')}"
                    elif traslado_item.get('fecha_hora'):
                        fecha_hora_str = traslado_item.get('fecha_hora')
                    
                    traslado_data = {
                        'venta': venta,
                        'origen': traslado_item.get('origen'),
                        'destino': traslado_item.get('destino'),
                        'fecha_hora': fecha_hora_str,
                        'pasajeros': pasajeros,
                        'proveedor_id': proveedor_id,
                        'notas': notas,
                    }
                    logger.info(f"[TRASLADO DEBUG] Creando traslado con data: {traslado_data}")
                    traslado_creado = TrasladoServicio.objects.create(**traslado_data)
                    logger.info(f"[TRASLADO DEBUG] Traslado creado con ID: {traslado_creado.id_traslado_servicio}")
            
            if tour_actividad_details:
                if 'proveedor' in tour_actividad_details and tour_actividad_details['proveedor']:
                    tour_actividad_details['proveedor_id'] = tour_actividad_details.pop('proveedor')
                ActividadServicio.objects.create(venta=venta, **tour_actividad_details)
            
            if seguro_viaje_details:
                servicio_data = {
                    'venta': venta,
                    'tipo_servicio': 'SEG',
                    'descripcion': seguro_viaje_details.get('plan', 'Seguro de Viaje'),
                    'proveedor_id': seguro_viaje_details.get('proveedor'),
                    'fecha_inicio': seguro_viaje_details.get('fecha_salida'),
                    'fecha_fin': seguro_viaje_details.get('fecha_regreso'),
                    'detalles_cobertura': f"Cobertura: USD {seguro_viaje_details.get('cobertura_monto', 0)}",
                    'notas': seguro_viaje_details.get('notas'),
                    'metadata_json': seguro_viaje_details,
                }
                ServicioAdicionalDetalle.objects.create(**servicio_data)
            
            if servicio_adicional_details:
                # Mapear tipo de servicio del frontend al modelo
                tipo_map = {
                    'SIM / E-SIM': 'SIM',
                    'Asistencia': 'AST',
                    'Lounge': 'LNG',
                    'Otro': 'OTR'
                }
                tipo_frontend = servicio_adicional_details.get('tipo_servicio', 'Otro')
                tipo_modelo = tipo_map.get(tipo_frontend, 'OTR')
                
                # Mapear campos del frontend a campos del modelo
                servicio_data = {
                    'venta': venta,
                    'tipo_servicio': tipo_modelo,
                    'descripcion': servicio_adicional_details.get('descripcion'),
                    'proveedor_id': servicio_adicional_details.get('proveedor'),
                    'notas': servicio_adicional_details.get('notas'),
                }
                
                # Mapear campos específicos según el tipo
                if servicio_adicional_details.get('lugar'):
                    servicio_data['hora_lugar_encuentro'] = servicio_adicional_details.get('lugar')
                
                if servicio_adicional_details.get('fecha'):
                    servicio_data['fecha_inicio'] = servicio_adicional_details.get('fecha')
                
                if servicio_adicional_details.get('destino'):
                    servicio_data['descripcion'] = f"{servicio_data.get('descripcion', '')} - Destino: {servicio_adicional_details.get('destino')}".strip(' -')
                
                if servicio_adicional_details.get('fecha_salida'):
                    servicio_data['fecha_inicio'] = servicio_adicional_details.get('fecha_salida')
                
                if servicio_adicional_details.get('fecha_retorno'):
                    servicio_data['fecha_fin'] = servicio_adicional_details.get('fecha_retorno')
                
                if servicio_adicional_details.get('duracion_horas'):
                    servicio_data['duracion_estimada'] = f"{servicio_adicional_details.get('duracion_horas')} horas"
                
                if servicio_adicional_details.get('pasajeros'):
                    servicio_data['participantes'] = str(servicio_adicional_details.get('pasajeros'))
                
                # Guardar datos originales en metadata_json
                servicio_data['metadata_json'] = servicio_adicional_details
                
                ServicioAdicionalDetalle.objects.create(**servicio_data)
        
        # Recalcular totales de la venta después de crear todos los items
        venta.recalcular_finanzas()
        
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


class PasaporteEscaneadoSerializer(serializers.ModelSerializer):
    cliente_detalle = ClienteSerializer(source='cliente', read_only=True)
    
    class Meta:
        from core.models.pasaportes import PasaporteEscaneado
        model = PasaporteEscaneado
        fields = [
            'id', 'imagen_original', 'cliente', 'cliente_detalle', 'numero_pasaporte',
            'nombres', 'apellidos', 'nombre_completo', 'nacionalidad', 'fecha_nacimiento',
            'fecha_vencimiento', 'sexo', 'confianza_ocr', 'verificado_manualmente',
            'es_valido', 'fecha_procesamiento', 'datos_ocr_completos', 'texto_mrz'
        ]
        read_only_fields = ['fecha_procesamiento', 'datos_ocr_completos', 'texto_mrz', 'es_valido', 'nombre_completo']


class ComunicacionProveedorSerializer(serializers.ModelSerializer):
    class Meta:
        from core.models import ComunicacionProveedor
        model = ComunicacionProveedor
        fields = [
            'id', 'remitente', 'asunto', 'fecha_recepcion', 'categoria',
            'contenido_extraido', 'cuerpo_completo'
        ]
        read_only_fields = fields


class ItemLiquidacionSerializer(serializers.ModelSerializer):
    item_venta_detalle = ItemVentaSerializer(source='item_venta', read_only=True)
    class Meta:
        model = ItemLiquidacion
        fields = ['id_item_liquidacion', 'liquidacion', 'item_venta', 'item_venta_detalle', 'descripcion', 'monto']
        read_only_fields = ['id_item_liquidacion']


class LiquidacionProveedorSerializer(serializers.ModelSerializer):
    proveedor_detalle = ProveedorSerializer(source='proveedor', read_only=True)
    venta_detalle = serializers.StringRelatedField(source='venta', read_only=True)
    items_liquidacion = ItemLiquidacionSerializer(many=True, read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    
    class Meta:
        model = LiquidacionProveedor
        fields = [
            'id_liquidacion', 'proveedor', 'proveedor_detalle', 'venta', 'venta_detalle',
            'fecha_emision', 'monto_total', 'saldo_pendiente', 'estado', 'estado_display',
            'notas', 'items_liquidacion'
        ]
        read_only_fields = ['id_liquidacion', 'fecha_emision', 'saldo_pendiente']


# --- Serializadores para Agencia (Multi-tenant) ---

from django.contrib.auth.models import User

class UsuarioSerializer(serializers.ModelSerializer):
    nombre_completo = serializers.CharField(source='get_full_name', read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'nombre_completo', 'is_active']
        read_only_fields = ['id']


class AgenciaSerializer(serializers.ModelSerializer):
    propietario_nombre = serializers.CharField(source='propietario.get_full_name', read_only=True)
    total_usuarios = serializers.SerializerMethodField()
    
    class Meta:
        model = Agencia
        fields = '__all__'
        read_only_fields = ['fecha_creacion', 'fecha_actualizacion', 'propietario']
    
    def get_total_usuarios(self, obj):
        return obj.usuarios.filter(activo=True).count()


class UsuarioAgenciaSerializer(serializers.ModelSerializer):
    usuario_detalle = UsuarioSerializer(source='usuario', read_only=True)
    agencia_nombre = serializers.CharField(source='agencia.nombre', read_only=True)
    rol_display = serializers.CharField(source='get_rol_display', read_only=True)
    
    class Meta:
        model = UsuarioAgencia
        fields = '__all__'
        read_only_fields = ['fecha_asignacion']


class CrearUsuarioAgenciaSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    rol = serializers.ChoiceField(choices=UsuarioAgencia.ROLES)
    
    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Este nombre de usuario ya existe")
        return value
    
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Este email ya está registrado")
        return value
