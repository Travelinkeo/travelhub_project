from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from core.api import SaaSAdminMixin

from .models import (
    CanalRecaudacion,
    DocumentoExportacion,
    Factura,
    GastoOperativo,
    ItemFactura,
    LinkDePago,
    Pago,
    PagoBinance,
)
from .models.reconciliacion import (
    ConciliacionBoleto,
    ReporteReconciliacion,
)


@admin.register(LinkDePago)
class LinkDePagoAdmin(SaaSAdminMixin, admin.ModelAdmin):
    list_display = ("id_corto", "venta_pnr", "monto_total", "moneda", "estado", "boton_link")
    list_filter = ("estado", "moneda", "creado_en")
    search_fields = ("venta__localizador", "id", "referencia_pago")
    readonly_fields = ("id", "creado_en")

    def id_corto(self, obj):
        return str(obj.id)[:8] + "..."

    id_corto.short_description = "ID"

    def venta_pnr(self, obj):
        return obj.venta.localizador

    venta_pnr.short_description = "PNR"

    def boton_link(self, obj):
        url = f"/finance/pay/{obj.id}/"
        return format_html(
            '<a href="{}" target="_blank" style="background: #10b981; color: white; padding: 4px 10px; border-radius: 4px; font-weight: bold; text-decoration: none;">Ver Checkout</a>',
            url,
        )

    boton_link.short_description = "B2C Link"


# =======================================================
# FACTURACIÓN UNIFICADA (NORMATIVA VENEZOLANA)
# =======================================================


class ItemFacturaInline(admin.TabularInline):
    model = ItemFactura
    extra = 1
    fields = (
        "descripcion",
        "cantidad",
        "precio_unitario",
        "tipo_servicio",
        "es_gravado",
        "alicuota_iva",
    )


class DocumentoExportacionInline(admin.TabularInline):
    model = DocumentoExportacion
    extra = 0
    fields = ("tipo_documento", "numero_documento", "archivo")


@admin.register(Factura)
class FacturaAdmin(SaaSAdminMixin, admin.ModelAdmin):
    list_display = (
        "numero_factura",
        "cliente",
        "fecha_emision",
        "tipo_operacion",
        "moneda_operacion",
        "monto_total",
        "estado",
    )
    list_filter = (
        "estado",
        "tipo_operacion",
        "moneda_operacion",
        "cliente_es_residente",
        "fecha_emision",
    )
    search_fields = ("numero_factura", "numero_control", "cliente__nombres", "cliente__apellidos")
    readonly_fields = ("subtotal", "monto_total", "saldo_pendiente")
    inlines = [ItemFacturaInline, DocumentoExportacionInline]

    actions = ["generar_pdf_selectos"]

    def generar_pdf_selectos(self, request, queryset):
        from django.contrib import messages

        from apps.finance.services.factura_pdf_generator import guardar_pdf_factura

        success_count = 0
        for factura in queryset:
            if guardar_pdf_factura(factura):
                success_count += 1
        messages.success(request, f"Se generaron {success_count} PDFs exitosamente.")

    generar_pdf_selectos.short_description = "Generar PDFs para facturas seleccionadas"

    fieldsets = (
        ("Identificación", {"fields": ("numero_factura", "numero_control", "venta_asociada")}),
        (
            "Cliente",
            {
                "fields": (
                    "cliente",
                    "cliente_identificacion",
                    "cliente_direccion",
                    "cliente_es_residente",
                )
            },
        ),
        ("Fechas", {"fields": ("fecha_emision", "fecha_vencimiento")}),
        (
            "Emisor",
            {
                "fields": (
                    "emisor_rif",
                    "emisor_razon_social",
                    "emisor_direccion_fiscal",
                    "es_sujeto_pasivo_especial",
                    "esta_inscrita_rtn",
                )
            },
        ),
        (
            "Operación",
            {"fields": ("tipo_operacion", "moneda", "moneda_operacion", "tasa_cambio_bcv")},
        ),
        (
            "Bases Imponibles (USD)",
            {"fields": ("subtotal_base_gravada", "subtotal_exento", "subtotal_exportacion")},
        ),
        ("Impuestos (USD)", {"fields": ("monto_iva_16", "monto_iva_adicional", "monto_igtf")}),
        ("Totales (USD)", {"fields": ("subtotal", "monto_total", "saldo_pendiente")}),
        (
            "Equivalentes en Bolívares",
            {
                "fields": (
                    "subtotal_base_gravada_bs",
                    "subtotal_exento_bs",
                    "monto_iva_16_bs",
                    "monto_igtf_bs",
                    "monto_total_bs",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Intermediación",
            {"fields": ("tercero_rif", "tercero_razon_social"), "classes": ("collapse",)},
        ),
        ("Digital", {"fields": ("modalidad_emision", "firma_digital")}),
        (
            "Estado y Archivos",
            {"fields": ("estado", "archivo_pdf", "asiento_contable_factura", "notas")},
        ),
    )


@admin.register(ItemFactura)
class ItemFacturaAdmin(SaaSAdminMixin, admin.ModelAdmin):
    saas_agency_field = "factura__venta_asociada__agencia"
    list_display = (
        "factura",
        "descripcion",
        "cantidad",
        "precio_unitario",
        "subtotal_item",
        "tipo_servicio",
        "es_gravado",
    )
    list_filter = ("tipo_servicio", "es_gravado")
    search_fields = ("descripcion", "factura__numero_factura", "nombre_pasajero", "numero_boleto")
    readonly_fields = ("subtotal_item",)


@admin.register(DocumentoExportacion)
class DocumentoExportacionAdmin(SaaSAdminMixin, admin.ModelAdmin):
    saas_agency_field = "factura__venta_asociada__agencia"
    list_display = ("factura", "tipo_documento", "numero_documento", "fecha_subida")
    list_filter = ("tipo_documento", "fecha_subida")
    search_fields = ("numero_documento", "factura__numero_factura")


# =======================================================
# MÓDULO DE RECONCILIACIÓN E INTELIGENCIA ARTIFICIAL
# =======================================================


class ConciliacionBoletoInline(admin.TabularInline):
    model = ConciliacionBoleto
    extra = 0
    readonly_fields = (
        "linea_reporte",
        "boleto_local",
        "estado",
        "diferencia_tarifa",
        "diferencia_impuestos",
        "diferencia_total",
    )
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ReporteReconciliacion)
class ReporteReconciliacionAdmin(SaaSAdminMixin, admin.ModelAdmin):
    list_display = (
        "proveedor",
        "fecha_subida",
        "estado",
        "periodo_inicio",
        "periodo_fin",
        "accion_ai_btn",
    )
    list_filter = ("estado", "proveedor")
    inlines = [ConciliacionBoletoInline]
    readonly_fields = ("estado", "datos_extraidos", "resumen_conciliacion", "error_log")

    def accion_ai_btn(self, obj):
        if obj.estado in ["PENDIENTE", "ERROR"]:  # Permitir reintentos
            return format_html(
                '<a class="button" style="background-color: var(--button-bg); color: var(--button-fg);" href="{}">🚀 Parsear Reporte con IA</a>',
                reverse("admin:finance_reconciliacion_process", args=[obj.pk]),
            )
        elif obj.estado == "PROCESANDO":
            return format_html("<b>Procesando (IA)...</b>")
        return format_html("✅ Evaluado")

    accion_ai_btn.short_description = "Motor IA"

    def get_urls(self):
        from django.urls import path

        urls = super().get_urls()
        custom_urls = [
            path(
                "<uuid:report_id>/process_ai/",
                self.admin_site.admin_view(self.process_view),
                name="finance_reconciliacion_process",
            ),
        ]
        return custom_urls + urls

    def process_view(self, request, report_id):
        from django.contrib import messages
        from django.shortcuts import redirect

        from .services.smart_reconciliation_service import SmartReconciliationService

        try:
            SmartReconciliationService.procesar_reporte(report_id)
            messages.success(
                request, "¡Reporte analizado con IA y cruzado estadísticamente con éxito!"
            )
        except Exception as e:
            messages.error(request, f"Fallo en la Inteligencia Artificial o Extracción: {e}")

        return redirect("admin:finance_reportereconciliacion_changelist")


@admin.register(ConciliacionBoleto)
class ConciliacionBoletoAdmin(SaaSAdminMixin, admin.ModelAdmin):
    saas_agency_field = "reporte__agencia"
    list_display = (
        "id_conciliacion",
        "reporte",
        "get_ticket",
        "estado_coloreado",
        "diferencia_total",
        "sugerencia_asiento",
    )
    list_filter = ("estado", "reporte__proveedor")
    search_fields = ("linea_reporte__numero_boleto_reportado", "boleto_local__numero_boleto")

    def get_ticket(self, obj):
        if obj.linea_reporte:
            return obj.linea_reporte.numero_boleto_reportado
        if obj.boleto_local:
            return obj.boleto_local.numero_boleto
        return "Desconocido"

    get_ticket.short_description = "Boleto"

    def estado_coloreado(self, obj):
        colores = {
            "OK": "green",
            "DISCREPANCIA": "red",
            "HUERFANO_PROVEEDOR": "orange",
            "HUERFANO_LOCAL": "purple",
            "IGNORADO": "gray",
        }
        color = colores.get(obj.estado, "black")
        return format_html(
            f'<span style="color: {color}; font-weight: bold;">{obj.get_estado_display()}</span>'
        )

    estado_coloreado.short_description = "Resolución"


@admin.register(GastoOperativo)
class GastoOperativoAdmin(SaaSAdminMixin, admin.ModelAdmin):
    list_display = ("fecha", "descripcion", "moneda", "monto", "categoria", "creado_por")
    list_filter = ("fecha", "categoria", "moneda")
    search_fields = ("descripcion", "categoria")
    date_hierarchy = "fecha"


@admin.register(PagoBinance)
class PagoBinanceAdmin(SaaSAdminMixin, admin.ModelAdmin):
    saas_agency_field = "factura__agencia"
    list_display = ("merchant_trade_no", "factura", "monto", "moneda", "estado", "fecha_creacion")
    list_filter = ("estado", "moneda", "fecha_creacion")
    search_fields = ("merchant_trade_no", "factura__numero_factura", "prepay_id")
    readonly_fields = ("merchant_trade_no", "prepay_id", "checkout_url", "raw_response")


@admin.register(CanalRecaudacion)
class CanalRecaudacionAdmin(SaaSAdminMixin, admin.ModelAdmin):
    list_display = ("nombre", "tipo", "moneda", "activo", "creado")
    list_filter = ("tipo", "moneda", "activo")
    search_fields = ("nombre", "descripcion")


@admin.register(Pago)
class PagoAdmin(SaaSAdminMixin, admin.ModelAdmin):
    list_display = (
        "id_pago",
        "venta",
        "canal_recaudacion",
        "monto",
        "moneda",
        "igtf_monto",
        "igtf_aplicado",
        "confirmado",
        "fecha_pago",
    )
    list_filter = ("moneda", "igtf_aplicado", "confirmado", "fecha_pago", "canal_recaudacion__tipo")
    search_fields = ("venta__localizador", "referencia", "notas")
    readonly_fields = ("igtf_monto", "igtf_aplicado")
