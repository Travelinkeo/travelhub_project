"""
apps/communications/admin.py
Consola de Diagnóstico del Mailbot - Admin UI para EmailMonitorLog.
Provee visibilidad total sobre el estado de la ingesta de correos por agencia.
"""

import logging

from django.contrib import admin, messages
from django.db.models import Avg, Count, Max
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from core.api import SaaSAdminMixin

from .models import EmailMonitorLog

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Filtros personalizados
# ---------------------------------------------------------------------------


class EstadoColorFilter(admin.SimpleListFilter):
    title = "Estado"
    parameter_name = "estado"

    def lookups(self, request, model_admin):
        return [
            (EmailMonitorLog.Estado.SUCCESS, "✅ Éxito"),
            (EmailMonitorLog.Estado.WARNING, "⚠️ Advertencia"),
            (EmailMonitorLog.Estado.ERROR, "❌ Error"),
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(estado=self.value())
        return queryset


class UltimasHorasFilter(admin.SimpleListFilter):
    title = "Período"
    parameter_name = "periodo"

    def lookups(self, request, model_admin):
        return [
            ("1h", "Última hora"),
            ("6h", "Últimas 6 horas"),
            ("24h", "Últimas 24 horas"),
            ("7d", "Últimos 7 días"),
            ("30d", "Últimos 30 días"),
        ]

    def queryset(self, request, queryset):
        ahora = timezone.now()
        deltas = {
            "1h": timezone.timedelta(hours=1),
            "6h": timezone.timedelta(hours=6),
            "24h": timezone.timedelta(hours=24),
            "7d": timezone.timedelta(days=7),
            "30d": timezone.timedelta(days=30),
        }
        if self.value() in deltas:
            return queryset.filter(fecha_ejecucion__gte=ahora - deltas[self.value()])
        return queryset


# ---------------------------------------------------------------------------
# Acciones
# ---------------------------------------------------------------------------


@admin.action(description="🗑️ Purgar logs seleccionados (> 30 días)")
def purgar_logs_antiguos(modeladmin, request, queryset):
    hace_30_dias = timezone.now() - timezone.timedelta(days=30)
    antiguos = queryset.filter(fecha_ejecucion__lt=hace_30_dias)
    count = antiguos.count()
    antiguos.delete()
    messages.success(request, f"Se eliminaron {count} log(s) con más de 30 días.")


@admin.action(description="🔄 Forzar re-escaneo de correos (agencias seleccionadas)")
def forzar_rescaneo(modeladmin, request, queryset):
    """Dispara una tarea Celery inmediata de monitoreo por cada agencia distinta en la selección."""
    from core.api import procesar_correo_individual_agencia

    agencias = queryset.values_list("agencia_id", flat=True).distinct()
    count = 0
    for agencia_id in agencias:
        if agencia_id:
            try:
                procesar_correo_individual_agencia.delay(agencia_id)
                count += 1
            except Exception as e:
                messages.error(
                    request, f"No se pudo despachar tarea para agencia {agencia_id}: {e}"
                )

    if count:
        messages.success(
            request, f"✅ Se despacharon {count} tarea(s) de re-escaneo en segundo plano."
        )


# ---------------------------------------------------------------------------
# Admin principal
# ---------------------------------------------------------------------------


@admin.register(EmailMonitorLog)
class EmailMonitorLogAdmin(SaaSAdminMixin, admin.ModelAdmin):
    """
    Consola de Diagnóstico del Mailbot.
    Proporciona visibilidad completa sobre el historial de ejecuciones del monitor
    de correos por agencia, permitiendo identificar fallos y tendencias.
    """

    list_display = [
        "badge_estado",
        "fecha_ejecucion",
        "agencia",
        "correos_procesados",
        "tiempo_ejecucion_display",
        "host_conectado",
        "mensaje_truncado",
    ]
    list_display_links = ["badge_estado", "fecha_ejecucion"]
    list_filter = [EstadoColorFilter, UltimasHorasFilter, "agencia"]
    search_fields = ["mensaje", "host_conectado", "agencia__nombre"]
    readonly_fields = [
        "fecha_ejecucion",
        "estado",
        "agencia",
        "mensaje",
        "host_conectado",
        "correos_procesados",
        "tiempo_ejecucion",
        "panel_salud_agencia",
    ]
    ordering = ["-fecha_ejecucion"]
    date_hierarchy = "fecha_ejecucion"
    actions = [purgar_logs_antiguos, forzar_rescaneo]

    # Sin permiso de agregar ni editar (sólo lectura + acciones)
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False  # No se editan logs, sólo se consultan

    # -----------------------------------------------------------------------
    # Columnas personalizadas
    # -----------------------------------------------------------------------

    @admin.display(description="Estado", ordering="estado")
    def badge_estado(self, obj):
        colores = {
            EmailMonitorLog.Estado.SUCCESS: ("#1a7f37", "✅"),
            EmailMonitorLog.Estado.WARNING: ("#9a6700", "⚠️"),
            EmailMonitorLog.Estado.ERROR: ("#cf222e", "❌"),
        }
        color, icon = colores.get(obj.estado, ("#586069", "❓"))
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:12px;'
            'font-size:0.8em;font-weight:bold;">{} {}</span>',
            color,
            icon,
            obj.get_estado_display(),
        )

    @admin.display(description="Duración", ordering="tiempo_ejecucion")
    def tiempo_ejecucion_display(self, obj):
        if obj.tiempo_ejecucion is None:
            return "—"
        seg = obj.tiempo_ejecucion
        if seg < 60:
            return format_html('<span style="font-family:monospace">{:.2f}s</span>', seg)
        mins = int(seg // 60)
        segs = seg % 60
        return format_html(
            '<span style="font-family:monospace;color:#d97706">{:d}m {:.1f}s</span>', mins, segs
        )

    @admin.display(description="Mensaje")
    def mensaje_truncado(self, obj):
        texto = obj.mensaje or ""
        if len(texto) <= 120:
            return texto
        return format_html('<span title="{}">{}&hellip;</span>', texto, texto[:120])

    # -----------------------------------------------------------------------
    # Panel de salud por agencia (visible en el detalle)
    # -----------------------------------------------------------------------

    @admin.display(description="📊 Resumen de Salud de la Agencia (últimas 24h)")
    def panel_salud_agencia(self, obj):
        if not obj.agencia:
            return "Sin agencia"

        hace_24h = timezone.now() - timezone.timedelta(hours=24)
        qs = EmailMonitorLog.objects.filter(agencia=obj.agencia, fecha_ejecucion__gte=hace_24h)

        total = qs.count()
        exitosos = qs.filter(estado=EmailMonitorLog.Estado.SUCCESS).count()
        errores = qs.filter(estado=EmailMonitorLog.Estado.ERROR).count()
        warnings = qs.filter(estado=EmailMonitorLog.Estado.WARNING).count()
        avg_dur = qs.aggregate(avg=Avg("tiempo_ejecucion"))["avg"] or 0
        max_dur = qs.aggregate(mx=Max("tiempo_ejecucion"))["mx"] or 0
        qs.aggregate(tp=Count("correos_procesados"))["tp"] or 0
        ultimo = qs.order_by("-fecha_ejecucion").first()

        tasa_exito = (exitosos / total * 100) if total else 0
        color_tasa = (
            "#1a7f37" if tasa_exito >= 80 else ("#9a6700" if tasa_exito >= 50 else "#cf222e")
        )

        ultimo_str = ultimo.fecha_ejecucion.strftime("%d/%m/%Y %H:%M:%S") if ultimo else "—"

        html = f"""
        <table style="border-collapse:collapse;width:100%;font-size:0.9em">
            <tr style="background:#f6f8fa">
                <th style="padding:6px 12px;text-align:left;border:1px solid #d0d7de">Métrica</th>
                <th style="padding:6px 12px;text-align:right;border:1px solid #d0d7de">Valor</th>
            </tr>
            <tr>
                <td style="padding:6px 12px;border:1px solid #d0d7de">Total de ejecuciones (24h)</td>
                <td style="padding:6px 12px;text-align:right;font-weight:bold;border:1px solid #d0d7de">{total}</td>
            </tr>
            <tr style="background:#f6f8fa">
                <td style="padding:6px 12px;border:1px solid #d0d7de">Tasa de éxito</td>
                <td style="padding:6px 12px;text-align:right;font-weight:bold;color:{color_tasa};border:1px solid #d0d7de">{tasa_exito:.1f}%</td>
            </tr>
            <tr>
                <td style="padding:6px 12px;border:1px solid #d0d7de">✅ Exitosos / ⚠️ Advertencias / ❌ Errores</td>
                <td style="padding:6px 12px;text-align:right;border:1px solid #d0d7de">
                    <span style="color:#1a7f37;font-weight:bold">{exitosos}</span> /
                    <span style="color:#9a6700;font-weight:bold">{warnings}</span> /
                    <span style="color:#cf222e;font-weight:bold">{errores}</span>
                </td>
            </tr>
            <tr style="background:#f6f8fa">
                <td style="padding:6px 12px;border:1px solid #d0d7de">Duración promedio</td>
                <td style="padding:6px 12px;text-align:right;font-family:monospace;border:1px solid #d0d7de">{avg_dur:.2f}s</td>
            </tr>
            <tr>
                <td style="padding:6px 12px;border:1px solid #d0d7de">Duración máxima</td>
                <td style="padding:6px 12px;text-align:right;font-family:monospace;border:1px solid #d0d7de">{max_dur:.2f}s</td>
            </tr>
            <tr style="background:#f6f8fa">
                <td style="padding:6px 12px;border:1px solid #d0d7de">Última ejecución</td>
                <td style="padding:6px 12px;text-align:right;border:1px solid #d0d7de">{ultimo_str}</td>
            </tr>
        </table>
        """
        return mark_safe(html)  # noqa: S308

    # -----------------------------------------------------------------------
    # Fieldsets del detalle
    # -----------------------------------------------------------------------

    fieldsets = (
        (
            "📋 Detalle de la Ejecución",
            {
                "fields": (
                    "fecha_ejecucion",
                    "agencia",
                    "estado",
                    "host_conectado",
                    "correos_procesados",
                    "tiempo_ejecucion",
                    "mensaje",
                )
            },
        ),
        (
            "📊 Resumen de Salud de la Agencia",
            {
                "fields": ("panel_salud_agencia",),
                "classes": ("collapse",),
            },
        ),
    )

    # -----------------------------------------------------------------------
    # Encabezado de la consola en la cabecera de la lista
    # -----------------------------------------------------------------------

    def changelist_view(self, request, extra_context=None):
        """Inyecta métricas globales en el encabezado de la consola."""
        extra_context = extra_context or {}

        hace_24h = timezone.now() - timezone.timedelta(hours=24)
        qs_24h = EmailMonitorLog.objects.filter(fecha_ejecucion__gte=hace_24h)

        if request.user.is_superuser:
            qs_base = qs_24h
        elif hasattr(request, "agencia") and request.agencia:
            qs_base = qs_24h.filter(agencia=request.agencia)
        else:
            qs_base = EmailMonitorLog.objects.none()

        extra_context["mailbot_stats"] = {
            "total_24h": qs_base.count(),
            "errores_24h": qs_base.filter(estado=EmailMonitorLog.Estado.ERROR).count(),
            "warnings_24h": qs_base.filter(estado=EmailMonitorLog.Estado.WARNING).count(),
            "procesados_24h": sum(qs_base.values_list("correos_procesados", flat=True)),
        }

        return super().changelist_view(request, extra_context=extra_context)
