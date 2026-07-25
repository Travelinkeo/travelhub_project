"""
Admin de Boletos — apps/bookings/admin_boletos.py

Contiene: BoletoImportadoAdmin, BoletoImportadoTransitoAdmin, AuditLogAdmin,
          SegmentoVueloAdmin, FeeVentaAdmin, PagoVentaAdmin.
Importado por admin.py vía: from .admin_boletos import *  # noqa
"""

import logging

from django.contrib import admin, messages
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from unfold.decorators import action

from core.api import SaaSAdminMixin

from .models import (
    AuditLog,
    BoletoImportado,
    BoletoImportadoTransito,
    FeeVenta,
    PagoVenta,
    SegmentoVuelo,
)

logger = logging.getLogger(__name__)


@admin.register(BoletoImportado)
class BoletoImportadoAdmin:
    """Configuración de administración para boletoimportado. Uso: instanciar según necesidad del dominio.
    """
    list_display = (
        "id_boleto_importado",
        "archivo_boleto_link",
        "pdf_generado_link",
        "fecha_subida",
        "estado_parseo",
        "numero_boleto",
        "nombre_pasajero_procesado",
        "venta_asociada",
    )
    search_fields = ("archivo_boleto", "numero_boleto", "nombre_pasajero_completo")
    list_filter = ("estado_parseo", "formato_detectado", "fecha_subida")
    readonly_fields = (
        "fecha_subida",
        "formato_detectado",
        "datos_parseados",
        "estado_parseo",
        "log_parseo",
        "pdf_generado_link",
    )
    autocomplete_fields = ["venta_asociada"]
    actions = ["reprocesar_boletos", "hard_delete_boletos"]
    actions_list = ["subir_boleto_action"]

    @action(description="📤 Subir Boleto (IA)")
    def subir_boleto_action(self, request):
        # subir_boleto_action: Subir boleto action. Args: según implementación. Returns: según implementación.
        from django.http import HttpResponseRedirect
        from django.urls import reverse
        return HttpResponseRedirect(reverse("core:boletos_importar"))

    def get_queryset(self, request):
        # get_queryset: Obtiene/recupera queryset. Args: según implementación. Returns: dato solicitado.
        return super().get_queryset(request).select_related("venta_asociada")

    def changelist_view(self, request, extra_context=None):
        # changelist_view: Changelist view. Args: según implementación. Returns: según implementación.
        extra_context = extra_context or {}
        extra_context["show_upload_button"] = True
        return super().changelist_view(request, extra_context=extra_context)

    def has_add_permission(self, request):
        # has_add_permission: Has add permission. Args: según implementación. Returns: según implementación.
        return True

    def archivo_boleto_link(self, obj):
        # archivo_boleto_link: Archivo boleto link. Args: según implementación. Returns: según implementación.
        if obj.archivo_boleto:
            return format_html(
                "<a href='{url}'>{name}</a>",
                url=obj.archivo_boleto.url,
                name=obj.archivo_boleto.name.split("/")[-1],
            )
        return "-"

    def pdf_generado_link(self, obj):
        # pdf_generado_link: Pdf generado link. Args: según implementación. Returns: según implementación.
        url = obj.get_pdf_url()
        if url:
            return format_html('<a href="{}" target="_blank" class="button">📄 Ver PDF</a>', url)
        return "No generado"

    def save_model(self, request, obj, form, change):
        # save_model: Guarda/persiste  model. Args: datos a guardar. Returns: objeto guardado.
        super().save_model(request, obj, form, change)
        if not change:
            return
        try:
            data = (
                obj.datos_parseados.copy()
                if (obj.datos_parseados and isinstance(obj.datos_parseados, dict))
                else {}
            )
            data["_boleto_instance"] = obj
            data["nombre_pasajero"] = obj.nombre_pasajero_procesado
            data["passenger_name"] = obj.nombre_pasajero_procesado
            data["numero_boleto"] = obj.numero_boleto
            data["ticket_number"] = obj.numero_boleto
            data["pnr"] = obj.localizador_pnr
            data["codigo_reserva"] = obj.localizador_pnr
            data["fecha_emision"] = obj.fecha_emision_boleto
            data["aerolinea_emisora"] = obj.aerolinea_emisora
            data["foid"] = obj.foid_pasajero
            data["passenger_document"] = obj.foid_pasajero
            data["total_boleto"] = obj.total_boleto

            from django.utils.module_loading import import_string

            generate_ticket = import_string("apps.automation.parsers.ticket_parser.generate_ticket")
            pdf_bytes, filename = generate_ticket(data, agencia_obj=obj.agencia)

            if pdf_bytes:
                messages.success(
                    request,
                    f"✨ PDF regenerado exitosamente para el boleto {obj.numero_boleto or obj.pk}.",
                )
            else:
                messages.warning(
                    request,
                    "Se guardaron los cambios, pero falló la regeneración del PDF (verifique Gotenberg).",
                )
        except Exception as e:
            logger.error(
                f"Error regenerando PDF desde Admin para Boleto {obj.pk}: {e}", exc_info=True
            )
            messages.warning(
                request, f"Se actualizaron los datos, pero falló la regeneración del PDF: {e}"
            )

    @admin.action(description="🔥 ELIMINACIÓN FÍSICA (Irreversible)")
    def hard_delete_boletos(self, request, queryset):
        # hard_delete_boletos: Hard delete boletos. Args: según implementación. Returns: según implementación.
        if not request.user.is_superuser:
            self.message_user(
                request, "Solo superusuarios pueden realizar la eliminación física.", level="error"
            )
            return
        count = queryset.count()
        for obj in queryset:
            for field in ("archivo_boleto", "archivo_pdf_generado"):
                archivo = getattr(obj, field, None)
                if archivo:
                    try:
                        archivo.delete(save=False)
                    except Exception as e:
                        logger.warning(f"No se pudo eliminar {field} del boleto {obj.pk}: {e}")
            obj.hard_delete()
        self.message_user(request, f"Se han eliminado físicamente {count} boletos y sus archivos.")

    @admin.action(description="🔄 Reprocesar Boletos Seleccionados")
    def reprocesar_boletos(self, request, queryset):
        # reprocesar_boletos: Reprocesar boletos. Args: según implementación. Returns: según implementación.
        from django.utils.module_loading import import_string

        parsear_boleto_individual = import_string("core.tasks.parsear_boleto_individual")

        lanzados = 0
        for boleto in queryset:
            BoletoImportado.objects.filter(pk=boleto.pk).update(
                estado_parseo=BoletoImportado.EstadoParseo.PENDIENTE,
                log_parseo="Re-encolado desde Django Admin...",
            )
            parsear_boleto_individual.delay(boleto.pk, ignore_manual=True, bypass_cache=True)
            lanzados += 1
        self.message_user(
            request, f"Se han encolado {lanzados} boletos para su reprocesamiento en segundo plano."
        )


@admin.register(BoletoImportadoTransito)
class BoletoImportadoTransitoAdmin:
    """Configuración de administración para boletoimportadotransito. Uso: instanciar según necesidad del dominio.
    """
    list_display = (
        "id_transito",
        "boleto_origen",
        "ticket_index",
        "nombre_pasajero",
        "numero_boleto",
        "procesado",
        "fecha_creacion",
    )
    search_fields = ("nombre_pasajero", "numero_boleto")
    list_filter = ("procesado", "fecha_creacion")
    readonly_fields = ("fecha_creacion",)


@admin.register(AuditLog)
class AuditLogAdmin:
    """Configuración de administración para auditlog. Uso: instanciar según necesidad del dominio.
    """
    saas_agency_field = "venta__agencia"
    list_display = ("id_audit_log", "modelo", "object_id", "accion", "venta", "creado")
    list_filter = ("modelo", "accion", "creado")
    readonly_fields = (
        "modelo",
        "object_id",
        "accion",
        "venta",
        "descripcion",
        "datos_previos",
        "datos_nuevos",
        "metadata_extra",
        "creado",
    )
    ordering = ("-creado",)


@admin.register(SegmentoVuelo)
class SegmentoVueloAdmin:
    """Configuración de administración para segmentovuelo. Uso: instanciar según necesidad del dominio.
    """
    saas_agency_field = "venta__agencia"
    list_display = (
        "id_segmento_vuelo",
        "venta",
        "origen",
        "destino",
        "numero_vuelo",
        "fecha_salida",
    )
    autocomplete_fields = ["venta", "origen", "destino"]


@admin.register(FeeVenta)
class FeeVentaAdmin:
    """Configuración de administración para feeventa. Uso: instanciar según necesidad del dominio.
    """
    saas_agency_field = "venta__agencia"
    list_display = ("id_fee_venta", "venta", "tipo_fee", "monto", "moneda")
    autocomplete_fields = ["venta", "moneda"]


@admin.register(PagoVenta)
class PagoVentaAdmin:
    """Configuración de administración para pagoventa. Uso: instanciar según necesidad del dominio.
    """
    saas_agency_field = "venta__agencia"
    list_display = ("id_pago_venta", "venta", "metodo", "monto", "moneda", "fecha_pago")
    autocomplete_fields = ["venta", "moneda"]
