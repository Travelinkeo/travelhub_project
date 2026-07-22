from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from core.api import SaaSAdminMixin

from .models import Factura, ItemFactura, Pago


class ItemFacturaInline(TabularInline):
    model = ItemFactura
    extra = 1
    fields = ("descripcion", "cantidad", "precio_unitario_usd", "exento", "total_linea_usd")


@admin.register(Factura)
class FacturaAdmin(SaaSAdminMixin, ModelAdmin):
    list_display = (
        "numero_control",
        "cliente",
        "fecha_emision",
        "gran_total_usd",
        "estado",
    )
    list_filter = ("estado", "fecha_emision")
    search_fields = ("numero_control", "cliente__nombres", "cliente__apellidos")
    inlines = [ItemFacturaInline]

    fieldsets = (
        ("Identificación", {"fields": ("numero_control", "fecha_emision", "cliente")}),
        (
            "Tasa BCV",
            {"fields": ("tasa_bcv_aplicada",)},
        ),
        (
            "Montos USD",
            {
                "fields": (
                    "subtotal_usd",
                    "total_iva_usd",
                    "total_igtf_usd",
                    "gran_total_usd",
                )
            },
        ),
        (
            "Montos VES",
            {
                "fields": (
                    "subtotal_ves",
                    "total_iva_ves",
                    "total_igtf_ves",
                    "gran_total_ves",
                ),
            },
        ),
        ("Estado", {"fields": ("estado",)}),
    )


@admin.register(ItemFactura)
class ItemFacturaAdmin(SaaSAdminMixin, ModelAdmin):
    list_display = ("factura", "descripcion", "cantidad", "precio_unitario_usd", "total_linea_usd")
    search_fields = ("descripcion", "factura__numero_control")


@admin.register(Pago)
class PagoAdmin(SaaSAdminMixin, ModelAdmin):
    list_display = ("factura", "monto_usd", "monto_ves", "metodo_pago", "referencia", "fecha_pago")
    list_filter = ("metodo_pago", "fecha_pago")
    search_fields = ("referencia", "factura__numero_control")
