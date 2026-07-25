import logging

from django.contrib import admin
from django.utils.html import format_html

from core.models import APISecret

logger = logging.getLogger(__name__)


def _test_api_secret(obj: APISecret) -> tuple[bool, str]:
    """Prueba la conexión real contra el servicio externo."""
    from core.services.api_testers import test_api_secret as real_test

    if not obj.value:
        return False, "Valor vacío"

    return real_test(obj.service, obj.value)


@admin.register(APISecret)
class APISecretAdmin(admin.ModelAdmin):
    """Admin para gestionar claves secretas de servicios externos."""
    list_display = [
        "service_colored",
        "category_badge",
        "value_masked",
        "is_active",
        "test_badge",
        "last_tested",
        "updated_at",
    ]
    list_filter = ["category", "is_active", "test_status"]
    search_fields = ["service", "description"]
    list_editable = ["is_active"]
    readonly_fields = ["last_tested", "test_status", "created_at", "updated_at"]
    ordering = ["category", "service"]

    fieldsets = (
        (None, {"fields": ("service", "category", "description")}),
        ("Valor", {"fields": ("value",), "classes": ("wide",)}),
        (
            "Estado",
            {
                "fields": ("is_active", "test_status", "last_tested"),
                "classes": ("collapse",),
            },
        ),
        ("Auditoría", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    actions = ["test_selected", "mark_active", "mark_inactive"]

    def get_queryset(self, request):
        """Método que obtiene queryset. Args: según implementación. Returns: datos solicitados."""
        return (
            super()
            .get_queryset(request)
            .only(
                "service",
                "category",
                "value",
                "is_active",
                "test_status",
                "last_tested",
                "updated_at",
            )
        )

    @admin.display(description="Servicio")
    def service_colored(self, obj):
        """Método: service colored."""
        colors = {
            "ai": "#8B5CF6",
            "payment": "#10B981",
            "email": "#3B82F6",
            "storage": "#F59E0B",
            "maps": "#EF4444",
            "messaging": "#06B6D4",
            "whatsapp": "#25D366",
            "gds": "#6366F1",
            "social": "#EC4899",
            "infra": "#6B7280",
            "monitoring": "#14B8A6",
            "security": "#DC2626",
        }
        color = colors.get(obj.category, "#6B7280")
        return format_html('<span style="color: {};">{}</span>', color, obj.service)

    @admin.display(description="Categoría")
    def category_badge(self, obj):
        """Método: category badge."""
        colors = {
            "ai": "bg-purple-100 text-purple-800",
            "payment": "bg-green-100 text-green-800",
            "email": "bg-blue-100 text-blue-800",
            "storage": "bg-yellow-100 text-yellow-800",
            "maps": "bg-red-100 text-red-800",
            "messaging": "bg-cyan-100 text-cyan-800",
            "whatsapp": "bg-emerald-100 text-emerald-800",
            "gds": "bg-indigo-100 text-indigo-800",
            "social": "bg-pink-100 text-pink-800",
            "infra": "bg-gray-100 text-gray-800",
            "monitoring": "bg-teal-100 text-teal-800",
            "security": "bg-red-100 text-red-800",
        }
        cls = colors.get(obj.category, "bg-gray-100 text-gray-800")
        return format_html(
            '<span style="background:{};color:{};padding:2px 8px;border-radius:4px;font-size:11px;">{}</span>',
            cls.split()[0]
            .replace("bg-", "#")
            .replace("purple-100", "#EDE9FE")
            .replace("green-100", "#D1FAE5")
            .replace("blue-100", "#DBEAFE")
            .replace("yellow-100", "#FEF3C7")
            .replace("red-100", "#FEE2E2")
            .replace("cyan-100", "#CFFAFE")
            .replace("emerald-100", "#D1FAE5")
            .replace("indigo-100", "#E0E7FF")
            .replace("pink-100", "#FCE7F3")
            .replace("gray-100", "#F3F4F6")
            .replace("teal-100", "#CCFBF1"),
            cls.split()[1]
            .replace("text-purple-800", "#6B21A8")
            .replace("text-green-800", "#065F46")
            .replace("text-blue-800", "#1E40AF")
            .replace("text-yellow-800", "#92400E")
            .replace("text-red-800", "#991B1B")
            .replace("text-cyan-800", "#155E75")
            .replace("text-emerald-800", "#065F46")
            .replace("text-indigo-800", "#3730A3")
            .replace("text-pink-800", "#9D174D")
            .replace("text-gray-800", "#1F2937")
            .replace("text-teal-800", "#115E59"),
            obj.get_category_display(),
        )

    @admin.display(description="Valor")
    def value_masked(self, obj):
        """Método: value masked."""
        raw = obj.value or ""
        if not raw:
            return format_html('<span style="color:#9CA3AF;">—</span>')
        visible = raw[:6]
        masked = visible + "••••" + raw[-4:] if len(raw) > 12 else visible + "••••"
        return format_html(
            '<span style="font-family:monospace;cursor:pointer;" '
            "onclick=\"this.innerHTML=this.innerHTML.includes('••••')?'{}':'{}'\">"
            "{}</span>",
            raw,
            masked,
            masked,
        )

    @admin.display(description="Estado")
    def test_badge(self, obj):
        """Método: test badge."""
        icons = {"unknown": "◯", "ok": "✓", "fail": "✗"}
        colors = {"unknown": "#9CA3AF", "ok": "#10B981", "fail": "#EF4444"}
        color = colors.get(obj.test_status, "#9CA3AF")
        icon = icons.get(obj.test_status, "?")
        return format_html(
            '<span style="color:{};font-weight:bold;">{} {}</span>',
            color,
            icon,
            obj.get_test_status_display()
            if hasattr(obj, "get_test_status_display")
            else obj.test_status.title(),
        )

    @admin.action(description="Probar conexión de las claves seleccionadas")
    def test_selected(self, request, queryset):
        """Método: test selected."""
        from django.utils import timezone

        ok = 0
        fail = 0
        for obj in queryset:
            success, msg = _test_api_secret(obj)
            obj.last_tested = timezone.now()
            obj.test_status = "ok" if success else "fail"
            obj.save(update_fields=["last_tested", "test_status"])
            if success:
                ok += 1
            else:
                fail += 1
                self.message_user(request, f"{obj.service}: {msg}", level="error")

        if ok:
            self.message_user(request, f"{ok} clave(s) verificada(s) correctamente.")
        if fail:
            self.message_user(request, f"{fail} clave(s) con problemas.")

    @admin.action(description="Marcar como activas")
    def mark_active(self, request, queryset):
        """Método: mark active."""
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} clave(s) activada(s).")

    @admin.action(description="Marcar como inactivas")
    def mark_inactive(self, request, queryset):
        """Método: mark inactive."""
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} clave(s) desactivada(s).")

    def save_model(self, request, obj, form, change):
        """Método que actualiza/guarda model."""
        super().save_model(request, obj, form, change)

    class Media:
        """Función: Media."""
        css = {"all": ("admin/css/api_secret.css",)}
