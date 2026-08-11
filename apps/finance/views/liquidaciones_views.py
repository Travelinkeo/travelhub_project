import logging

from django.views.generic import TemplateView

from core.api import SaaSAdminMixin

logger = logging.getLogger(__name__)


class LiquidacionDashboardView(SaaSAdminMixin, TemplateView):
    template_name = "finance/liquidaciones/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from django.db.models import Sum

        from apps.bookings.models import ItemVenta
        from apps.finance.models_stubs import ReporteReconciliacion

        agencia = getattr(self.request.user, "agencia_activa", None)
        qs_items = ItemVenta.objects.exclude(costo_neto_proveedor__isnull=True)
        if agencia:
            qs_items = qs_items.filter(venta__agencia=agencia)

        total_pendiente = qs_items.aggregate(tot=Sum("costo_neto_proveedor"))["tot"] or 0

        qs_reportes = ReporteReconciliacion.objects.all()
        if agencia:
            qs_reportes = qs_reportes.filter(agencia=agencia)

        context["total_pendiente"] = total_pendiente
        context["total_liquidado"] = 0
        context["liquidaciones"] = qs_reportes.order_by("-fecha_subida")[:20]
        context["title"] = "Liquidaciones a Proveedores"
        return context
