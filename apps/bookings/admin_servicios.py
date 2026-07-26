"""
Admin de Servicios y Tarifarios — apps/bookings/admin_servicios.py

Contiene: AlojamientoReservaAdmin, AlquilerAutoReservaAdmin, EventoServicioAdmin,
          CircuitoTuristicoAdmin, PaqueteAereoAdmin, ServicioAdicionalDetalleAdmin,
          TrasladoServicioAdmin, ActividadServicioAdmin, CircuitoDiaAdmin,
          y todo el bloque de Tarifario/Hoteles.
Importado por admin.py vía: from .admin_servicios import *  # noqa
"""

import logging

from django.contrib import admin, messages
from django.http import HttpResponse
from django.urls import reverse
from django.utils.html import format_html
from unfold.admin import ModelAdmin

from core.api import SaaSAdminMixin

from .models import (
    ActividadServicio,
    AlojamientoReserva,
    AlquilerAutoReserva,
    Amenity,
    CircuitoDia,
    CircuitoTuristico,
    EventoServicio,
    HotelTarifario,
    ImagenHotel,
    PaqueteAereo,
    ProductoServicio,
    Proveedor,
    ServicioAdicionalDetalle,
    TarifaHabitacion,
    TarifarioProveedor,
    TipoHabitacion,
    TrasladoServicio,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers privados — reutilizado por múltiples acciones de vouchers
# ---------------------------------------------------------------------------
def _generar_voucher_pdf(request, pdf_bytes, filename, error_label):
    """_generar_voucher_pdf."""
    if pdf_bytes:
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
    messages.error(request, f"No se pudo generar el voucher para {error_label}.")
    return None


# ---------------------------------------------------------------------------
# Servicios de viaje
# ---------------------------------------------------------------------------
@admin.register(AlojamientoReserva)
class AlojamientoReservaAdmin(SaaSAdminMixin, ModelAdmin):
    """AlojamientoReservaAdmin."""

    saas_agency_field = "venta__agencia"
    list_display = (
        "id_alojamiento_reserva",
        "nombre_establecimiento",
        "venta",
        "check_in",
        "check_out",
        "nombre_pasajero",
    )
    search_fields = ("nombre_establecimiento", "nombre_pasajero", "localizador_proveedor")
    list_filter = ("check_in", "check_out")
    autocomplete_fields = ["venta", "proveedor", "ciudad"]
    actions = ["generar_voucher_hotel"]

    @admin.action(description="Generar Voucher de Hotel (PDF)")
    def generar_voucher_hotel(self, request, queryset):
        """generar_voucher_hotel."""
        if queryset.count() != 1:
            messages.error(
                request, "Por favor, seleccione exactamente una reserva para generar el voucher."
            )
            return
        reserva = queryset.first()
        from apps.bookings.services.voucher_service import generar_voucher_alojamiento

        pdf_bytes, filename = generar_voucher_alojamiento(reserva)
        return _generar_voucher_pdf(request, pdf_bytes, filename, reserva.nombre_establecimiento)


@admin.register(AlquilerAutoReserva)
class AlquilerAutoReservaAdmin(SaaSAdminMixin, ModelAdmin):
    """AlquilerAutoReservaAdmin."""

    saas_agency_field = "venta__agencia"
    list_display = ("id_alquiler_auto", "venta", "compania_rentadora", "fecha_hora_retiro")
    autocomplete_fields = ["venta", "proveedor", "ciudad_retiro", "ciudad_devolucion"]
    actions = ["generar_voucher_auto"]

    @admin.action(description="Generar Voucher de Auto (PDF)")
    def generar_voucher_auto(self, request, queryset):
        """generar_voucher_auto."""
        if queryset.count() != 1:
            messages.error(
                request, "Por favor, seleccione exactamente un alquiler para generar el voucher."
            )
            return
        alquiler = queryset.first()
        from apps.bookings.services.voucher_service import generar_voucher_alquiler_auto

        pdf_bytes, filename = generar_voucher_alquiler_auto(alquiler)
        return _generar_voucher_pdf(request, pdf_bytes, filename, f"alquiler {alquiler.pk}")


@admin.register(EventoServicio)
class EventoServicioAdmin(SaaSAdminMixin, ModelAdmin):
    """EventoServicioAdmin."""

    saas_agency_field = "venta__agencia"
    list_display = ("id_evento_servicio", "venta", "nombre_evento", "fecha_evento")
    autocomplete_fields = ["venta", "proveedor"]


@admin.register(CircuitoTuristico)
class CircuitoTuristicoAdmin(SaaSAdminMixin, ModelAdmin):
    """CircuitoTuristicoAdmin."""

    saas_agency_field = "venta__agencia"
    list_display = ("id_circuito", "venta", "nombre_circuito", "fecha_inicio")
    search_fields = ("nombre_circuito",)
    autocomplete_fields = ["venta"]


@admin.register(PaqueteAereo)
class PaqueteAereoAdmin(SaaSAdminMixin, ModelAdmin):
    """PaqueteAereoAdmin."""

    saas_agency_field = "venta__agencia"
    list_display = ("id_paquete_aereo", "venta", "nombre_paquete")
    autocomplete_fields = ["venta"]


@admin.register(ServicioAdicionalDetalle)
class ServicioAdicionalDetalleAdmin(SaaSAdminMixin, ModelAdmin):
    """ServicioAdicionalDetalleAdmin."""

    saas_agency_field = "venta__agencia"
    list_display = ("id_servicio_adicional", "venta", "tipo_servicio", "codigo_referencia")
    autocomplete_fields = ["venta", "proveedor"]
    actions = ["generar_voucher_servicio_action"]

    @admin.action(description="Generar Voucher de Servicio (PDF)")
    def generar_voucher_servicio_action(self, request, queryset):
        """generar_voucher_servicio_action."""
        if queryset.count() != 1:
            messages.error(
                request, "Por favor, seleccione exactamente un servicio para generar el voucher."
            )
            return
        servicio = queryset.first()
        from apps.bookings.services.voucher_service import generar_voucher_servicio

        pdf_bytes, filename = generar_voucher_servicio(servicio)
        return _generar_voucher_pdf(request, pdf_bytes, filename, f"servicio {servicio.pk}")


@admin.register(TrasladoServicio)
class TrasladoServicioAdmin(SaaSAdminMixin, ModelAdmin):
    """TrasladoServicioAdmin."""

    saas_agency_field = "venta__agencia"
    list_display = (
        "id_traslado_servicio",
        "venta",
        "tipo_traslado",
        "origen",
        "destino",
        "fecha_hora",
    )
    autocomplete_fields = ["venta", "proveedor"]
    actions = ["generar_voucher_traslado_action"]

    @admin.action(description="Generar Voucher de Traslado (PDF)")
    def generar_voucher_traslado_action(self, request, queryset):
        """generar_voucher_traslado_action."""
        if queryset.count() != 1:
            messages.error(
                request, "Por favor, seleccione exactamente un traslado para generar el voucher."
            )
            return
        traslado = queryset.first()
        from apps.bookings.services.voucher_service import generar_voucher_traslado

        pdf_bytes, filename = generar_voucher_traslado(traslado)
        return _generar_voucher_pdf(request, pdf_bytes, filename, f"traslado {traslado.pk}")


@admin.register(ActividadServicio)
class ActividadServicioAdmin(SaaSAdminMixin, ModelAdmin):
    """ActividadServicioAdmin."""

    saas_agency_field = "venta__agencia"
    list_display = ("id_actividad_servicio", "venta", "nombre", "fecha", "proveedor")
    autocomplete_fields = ["venta", "proveedor"]
    actions = ["generar_voucher_actividad_action"]

    @admin.action(description="Generar Voucher de Actividad (PDF)")
    def generar_voucher_actividad_action(self, request, queryset):
        """generar_voucher_actividad_action."""
        if queryset.count() != 1:
            messages.error(
                request, "Por favor, seleccione exactamente una actividad para generar el voucher."
            )
            return
        actividad = queryset.first()
        from apps.bookings.services.voucher_service import generar_voucher_actividad

        pdf_bytes, filename = generar_voucher_actividad(actividad)
        return _generar_voucher_pdf(request, pdf_bytes, filename, f"actividad {actividad.pk}")


@admin.register(CircuitoDia)
class CircuitoDiaAdmin(SaaSAdminMixin, ModelAdmin):
    """CircuitoDiaAdmin."""

    saas_agency_field = "circuito__agencia"
    list_display = ["circuito", "dia_numero", "titulo", "ciudad"]
    list_filter = ["circuito"]
    autocomplete_fields = ["circuito", "ciudad"]


# ---------------------------------------------------------------------------
# Tarifarios y Hoteles
# ---------------------------------------------------------------------------
class TarifaHabitacionInline(admin.TabularInline):
    """TarifaHabitacionInline."""

    model = TarifaHabitacion
    extra = 1
    fields = [
        "fecha_inicio",
        "fecha_fin",
        "nombre_temporada",
        "moneda",
        "tipo_tarifa",
        "tarifa_sgl",
        "tarifa_dbl",
        "tarifa_tpl",
        "tarifa_cpl",
        "tarifa_nino",
    ]


class TipoHabitacionInline(admin.TabularInline):
    """TipoHabitacionInline."""

    model = TipoHabitacion
    extra = 1
    fields = [
        "nombre",
        "capacidad_adultos",
        "capacidad_ninos",
        "capacidad_total",
        "edit_rates_link",
    ]
    readonly_fields = ["edit_rates_link"]

    def edit_rates_link(self, obj):
        """edit_rates_link."""
        if obj.id:
            url = reverse("admin:bookings_tipohabitacion_change", args=[obj.id])
            return format_html(
                '<a href="{}" target="_blank" class="button" style="background-color:#4f46e5;color:white;padding:4px 8px;border-radius:4px;">Gestionar Tarifas</a>',
                url,
            )
        return "-"

    edit_rates_link.short_description = "Tarifas"


class ImagenHotelInline(admin.TabularInline):
    """ImagenHotelInline."""

    model = ImagenHotel
    extra = 2
    fields = ["imagen", "titulo", "tipo", "es_portada"]


@admin.register(Amenity)
class AmenityAdmin(ModelAdmin):
    """AmenityAdmin."""

    list_display = ["nombre", "icono_lucide"]
    search_fields = ["nombre"]


@admin.register(TarifarioProveedor)
class TarifarioProveedorAdmin(SaaSAdminMixin, ModelAdmin):
    """TarifarioProveedorAdmin."""

    saas_agency_field = "proveedor__agencia"
    list_display = [
        "id",
        "nombre",
        "proveedor",
        "fecha_vigencia_inicio",
        "fecha_vigencia_fin",
        "comision_estandar",
        "activo",
    ]
    list_filter = ["activo", "proveedor"]
    search_fields = ["nombre"]


@admin.register(HotelTarifario)
class HotelTarifarioAdmin(SaaSAdminMixin, ModelAdmin):
    """HotelTarifarioAdmin."""

    saas_agency_field = "tarifario__proveedor__agencia"
    list_display = ["nombre", "destino", "categoria", "regimen_default", "activo", "destacado"]
    list_filter = ["activo", "destacado", "destino", "categoria"]
    search_fields = ["nombre", "destino", "descripcion_larga"]
    prepopulated_fields = {"slug": ("nombre", "destino")}
    filter_horizontal = ["amenidades"]
    inlines = [ImagenHotelInline, TipoHabitacionInline]
    fieldsets = [
        (
            "Información Principal",
            {
                "fields": [
                    "tarifario",
                    "nombre",
                    "slug",
                    "destino",
                    "imagen_principal",
                    "logo",
                    "video_promocional",
                    "categoria",
                ]
            },
        ),
        (
            "Detalles y Geolocalización",
            {"fields": ["descripcion_corta", "descripcion_larga", "direccion", "coordenadas_mapa"]},
        ),
        ("Servicios", {"fields": ["amenidades"]}),
        ("Operativo", {"fields": ["regimen_default", "comision", "politicas"]}),
        ("Configuración", {"fields": ["check_in", "check_out", "activo", "destacado"]}),
    ]


@admin.register(TarifaHabitacion)
class TarifaHabitacionAdmin(SaaSAdminMixin, ModelAdmin):
    """TarifaHabitacionAdmin."""

    saas_agency_field = "tipo_habitacion__hotel__tarifario__proveedor__agencia"
    list_display = [
        "tipo_habitacion",
        "fecha_inicio",
        "fecha_fin",
        "moneda",
        "tarifa_sgl",
        "tarifa_dbl",
    ]
    list_filter = ["moneda", "tipo_habitacion__hotel"]
    search_fields = ["tipo_habitacion__nombre", "tipo_habitacion__hotel__nombre"]


@admin.register(TipoHabitacion)
class TipoHabitacionAdmin(SaaSAdminMixin, ModelAdmin):
    """Permite editar tarifas directamente desde el Tipo de Habitación."""

    saas_agency_field = "hotel__tarifario__proveedor__agencia"
    list_display = ["nombre", "hotel", "capacidad_total"]
    list_filter = ["hotel"]
    search_fields = ["nombre", "hotel__nombre"]
    inlines = [TarifaHabitacionInline]
    autocomplete_fields = ["hotel"]


# ---------------------------------------------------------------------------
# Catálogos base (requeridos por autocomplete_fields en otros admins)
# ---------------------------------------------------------------------------
@admin.register(Proveedor)
class ProveedorAdmin(SaaSAdminMixin, ModelAdmin):
    """ProveedorAdmin."""

    list_display = ["nombre", "tipo_proveedor", "activo"]
    search_fields = ["nombre", "rif"]
    list_filter = ["tipo_proveedor", "activo"]
    ordering = ["nombre"]


@admin.register(ProductoServicio)
class ProductoServicioAdmin(SaaSAdminMixin, ModelAdmin):
    """ProductoServicioAdmin."""

    list_display = ["nombre", "tipo_producto", "activo"]
    search_fields = ["nombre", "codigo_interno"]
    list_filter = ["tipo_producto", "activo"]
    ordering = ["nombre"]
