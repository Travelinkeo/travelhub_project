from rest_framework import serializers

from apps.bookings.models import (
    ActividadServicio,
    AlojamientoReserva,
    AlquilerAutoReserva,
    BoletoImportado,
    CircuitoDia,
    CircuitoTuristico,
    ComisionProveedorServicio,
    EventoServicio,
    FeeVenta,
    HotelTarifario,
    ItemVenta,
    PagoVenta,
    PaqueteAereo,
    ProductoServicio,
    Proveedor,
    SegmentoVuelo,
    ServicioAdicionalDetalle,
    TarifaHabitacion,
    TarifarioProveedor,
    TipoHabitacion,
    TrasladoServicio,
    Venta,
    VentaParseMetadata,
)
from apps.common.serializers import CiudadSerializer
from apps.crm.serializers import CoreClienteSerializer
from apps.finance.serializers import MonedaSerializer

# --- Original Bookings Serializers ---


class TarifaHabitacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TarifaHabitacion
        fields = [
            "id",
            "fecha_inicio",
            "fecha_fin",
            "nombre_temporada",
            "tarifa_sgl",
            "tarifa_dbl",
            "tarifa_tpl",
            "tarifa_cpl",
            "tarifa_nino",
        ]


class TipoHabitacionSerializer(serializers.ModelSerializer):
    tarifas = TarifaHabitacionSerializer(many=True, read_only=True)

    class Meta:
        model = TipoHabitacion
        fields = [
            "id",
            "nombre",
            "capacidad_adultos",
            "capacidad_ninos",
            "capacidad_total",
            "descripcion",
            "tarifas",
        ]


class HotelTarifarioSerializer(serializers.ModelSerializer):
    tipos_habitacion = TipoHabitacionSerializer(many=True, read_only=True)
    regimen_display = serializers.CharField(source="get_regimen_default_display", read_only=True)

    class Meta:
        model = HotelTarifario
        fields = [
            "id",
            "nombre",
            "slug",
            "destino",
            "regimen_default",
            "regimen_display",
            "comision",
            "check_in",
            "check_out",
            "activo",
            "tipos_habitacion",
        ]


class TarifarioProveedorSerializer(serializers.ModelSerializer):
    proveedor_nombre = serializers.CharField(source="proveedor.nombre", read_only=True)

    class Meta:
        model = TarifarioProveedor
        fields = [
            "id",
            "proveedor",
            "proveedor_nombre",
            "nombre",
            "fecha_vigencia_inicio",
            "fecha_vigencia_fin",
            "comision_estandar",
            "activo",
            "fecha_carga",
        ]


class CotizacionHotelSerializer(serializers.Serializer):
    destino = serializers.CharField(required=True)
    fecha_entrada = serializers.DateField(required=True)
    fecha_salida = serializers.DateField(required=True)
    habitaciones = serializers.ListField(
        child=serializers.DictField(),
        required=True,
    )


class ResultadoCotizacionSerializer(serializers.Serializer):
    hotel = serializers.CharField()
    destino = serializers.CharField()
    regimen = serializers.CharField()
    comision = serializers.DecimalField(max_digits=5, decimal_places=2)
    total_sin_comision = serializers.DecimalField(max_digits=10, decimal_places=2)
    comision_monto = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_neto = serializers.DecimalField(max_digits=10, decimal_places=2)
    desglose = serializers.ListField()


# --- Bookings Serializers Transferred from core ---


class ProveedorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Proveedor
        fields = [
            "id_proveedor",
            "nombre",
            "alias",
            "rif",
            "tipo_proveedor",
            "nivel_proveedor",
            "contacto_nombre",
            "contacto_email",
            "contacto_telefono",
            "direccion",
            "ciudad",
            "notas",
            "numero_cuenta_agencia",
            "condiciones_pago",
            "datos_bancarios",
            "fee_nacional",
            "fee_internacional",
            "activo",
            "identificadores_gds",
            "iata",
            "seudo_sabre",
            "office_id_kiu",
            "office_id_amadeus",
            "office_id_travelport",
            "office_id_hotelbeds",
            "office_id_expedia",
            "agencia",
            "is_deleted",
            "deleted_at",
        ]
        read_only_fields = ["agencia", "is_deleted", "deleted_at"]


class ComisionProveedorServicioSerializer(serializers.ModelSerializer):
    tipo_servicio_display = serializers.CharField(
        source="get_tipo_servicio_display", read_only=True, default=""
    )
    moneda_codigo = serializers.SerializerMethodField()

    def get_moneda_codigo(self, obj):
        return obj.moneda.codigo_iso if obj.moneda else ""

    class Meta:
        model = ComisionProveedorServicio
        fields = [
            "id_comision",
            "proveedor",
            "tipo_servicio",
            "tipo_servicio_display",
            "comision_porcentaje",
            "comision_monto_fijo",
            "moneda",
            "moneda_codigo",
            "activo",
        ]
        extra_kwargs = {"proveedor": {"required": True}, "tipo_servicio": {"required": True}}


class ProductoServicioSerializer(serializers.ModelSerializer):
    tipo_producto_display = serializers.CharField(
        source="get_tipo_producto_display", read_only=True
    )

    class Meta:
        model = ProductoServicio
        fields = [
            "id_producto_servicio",
            "nombre",
            "codigo_interno",
            "tipo_producto",
            "tipo_producto_display",
        ]


class BoletoImportadoSerializer(serializers.ModelSerializer):
    formato_detectado_display = serializers.CharField(
        source="get_formato_detectado_display", read_only=True
    )
    estado_parseo_display = serializers.CharField(
        source="get_estado_parseo_display", read_only=True
    )
    archivo_pdf_generado = serializers.SerializerMethodField()

    class Meta:
        model = BoletoImportado
        fields = [
            "id_boleto_importado",
            "archivo_boleto",
            "fecha_subida",
            "updated_at",
            "formato_detectado",
            "formato_detectado_display",
            "datos_parseados",
            "estado_parseo",
            "estado_parseo_display",
            "log_parseo",
            "numero_boleto",
            "nombre_pasajero_completo",
            "nombre_pasajero_procesado",
            "ruta_vuelo",
            "fecha_emision_boleto",
            "aerolinea_emisora",
            "direccion_aerolinea",
            "agente_emisor",
            "foid_pasajero",
            "localizador_pnr",
            "tarifa_base",
            "impuestos_descripcion",
            "impuestos_total_calculado",
            "total_boleto",
            "exchange_monto",
            "void_monto",
            "comision_agencia",
            "iva_monto",
            "inatur_monto",
            "otros_impuestos_monto",
            "fee_servicio",
            "igtf_monto",
            "proveedor_emisor",
            "venta_asociada",
            "archivo_pdf_generado",
            "telegram_file_id",
            "raw_hash",
            "version",
            "boleto_padre",
            "estado_emision",
            "agencia",
            "is_deleted",
            "deleted_at",
        ]
        read_only_fields = [
            "agencia",
            "is_deleted",
            "deleted_at",
            "fecha_subida",
            "updated_at",
            "raw_hash",
            "version",
        ]

    def get_archivo_pdf_generado(self, obj):
        if obj.archivo_pdf_generado:
            from django.conf import settings

            if getattr(settings, "USE_CLOUDINARY", False):
                request = self.context.get("request")
                if request:
                    return request.build_absolute_uri(
                        f"/api/boletos-importados/{obj.id_boleto_importado}/descargar-pdf/"
                    )
            return obj.archivo_pdf_generado.url
        return None

    def create(self, validated_data):
        if not validated_data.get("archivo_boleto"):
            validated_data["estado_parseo"] = BoletoImportado.EstadoParseo.COMPLETADO

            if not validated_data.get("datos_parseados"):
                validated_data["datos_parseados"] = {
                    "normalized": {
                        "reservation_code": validated_data.get("localizador_pnr", ""),
                        "ticket_number": validated_data.get("numero_boleto", ""),
                        "passenger_name": validated_data.get("nombre_pasajero_completo", ""),
                        "passenger_document": validated_data.get("foid_pasajero", ""),
                        "total_amount": str(validated_data.get("total_boleto", "0.00")),
                        "total_currency": "USD",
                        "airline_name": validated_data.get("aerolinea_emisora", "N/A"),
                    }
                }

        instance = super().create(validated_data)

        if not instance.archivo_boleto and instance.datos_parseados:
            try:
                from apps.automation.parsers import ticket_parser

                agencia_obj = None
                request = self.context.get("request")
                if request and hasattr(request.user, "usuarioagencia"):
                    agencia_obj = request.user.usuarioagencia.agencia
                elif request and hasattr(request, "agencia"):
                    agencia_obj = request.agencia
                else:
                    agencia_obj = None
                    import logging

                    logger = logging.getLogger(__name__)
                    logger.debug("Boleto manual creado sin contexto de agencia explícito.")

                pdf_bytes, pdf_filename = ticket_parser.generate_ticket(
                    instance.datos_parseados, agencia_obj=agencia_obj, boleto_obj=instance
                )
                if not pdf_bytes:
                    logger.warning(
                        f"No se pudo generar PDF para boleto manual {instance.id_boleto_importado}"
                    )
            except Exception as e:
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(
                    f"Error crítico generando PDF para boleto manual {instance.id_boleto_importado}: {e}"
                )

        return instance


class ItemVentaSerializer(serializers.ModelSerializer):
    producto_servicio_detalle = ProductoServicioSerializer(
        source="producto_servicio", read_only=True
    )
    proveedor_servicio_detalle = serializers.StringRelatedField(
        source="proveedor_servicio", read_only=True
    )
    estado_item_display = serializers.CharField(source="get_estado_item_display", read_only=True)

    alojamiento_details = serializers.JSONField(write_only=True, required=False, allow_null=True)
    alquiler_auto_details = serializers.JSONField(write_only=True, required=False, allow_null=True)
    traslado_details = serializers.JSONField(write_only=True, required=False, allow_null=True)
    tour_actividad_details = serializers.JSONField(write_only=True, required=False, allow_null=True)
    seguro_viaje_details = serializers.JSONField(write_only=True, required=False, allow_null=True)
    servicio_adicional_details = serializers.JSONField(
        write_only=True, required=False, allow_null=True
    )

    class Meta:
        model = ItemVenta
        fields = [
            "id_item_venta",
            "producto_servicio",
            "producto_servicio_detalle",
            "descripcion_personalizada",
            "cantidad",
            "precio_unitario_venta",
            "costo_unitario_referencial",
            "impuestos_item_venta",
            "subtotal_item_venta",
            "total_item_venta",
            "fecha_inicio_servicio",
            "fecha_fin_servicio",
            "codigo_reserva_proveedor",
            "proveedor_servicio",
            "proveedor_servicio_detalle",
            "estado_item",
            "estado_item_display",
            "notas_item",
            "alojamiento_details",
            "alquiler_auto_details",
            "traslado_details",
            "tour_actividad_details",
            "seguro_viaje_details",
            "servicio_adicional_details",
        ]
        read_only_fields = ("subtotal_item_venta", "total_item_venta")
        extra_kwargs = {
            "venta": {"write_only": True, "required": False},
            "producto_servicio": {"write_only": True, "allow_null": False, "required": True},
            "proveedor_servicio": {"allow_null": True, "required": False},
        }


class SegmentoVueloSerializer(serializers.ModelSerializer):
    origen_detalle = CiudadSerializer(source="origen", read_only=True)
    destino_detalle = CiudadSerializer(source="destino", read_only=True)

    class Meta:
        model = SegmentoVuelo
        fields = [
            "id_segmento_vuelo",
            "venta",
            "origen",
            "origen_detalle",
            "destino",
            "destino_detalle",
            "aerolinea",
            "numero_vuelo",
            "fecha_salida",
            "fecha_llegada",
            "clase_reserva",
            "cabina",
            "notas",
        ]
        extra_kwargs = {"venta": {"write_only": True, "required": True}}


class AlojamientoReservaSerializer(serializers.ModelSerializer):
    ciudad_detalle = CiudadSerializer(source="ciudad", read_only=True)
    proveedor_detalle = serializers.StringRelatedField(source="proveedor", read_only=True)

    class Meta:
        model = AlojamientoReserva
        fields = [
            "id_alojamiento_reserva",
            "venta",
            "proveedor",
            "proveedor_detalle",
            "ciudad",
            "ciudad_detalle",
            "nombre_establecimiento",
            "check_in",
            "check_out",
            "regimen_alimentacion",
            "habitaciones",
            "notas",
        ]
        extra_kwargs = {"venta": {"write_only": True, "required": True}}


class TrasladoServicioSerializer(serializers.ModelSerializer):
    proveedor_detalle = serializers.StringRelatedField(source="proveedor", read_only=True)
    tipo_traslado_display = serializers.CharField(
        source="get_tipo_traslado_display", read_only=True
    )

    class Meta:
        model = TrasladoServicio
        fields = [
            "id_traslado_servicio",
            "venta",
            "tipo_traslado",
            "tipo_traslado_display",
            "origen",
            "destino",
            "fecha_hora",
            "proveedor",
            "proveedor_detalle",
            "pasajeros",
            "notas",
        ]
        extra_kwargs = {"venta": {"write_only": True, "required": True}}


class ActividadServicioSerializer(serializers.ModelSerializer):
    proveedor_detalle = serializers.StringRelatedField(source="proveedor", read_only=True)

    class Meta:
        model = ActividadServicio
        fields = [
            "id_actividad_servicio",
            "venta",
            "nombre",
            "fecha",
            "duracion_horas",
            "incluye",
            "no_incluye",
            "proveedor",
            "proveedor_detalle",
            "notas",
        ]
        extra_kwargs = {"venta": {"write_only": True, "required": True}}


class AlquilerAutoReservaSerializer(serializers.ModelSerializer):
    margen_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    margen_pct = serializers.SerializerMethodField()

    class Meta:
        model = AlquilerAutoReserva
        fields = [
            "id_alquiler_auto",
            "venta",
            "item_venta",
            "proveedor",
            "ciudad_retiro",
            "ciudad_devolucion",
            "fecha_hora_retiro",
            "fecha_hora_devolucion",
            "categoria_auto",
            "compania_rentadora",
            "numero_confirmacion",
            "nombre_conductor",
            "incluye_seguro",
            "notas",
            "costo_neto",
            "precio_venta",
            "margen_amount",
            "margen_pct",
            "agencia",
            "is_deleted",
            "deleted_at",
        ]
        read_only_fields = ["agencia", "is_deleted", "deleted_at"]

    def get_margen_pct(self, obj):
        return float(obj.margen_pct) if obj.margen_pct is not None else None


class EventoServicioSerializer(serializers.ModelSerializer):
    margen_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    margen_pct = serializers.SerializerMethodField()

    class Meta:
        model = EventoServicio
        fields = [
            "id_evento_servicio",
            "venta",
            "item_venta",
            "proveedor",
            "nombre_evento",
            "fecha_evento",
            "ubicacion",
            "zona_asiento",
            "codigo_boleto_evento",
            "notas",
            "costo_neto",
            "precio_venta",
            "margen_amount",
            "margen_pct",
            "agencia",
            "is_deleted",
            "deleted_at",
        ]
        read_only_fields = ["agencia", "is_deleted", "deleted_at"]

    def get_margen_pct(self, obj):
        return float(obj.margen_pct) if obj.margen_pct is not None else None


class CircuitoDiaSerializer(serializers.ModelSerializer):
    class Meta:
        model = CircuitoDia
        fields = [
            "id_circuito_dia",
            "circuito",
            "dia_numero",
            "titulo",
            "descripcion",
            "ciudad",
            "alojamiento_previsto",
            "actividades_resumen",
            "agencia",
        ]
        read_only_fields = ["agencia"]


class CircuitoTuristicoSerializer(serializers.ModelSerializer):
    dias = CircuitoDiaSerializer(many=True, read_only=True)
    margen_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    margen_pct = serializers.SerializerMethodField()

    class Meta:
        model = CircuitoTuristico
        fields = [
            "id_circuito",
            "venta",
            "item_venta",
            "nombre_circuito",
            "dias_total",
            "fecha_inicio",
            "fecha_fin",
            "descripcion_general",
            "incluye",
            "no_incluye",
            "costo_neto_estimado",
            "precio_venta_estimado",
            "dias",
            "margen_amount",
            "margen_pct",
            "agencia",
        ]
        read_only_fields = ["agencia"]

    def get_margen_pct(self, obj):
        return float(obj.margen_pct) if obj.margen_pct is not None else None


class PaqueteAereoSerializer(serializers.ModelSerializer):
    margen_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    margen_pct = serializers.SerializerMethodField()

    class Meta:
        model = PaqueteAereo
        fields = [
            "id_paquete_aereo",
            "venta",
            "item_venta",
            "nombre_paquete",
            "incluye_vuelos",
            "incluye_hotel",
            "noches",
            "pasajeros",
            "resumen_componentes",
            "observaciones",
            "costo_neto_estimado",
            "precio_venta_estimado",
            "margen_amount",
            "margen_pct",
            "agencia",
        ]
        read_only_fields = ["agencia"]

    def get_margen_pct(self, obj):
        return float(obj.margen_pct) if obj.margen_pct is not None else None


class ServicioAdicionalDetalleSerializer(serializers.ModelSerializer):
    margen_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    margen_pct = serializers.SerializerMethodField()

    class Meta:
        model = ServicioAdicionalDetalle
        fields = [
            "id_servicio_adicional",
            "venta",
            "item_venta",
            "proveedor",
            "tipo_servicio",
            "descripcion",
            "codigo_referencia",
            "fecha_inicio",
            "fecha_fin",
            "nombre_pasajero",
            "notas",
            "costo_neto",
            "precio_venta",
            "margen_amount",
            "margen_pct",
            "agencia",
        ]
        read_only_fields = ["agencia"]

    def get_margen_pct(self, obj):
        return float(obj.margen_pct) if obj.margen_pct is not None else None


class FeeVentaSerializer(serializers.ModelSerializer):
    tipo_fee_display = serializers.CharField(source="get_tipo_fee_display", read_only=True)
    moneda_detalle = MonedaSerializer(source="moneda", read_only=True)

    class Meta:
        model = FeeVenta
        fields = [
            "id_fee_venta",
            "venta",
            "tipo_fee",
            "tipo_fee_display",
            "descripcion",
            "monto",
            "moneda",
            "moneda_detalle",
            "es_comision_agencia",
            "taxable",
            "creado",
        ]
        read_only_fields = ("creado",)
        extra_kwargs = {
            "venta": {"write_only": True, "required": True},
            "moneda": {"write_only": True, "required": True},
        }


class PagoVentaSerializer(serializers.ModelSerializer):
    metodo_display = serializers.CharField(source="get_metodo_display", read_only=True)
    moneda_detalle = MonedaSerializer(source="moneda", read_only=True)

    class Meta:
        model = PagoVenta
        fields = [
            "id_pago_venta",
            "venta",
            "fecha_pago",
            "monto",
            "moneda",
            "moneda_detalle",
            "metodo",
            "metodo_display",
            "referencia",
            "confirmado",
            "notas",
            "creado",
            "aplica_igtf",
            "tasa_igtf",
            "monto_igtf",
        ]
        read_only_fields = ("creado",)
        extra_kwargs = {
            "venta": {"write_only": True, "required": True},
            "moneda": {"write_only": True, "required": True},
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
    cliente_detalle = CoreClienteSerializer(source="cliente", read_only=True)
    moneda_detalle = MonedaSerializer(source="moneda", read_only=True)
    estado_display = serializers.CharField(source="get_estado_display", read_only=True)
    tipo_venta_display = serializers.CharField(source="get_tipo_venta_display", read_only=True)
    canal_origen_display = serializers.CharField(source="get_canal_origen_display", read_only=True)
    puntos_fidelidad_asignados = serializers.BooleanField(read_only=True)
    amount_consistency = serializers.CharField(read_only=True, required=False, allow_null=True)
    amount_difference = serializers.CharField(read_only=True, required=False, allow_null=True)
    taxes_amount_expected = serializers.CharField(read_only=True, required=False, allow_null=True)
    taxes_difference = serializers.CharField(read_only=True, required=False, allow_null=True)

    class Meta:
        model = Venta
        fields = [
            "id_venta",
            "localizador",
            "cliente",
            "cliente_detalle",
            "cotizacion_origen",
            "fecha_venta",
            "descripcion_general",
            "moneda",
            "moneda_detalle",
            "tipo_venta",
            "tipo_venta_display",
            "canal_origen",
            "canal_origen_display",
            "subtotal",
            "impuestos",
            "total_venta",
            "monto_pagado",
            "saldo_pendiente",
            "margen_estimado",
            "co2_estimado_kg",
            "estado",
            "estado_display",
            "asiento_contable_venta",
            "notas",
            "creado_por",
            "items_venta",
            "segmentos_vuelo",
            "alojamientos",
            "traslados",
            "actividades",
            "fees_venta",
            "pagos_venta",
            "alquileres_autos",
            "eventos_servicios",
            "circuitos_turisticos",
            "paquetes_aereos",
            "servicios_adicionales",
            "puntos_fidelidad_asignados",
            "amount_consistency",
            "amount_difference",
            "taxes_amount_expected",
            "taxes_difference",
        ]
        read_only_fields = (
            "localizador",
            "total_venta",
            "saldo_pendiente",
            "fecha_venta",
            "creado_por",
            "segmentos_vuelo",
            "alojamientos",
            "traslados",
            "actividades",
            "fees_venta",
            "pagos_venta",
            "alquileres_autos",
            "eventos_servicios",
            "circuitos_turisticos",
            "paquetes_aereos",
            "servicios_adicionales",
        )
        extra_kwargs = {
            "cliente": {"write_only": True, "allow_null": False, "required": True},
            "moneda": {"write_only": True, "allow_null": False, "required": True},
            "cotizacion_origen": {"allow_null": True, "required": False},
            "asiento_contable_venta": {"allow_null": True, "required": False},
        }

    def create(self, validated_data):
        import logging

        logger = logging.getLogger(__name__)

        items_data = validated_data.pop("items_venta", [])
        logger.info(f"[VENTA DEBUG] Creando venta con {len(items_data)} items")
        venta = Venta.objects.create(**validated_data)
        logger.info(f"[VENTA DEBUG] Venta creada con ID: {venta.id_venta}")

        for item_data in items_data:
            alojamiento_details = item_data.pop("alojamiento_details", None)
            alquiler_auto_details = item_data.pop("alquiler_auto_details", None)
            traslado_details = item_data.pop("traslado_details", None)
            tour_actividad_details = item_data.pop("tour_actividad_details", None)
            seguro_viaje_details = item_data.pop("seguro_viaje_details", None)
            servicio_adicional_details = item_data.pop("servicio_adicional_details", None)

            ItemVenta.objects.create(venta=venta, **item_data)

            if alojamiento_details:
                if "ciudad" in alojamiento_details and alojamiento_details["ciudad"]:
                    alojamiento_details["ciudad_id"] = alojamiento_details.pop("ciudad")
                if "proveedor" in alojamiento_details and alojamiento_details["proveedor"]:
                    alojamiento_details["proveedor_id"] = alojamiento_details.pop("proveedor")
                AlojamientoReserva.objects.create(venta=venta, **alojamiento_details)

            if alquiler_auto_details:
                alquiler_data = {
                    "venta": venta,
                    "compania_rentadora": alquiler_auto_details.get("compania_rentadora"),
                    "categoria_auto": alquiler_auto_details.get("categoria_auto"),
                    "fecha_hora_retiro": f"{alquiler_auto_details.get('fecha_recogida')} {alquiler_auto_details.get('hora_recogida', '00:00')}"
                    if alquiler_auto_details.get("fecha_recogida")
                    else None,
                    "fecha_hora_devolucion": f"{alquiler_auto_details.get('fecha_devolucion')} {alquiler_auto_details.get('hora_devolucion', '00:00')}"
                    if alquiler_auto_details.get("fecha_devolucion")
                    else None,
                    "ciudad_retiro_id": alquiler_auto_details.get("ciudad_retiro"),
                    "ciudad_devolucion_id": alquiler_auto_details.get("ciudad_devolucion"),
                    "incluye_seguro": alquiler_auto_details.get("incluye_seguro", False),
                    "numero_confirmacion": alquiler_auto_details.get("numero_confirmacion"),
                    "proveedor_id": alquiler_auto_details.get("proveedor"),
                    "notas": alquiler_auto_details.get("notas"),
                }
                AlquilerAutoReserva.objects.create(**alquiler_data)

            if traslado_details:
                import logging

                logger = logging.getLogger(__name__)
                logger.info(f"[TRASLADO DEBUG] traslado_details recibido: {traslado_details}")

                traslados_list = traslado_details.get("traslados", [])
                pasajeros = traslado_details.get("pasajeros", 1)
                proveedor_id = traslado_details.get("proveedor")
                notas = traslado_details.get("notas")

                logger.info(
                    f"[TRASLADO DEBUG] traslados_list: {traslados_list}, pasajeros: {pasajeros}"
                )

                for traslado_item in traslados_list:
                    fecha_hora_str = None
                    if traslado_item.get("fecha_hora") and traslado_item.get("hora"):
                        fecha_hora_str = (
                            f"{traslado_item.get('fecha_hora')} {traslado_item.get('hora')}"
                        )
                    elif traslado_item.get("fecha_hora"):
                        fecha_hora_str = traslado_item.get("fecha_hora")

                    traslado_data = {
                        "venta": venta,
                        "origen": traslado_item.get("origen"),
                        "destino": traslado_item.get("destino"),
                        "fecha_hora": fecha_hora_str,
                        "pasajeros": pasajeros,
                        "proveedor_id": proveedor_id,
                        "notas": notas,
                    }
                    logger.info(f"[TRASLADO DEBUG] Creando traslado con data: {traslado_data}")
                    traslado_creado = TrasladoServicio.objects.create(**traslado_data)
                    logger.info(
                        f"[TRASLADO DEBUG] Traslado creado con ID: {traslado_creado.id_traslado_servicio}"
                    )

            if tour_actividad_details:
                if "proveedor" in tour_actividad_details and tour_actividad_details["proveedor"]:
                    tour_actividad_details["proveedor_id"] = tour_actividad_details.pop("proveedor")
                ActividadServicio.objects.create(venta=venta, **tour_actividad_details)

            if seguro_viaje_details:
                servicio_data = {
                    "venta": venta,
                    "tipo_servicio": "SEG",
                    "descripcion": seguro_viaje_details.get("plan", "Seguro de Viaje"),
                    "proveedor_id": seguro_viaje_details.get("proveedor"),
                    "fecha_inicio": seguro_viaje_details.get("fecha_salida"),
                    "fecha_fin": seguro_viaje_details.get("fecha_regreso"),
                    "detalles_cobertura": f"Cobertura: USD {seguro_viaje_details.get('cobertura_monto', 0)}",
                    "notas": seguro_viaje_details.get("notas"),
                    "metadata_json": seguro_viaje_details,
                }
                ServicioAdicionalDetalle.objects.create(**servicio_data)

            if servicio_adicional_details:
                tipo_map = {
                    "SIM / E-SIM": "SIM",
                    "Asistencia": "AST",
                    "Lounge": "LNG",
                    "Otro": "OTR",
                }
                tipo_frontend = servicio_adicional_details.get("tipo_servicio", "Otro")
                tipo_modelo = tipo_map.get(tipo_frontend, "OTR")

                servicio_data = {
                    "venta": venta,
                    "tipo_servicio": tipo_modelo,
                    "descripcion": servicio_adicional_details.get("descripcion"),
                    "proveedor_id": servicio_adicional_details.get("proveedor"),
                    "notas": servicio_adicional_details.get("notas"),
                }

                if servicio_adicional_details.get("lugar"):
                    servicio_data["hora_lugar_encuentro"] = servicio_adicional_details.get("lugar")

                if servicio_adicional_details.get("fecha"):
                    servicio_data["fecha_inicio"] = servicio_adicional_details.get("fecha")

                if servicio_adicional_details.get("destino"):
                    servicio_data["descripcion"] = (
                        f"{servicio_data.get('descripcion', '')} - Destino: {servicio_adicional_details.get('destino')}".strip(
                            " -"
                        )
                    )

                if servicio_adicional_details.get("fecha_salida"):
                    servicio_data["fecha_inicio"] = servicio_adicional_details.get("fecha_salida")

                if servicio_adicional_details.get("fecha_retorno"):
                    servicio_data["fecha_fin"] = servicio_adicional_details.get("fecha_retorno")

                if servicio_adicional_details.get("duracion_horas"):
                    servicio_data["duracion_estimada"] = (
                        f"{servicio_adicional_details.get('duracion_horas')} horas"
                    )

                if servicio_adicional_details.get("pasajeros"):
                    servicio_data["participantes"] = str(
                        servicio_adicional_details.get("pasajeros")
                    )

                servicio_data["metadata_json"] = servicio_adicional_details

                ServicioAdicionalDetalle.objects.create(**servicio_data)

        from apps.finance.services.finance_service import FinanceService

        FinanceService.recalculate_sale_finances(venta.pk)
        venta.refresh_from_db()

        return venta

    def update(self, instance, validated_data):
        items_data = validated_data.pop("items_venta", None)
        for attr in [
            "cliente",
            "cotizacion_origen",
            "descripcion_general",
            "moneda",
            "subtotal",
            "impuestos",
            "monto_pagado",
            "estado",
            "asiento_contable_venta",
            "notas",
            "tipo_venta",
            "canal_origen",
            "margen_estimado",
            "co2_estimado_kg",
        ]:
            if attr in validated_data:
                setattr(instance, attr, validated_data[attr])
        instance.save()

        from apps.finance.services.finance_service import FinanceService

        FinanceService.recalculate_sale_finances(instance.pk)
        instance.refresh_from_db()

        if items_data is not None:
            instance.items_venta.all().delete()
            for item_data in items_data:
                ItemVenta.objects.create(venta=instance, **item_data)

            FinanceService.recalculate_sale_finances(instance.pk)
            instance.refresh_from_db()

        return instance


class VentaParseMetadataSerializer(serializers.ModelSerializer):
    class Meta:
        model = VentaParseMetadata
        fields = [
            "id_metadata",
            "venta",
            "fuente",
            "currency",
            "fare_amount",
            "taxes_amount",
            "total_amount",
            "amount_consistency",
            "amount_difference",
            "taxes_amount_expected",
            "taxes_difference",
            "segments_json",
            "raw_normalized_json",
            "creado",
        ]
        read_only_fields = ("creado",)


class ItinerarioSegmentoSerializer(serializers.Serializer):
    origen_iata = serializers.CharField(max_length=3, required=False)
    destino_iata = serializers.CharField(max_length=3, required=False)
    numero_vuelo = serializers.CharField(max_length=10, required=False)
    fecha_salida = serializers.DateTimeField(required=False)

    class Meta:
        fields = ["origen_iata", "destino_iata", "numero_vuelo", "fecha_salida"]


class GeminiBoletoParseadoSerializer(serializers.Serializer):
    localizador_pnr = serializers.CharField(max_length=10)
    nombre_pasajero_completo = serializers.CharField(max_length=150)
    numero_boleto = serializers.CharField(max_length=50, required=False, allow_null=True)
    aerolinea_emisora = serializers.CharField(max_length=100, required=False, allow_null=True)
    tarifa_base = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True
    )
    impuestos_total = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True
    )
    total_boleto = serializers.DecimalField(max_digits=10, decimal_places=2)
    itinerario = ItinerarioSegmentoSerializer(many=True, required=False)

    def create(self, validated_data):
        return validated_data
