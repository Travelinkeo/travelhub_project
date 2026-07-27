"""
Admin de Ventas — apps/bookings/admin_ventas.py

Contiene: VentaAdmin + Inlines de Venta + acciones de facturación/liquidación/vouchers.
Importado por admin.py vía: from .admin_ventas import *  # noqa
"""

import logging

from django import forms
from django.contrib import admin, messages
from django.core.files.base import ContentFile
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.utils.html import format_html
from unfold.admin import ModelAdmin, StackedInline, TabularInline

from apps.crm.models import Cliente
from core.api import MigrationCheckInline, SaaSAdminMixin, validate_migration_requirements_action

from .models import (
    ActividadServicio,
    AlojamientoReserva,
    AlquilerAutoReserva,
    BoletoImportado,
    FeeVenta,
    ItemVenta,
    PagoVenta,
    SegmentoVuelo,
    ServicioAdicionalDetalle,
    TrasladoServicio,
    Venta,
    VentaParseMetadata,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
@admin.register(ItemVenta)
class ItemVentaAdmin(SaaSAdminMixin, ModelAdmin):
    """ItemVentaAdmin."""

    list_display = (
        "id_item_venta",
        "venta",
        "producto_servicio",
        "descripcion_personalizada",
        "cantidad",
        "precio_unitario_venta",
        "total_item_venta",
    )
    search_fields = ("descripcion_personalizada", "codigo_reserva_proveedor")
    list_filter = ("fecha_inicio_servicio",)


# ---------------------------------------------------------------------------
# Formulario de selección de cliente para acción de facturación
# ---------------------------------------------------------------------------
class FacturaClienteSelectionForm(forms.Form):
    """FacturaClienteSelectionForm."""

    cliente = forms.ModelChoiceField(
        queryset=Cliente.objects.all(),
        label="Cliente a Facturar",
        help_text="Seleccione el cliente que asumirá el cobro de la factura consolidada.",
    )


# ---------------------------------------------------------------------------
# Inlines de Venta
# ---------------------------------------------------------------------------
class ItemVentaInline(TabularInline):
    """ItemVentaInline."""

    model = ItemVenta
    extra = 1
    autocomplete_fields = ["producto_servicio", "proveedor_servicio"]
    readonly_fields = ("subtotal_item_venta", "total_item_venta")
    fields = (
        "tipo_servicio",
        "descripcion_personalizada",
        "proveedor_servicio",
        "producto_servicio",
        "cantidad",
        "precio_unitario",
        "moneda",
        "costo_neto_proveedor",
        "fee_proveedor",
        "comision_agencia_monto",
        "subtotal_item_venta",
        "total_item_venta",
    )


class SegmentoVueloInline(TabularInline):
    """SegmentoVueloInline."""

    model = SegmentoVuelo
    extra = 0
    autocomplete_fields = ["origen", "destino"]


class AlojamientoReservaInline(StackedInline):
    """AlojamientoReservaInline."""

    model = AlojamientoReserva
    extra = 0
    autocomplete_fields = ["proveedor", "ciudad"]


class AlquilerAutoReservaInline(StackedInline):
    """AlquilerAutoReservaInline."""

    model = AlquilerAutoReserva
    extra = 0
    autocomplete_fields = ["proveedor", "ciudad_retiro", "ciudad_devolucion"]
    fields = (
        "compania_rentadora",
        "proveedor",
        "categoria_vehiculo",
        "modelo_vehiculo",
        "ciudad_retiro",
        "ciudad_devolucion",
        "fecha_hora_retiro",
        "fecha_hora_devolucion",
        "precio_por_dia",
        "dias_alquiler",
        "incluye_seguro",
        "tipo_seguro",
        "costo_seguro",
        "deposito_requerido",
        "monto_deposito",
        "numero_reserva_proveedor",
        "notas_adicionales",
    )


class ServicioAdicionalDetalleInline(StackedInline):
    """ServicioAdicionalDetalleInline."""

    model = ServicioAdicionalDetalle
    extra = 0
    autocomplete_fields = ["proveedor"]
    fields = (
        "tipo_servicio",
        "proveedor",
        "nombre_servicio",
        "codigo_referencia",
        "descripcion_detallada",
        "fecha_inicio",
        "fecha_fin",
        "cantidad_personas",
        "precio_unitario",
        "costo_neto",
        "notas_operativas",
    )


class TrasladoServicioInline(TabularInline):
    """TrasladoServicioInline."""

    model = TrasladoServicio
    extra = 0
    autocomplete_fields = ["proveedor"]


class ActividadServicioInline(TabularInline):
    """ActividadServicioInline."""

    model = ActividadServicio
    extra = 0
    autocomplete_fields = ["proveedor"]


class FeeVentaInline(TabularInline):
    """FeeVentaInline."""

    model = FeeVenta
    extra = 0
    autocomplete_fields = ["moneda"]


class PagoVentaInline(TabularInline):
    """PagoVentaInline."""

    model = PagoVenta
    extra = 0
    autocomplete_fields = ["moneda"]


class VentaAdminForm(forms.ModelForm):
    """VentaAdminForm."""

    class Meta:
        model = Venta
        fields = "__all__"


# ---------------------------------------------------------------------------
# VentaAdmin
# ---------------------------------------------------------------------------
@admin.register(Venta)
class VentaAdmin(SaaSAdminMixin, ModelAdmin):
    """VentaAdmin."""

    def get_queryset(self, request):
        """get_queryset."""
        return (
            super()
            .get_queryset(request)
            .select_related("cliente", "moneda", "agencia", "creado_por")
            .prefetch_related(
                "items_venta__proveedor_servicio",
                "boletos_adjuntos",
                "pagos_venta",
            )
        )

    form = VentaAdminForm
    list_display = (
        "venta_link",
        "cliente",
        "fecha_venta",
        "total_venta",
        "estado",
        "tipo_venta",
        "canal_origen",
        "saldo_pendiente",
    )
    list_display_links = ("venta_link",)
    search_fields = ("localizador", "id_venta", "cliente__nombres", "cliente__apellidos")
    list_filter = ("estado", "fecha_venta", "tipo_venta", "canal_origen")
    autocomplete_fields = ["cliente", "moneda", "cotizacion_origen"]
    inlines = [
        ItemVentaInline,
        SegmentoVueloInline,
        AlojamientoReservaInline,
        AlquilerAutoReservaInline,
        ServicioAdicionalDetalleInline,
        TrasladoServicioInline,
        ActividadServicioInline,
        FeeVentaInline,
        PagoVentaInline,
        MigrationCheckInline,
    ]
    readonly_fields = ("total_venta", "saldo_pendiente", "boleto_importado_link", "margen_estimado")
    actions = [
        "generar_links_de_pago",
        "asignar_cliente_y_facturar",
        "generar_liquidaciones_proveedor",
        "generar_voucher_unificado",
        "generar_doble_facturacion",
        "hard_delete_ventas",
        validate_migration_requirements_action,
    ]

    # --- Métodos de display ---

    def venta_link(self, obj):
        """venta_link."""
        url = reverse("admin:bookings_venta_change", args=[obj.id_venta])
        display_text = obj.localizador or f"Venta #{obj.id_venta}"
        return format_html('<a href="{}">{}</a>', url, display_text)

    venta_link.short_description = "Venta (ID/Localizador)"

    def boleto_importado_link(self, obj):
        """boleto_importado_link."""
        boleto = BoletoImportado.objects.filter(venta_asociada=obj).first()
        if boleto:
            url = reverse("admin:bookings_boletoimportado_change", args=[boleto.pk])
            return format_html('<a href="{}">Ver Boleto Original (ID: {})</a>', url, boleto.pk)
        return "N/A"

    boleto_importado_link.short_description = "Boleto de Origen"

    def get_changeform_initial_data(self, request):
        """get_changeform_initial_data."""
        initial = super().get_changeform_initial_data(request)
        boleto_id = request.GET.get("boleto_id")
        if boleto_id:
            try:
                boleto = BoletoImportado.objects.get(pk=boleto_id)
                initial.update(
                    {
                        "subtotal": boleto.tarifa_base,
                        "impuestos": boleto.impuestos_total_calculado,
                        "localizador": boleto.localizador_pnr,
                    }
                )
            except BoletoImportado.DoesNotExist:
                pass
        return initial

    def has_add_permission(self, request):
        """has_add_permission."""
        return True

    # --- Acciones ---

    @admin.action(description="🔥 ELIMINACIÓN FÍSICA (Irreversible)")
    def hard_delete_ventas(self, request, queryset):
        """hard_delete_ventas."""
        if not request.user.is_superuser:
            self.message_user(
                request, "Solo superusuarios pueden realizar la eliminación física.", level="error"
            )
            return
        count = queryset.count()
        for obj in queryset:
            obj.hard_delete()
        self.message_user(request, f"Se han eliminado físicamente {count} ventas.")

    @admin.action(description="Generar Link de Pago B2C para Ventas seleccionadas")
    def generar_links_de_pago(self, request, queryset):
        """generar_links_de_pago."""
        from apps.finance.models_stubs import LinkDePago

        creados = 0
        existentes = 0
        for venta in queryset:
            if not hasattr(venta, "link_pago"):
                LinkDePago.objects.create(
                    venta=venta,
                    monto_total=venta.total_venta,
                    moneda=venta.moneda.codigo_iso
                    if (venta.moneda and hasattr(venta.moneda, "codigo_iso"))
                    else "USD",
                )
                creados += 1
            else:
                existentes += 1
        self.message_user(
            request,
            f"Se generaron {creados} links de pago nuevos. {existentes} ventas ya tenían link.",
        )

    def generar_doble_facturacion(self, request, queryset):
        """generar_doble_facturacion."""
        from django.utils.module_loading import import_string

        InvoiceService = import_string("apps.finance.services.invoice_service.InvoiceService")
        procesados = 0
        for venta in queryset:
            try:
                InvoiceService.generate_double_invoice(venta)
                procesados += 1
            except Exception as e:
                self.message_user(request, f"Error en Venta {venta.pk}: {str(e)}", level="error")
        if procesados:
            self.message_user(request, f"Doble facturación generada para {procesados} venta(s).")

    generar_doble_facturacion.short_description = (
        "Generar Doble Facturación (Intermediación + Propia)"
    )

    def generar_voucher_unificado(self, request, queryset):
        """generar_voucher_unificado."""
        if queryset.count() != 1:
            messages.error(
                request,
                "Por favor, seleccione exactamente una Venta para generar el voucher unificado.",
            )
            return
        venta = queryset.first()
        from apps.bookings.services.voucher_service import generar_voucher_unificado

        pdf_bytes, filename = generar_voucher_unificado(venta.pk)
        if pdf_bytes:
            response = HttpResponse(pdf_bytes, content_type="application/pdf")
            response["Content-Disposition"] = f'attachment; filename="{filename}"'
            return response
        else:
            messages.error(
                request,
                f"No se pudo generar el voucher para la Venta {venta.localizador or venta.id_venta}.",
            )

    generar_voucher_unificado.short_description = "Generar Voucher Unificado (PDF)"

    def asignar_cliente_y_facturar(self, request, queryset):
        """asignar_cliente_y_facturar."""
        queryset = queryset.filter(cliente__isnull=True, factura__isnull=True)
        if not queryset.exists():
            self.message_user(
                request,
                "Las ventas seleccionadas ya tienen un cliente o ya han sido facturadas.",
                level="warning",
            )
            return
        form = FacturaClienteSelectionForm(request.POST or None)
        if "apply" in request.POST and form.is_valid():
            cliente = form.cleaned_data["cliente"]
            from django.utils.module_loading import import_string

            FacturacionService = import_string(
                "apps.finance.services.facturacion_service.FacturacionService"
            )
            facturas_creadas = 0
            for venta in queryset:
                try:
                    venta.cliente = cliente
                    venta.save(update_fields=["cliente"])
                    factura = FacturacionService.generar_factura_desde_venta(venta, cliente)
                    from apps.common.services.pdf_service import generar_pdf_factura

                    pdf_bytes, pdf_filename = generar_pdf_factura(factura.pk)
                    if pdf_bytes:
                        factura.archivo_pdf.save(pdf_filename, ContentFile(pdf_bytes), save=True)
                    facturas_creadas += 1
                except Exception as e:
                    self.message_user(
                        request, f"Error en Venta {venta.id_venta}: {str(e)}", level="error"
                    )
            if facturas_creadas:
                self.message_user(
                    request, f"{facturas_creadas} factura(s) generada(s) exitosamente."
                )
            return HttpResponseRedirect(request.get_full_path())
        context = {
            "ventas": queryset,
            "cliente_form": form,
            "title": "Asignar Cliente y Facturar",
            "opts": self.model._meta,
        }
        return render(request, "admin/asignar_cliente_y_facturar.html", context)

    @admin.action(description="Generar Liquidación a Proveedor(es)")
    def generar_liquidaciones_proveedor(self, request, queryset):
        """generar_liquidaciones_proveedor."""
        # ELIMINADO: LiquidacionProveedor/ItemLiquidacion creation
        # Feature de liquidaciones a proveedores eliminada en refactor
        self.message_user(request, "Función de liquidaciones desactivada (refactor en curso).")


@admin.register(VentaParseMetadata)
class VentaParseMetadataAdmin(SaaSAdminMixin, ModelAdmin):
    """VentaParseMetadataAdmin."""

    saas_agency_field = "venta__agencia"
    list_display = ("id_metadata", "venta", "fuente", "creado")
    readonly_fields = ("raw_normalized_json", "segments_json", "creado")
