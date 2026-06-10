import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import ListView, TemplateView, View
from django.views.generic.edit import CreateView

from apps.bookings.models import AuditLog, BoletoImportado
from apps.common.services.analytics_service import AnalyticsService
from apps.communications.models import ComunicacionProveedor
from apps.contabilidad.models import LiquidacionProveedor
from apps.crm.models import PasaporteEscaneado
from core.mixins import SaaSMixin
from core.security import get_agencia_from_request

from ..forms import BoletoManualForm


class LiquidacionesListView(SaaSMixin, LoginRequiredMixin, ListView):
    model = LiquidacionProveedor
    template_name = "core/erp/liquidaciones.html"
    context_object_name = "liquidaciones"
    paginate_by = 20

    def get_queryset(self):
        queryset = (
            super().get_queryset().select_related("proveedor", "venta").order_by("-fecha_emision")
        )

        # Filters
        estado = self.request.GET.get("estado")
        search = self.request.GET.get("search")

        if estado:
            queryset = queryset.filter(estado=estado)

        if search:
            queryset = queryset.filter(
                proveedor__nombre_comercial__icontains=search
            ) | queryset.filter(venta__localizador__icontains=search)

        return queryset


class PasaportesListView(SaaSMixin, LoginRequiredMixin, ListView):
    model = PasaporteEscaneado
    template_name = "core/erp/pasaportes.html"
    context_object_name = "pasaportes"
    paginate_by = 12

    def get_queryset(self):
        queryset = super().get_queryset().select_related("cliente").order_by("-fecha_procesamiento")

        # Filters
        estado = self.request.GET.get("estado")
        search = self.request.GET.get("search")

        if estado == "pendientes":
            queryset = queryset.filter(cliente__isnull=True)
        elif estado == "baja_confianza":
            queryset = queryset.filter(confianza_ocr="LOW")

        if search:
            queryset = queryset.filter(
                Q(nombres__icontains=search)
                | Q(apellidos__icontains=search)
                | Q(numero_pasaporte__icontains=search)
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["active_tab"] = "pasaportes"
        context["today"] = timezone.now().date()
        return context


class AuditoriaListView(SaaSMixin, LoginRequiredMixin, ListView):
    model = AuditLog
    template_name = "core/erp/auditoria.html"
    context_object_name = "logs"
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset().select_related("venta").order_by("-creado")

        # Filters
        accion = self.request.GET.get("accion")
        modelo = self.request.GET.get("modelo")
        search = self.request.GET.get("search")
        venta_id = self.request.GET.get("venta_id")

        if accion:
            queryset = queryset.filter(accion=accion)

        if modelo:
            queryset = queryset.filter(modelo=modelo)

        if venta_id:
            queryset = queryset.filter(venta_id=venta_id)

        if search:
            queryset = queryset.filter(
                Q(object_id__icontains=search)
                | Q(descripcion__icontains=search)
                | Q(modelo__icontains=search)
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["active_tab"] = "auditoria"

        # Statistics
        context["total_registros"] = AuditLog.objects.count()
        context["acciones_stats"] = (
            AuditLog.objects.values("accion")
            .annotate(total=Count("id_audit_log"))
            .order_by("-total")
        )
        context["modelos_stats"] = (
            AuditLog.objects.values("modelo")
            .annotate(total=Count("id_audit_log"))
            .order_by("-total")[:5]
        )

        return context


class ComunicacionesListView(SaaSMixin, LoginRequiredMixin, ListView):
    model = ComunicacionProveedor
    template_name = "core/erp/comunicaciones.html"
    context_object_name = "comunicaciones"
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset().order_by("-fecha_recepcion")

        search = self.request.GET.get("search")
        categoria = self.request.GET.get("categoria")

        if search:
            queryset = queryset.filter(
                Q(asunto__icontains=search)
                | Q(remitente__icontains=search)
                | Q(cuerpo_completo__icontains=search)
            )

        if categoria:
            queryset = queryset.filter(categoria=categoria)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["active_tab"] = "comunicaciones"

        # Category Stats
        context["categorias_stats"] = (
            ComunicacionProveedor.objects.values("categoria")
            .annotate(total=Count("id"))
            .order_by("-total")
        )

        return context


class DashboardBoletosView(LoginRequiredMixin, TemplateView):
    template_name = "core/erp/dashboard_boletos.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["active_tab"] = "boletos_dashboard"
        return context


class BoletosBusquedaView(SaaSMixin, LoginRequiredMixin, TemplateView):
    template_name = "core/erp/boletos_busqueda.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["active_tab"] = "boletos_busqueda"
        return context


class BoletosReportesView(SaaSMixin, LoginRequiredMixin, TemplateView):
    template_name = "core/erp/boletos_reportes.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["active_tab"] = "boletos_reportes"

        agencia = get_agencia_from_request(self.request)
        fecha_inicio = self.request.GET.get("fecha_inicio")
        fecha_fin = self.request.GET.get("fecha_fin")
        aerolinea = self.request.GET.get("aerolinea")

        # Obtener aerolíneas para el filtro
        context["aerolineas_disponibles"] = AnalyticsService.get_aerolineas_disponibles(agencia)

        # Obtener reporte usando el servicio centralizado
        reporte = AnalyticsService.get_reporte_comisiones_boletos(
            agencia=agencia, fecha_inicio=fecha_inicio, fecha_fin=fecha_fin, aerolinea=aerolinea
        )

        context.update(
            {
                "total_boletos": reporte["totales"]["total_boletos"],
                "total_ventas": reporte["totales"]["total_ventas"],
                "total_comisiones": reporte["totales"]["total_comisiones"],
                "total_neto": reporte["totales"]["total_neto"],
                "total_pendiente": reporte["totales"]["total_pendiente"],
                "boletos": reporte["boletos"],
                "por_aerolinea": reporte["por_aerolinea"],
                "filtro_aerolinea": aerolinea,
                "stats_graficas": json.dumps(
                    AnalyticsService.get_stats_graficas_boletos(
                        agencia=agencia, fecha_inicio=fecha_inicio, fecha_fin=fecha_fin
                    )
                ),
            }
        )

        return context


class BoletosAnulacionesView(SaaSMixin, LoginRequiredMixin, TemplateView):
    template_name = "core/erp/boletos_anulaciones.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["active_tab"] = "boletos_anulaciones"
        return context


class BoletosImportarView(SaaSMixin, LoginRequiredMixin, TemplateView):
    template_name = "core/erp/boletos_importar.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["active_tab"] = "boletos_importar"

        # Fetch recent imported tickets
        qs = BoletoImportado.objects.all()
        if not self.request.user.is_superuser and hasattr(self.request.user, "agencias"):
            ua = self.request.user.agencias.filter(activo=True).first()
            if ua:
                qs = qs.filter(agencia=ua.agencia)

        context["boletos"] = qs.order_by("-fecha_subida")[:20]  # Show last 20

        # Add Active Consolidators
        from apps.bookings.models import Proveedor
        from apps.bookings.models.tarifario import TarifarioProveedor

        proveedores = Proveedor.objects.filter(
            tipo_proveedor=Proveedor.TipoProveedorChoices.CONSOLIDADOR, activo=True
        ).order_by("nombre")

        # Optimized: Fetch latest active tariffarios in a single query using prefetch_related or dict mapping
        # Since we only need the latest one per provider, we can do a subquery or just prefetch and pick first
        # Using a dict lookup for O(1) access
        latest_tarifarios = {}
        for t in TarifarioProveedor.objects.filter(proveedor__in=proveedores, activo=True).order_by(
            "proveedor_id", "-fecha_carga"
        ):
            if t.proveedor_id not in latest_tarifarios:
                latest_tarifarios[t.proveedor_id] = t

        for p in proveedores:
            t = latest_tarifarios.get(p.pk)
            p.comision_display = t.comision_estandar if t else 0

        context["proveedores"] = proveedores
        return context


class BoletosManualView(SaaSMixin, LoginRequiredMixin, CreateView):
    model = BoletoImportado
    form_class = BoletoManualForm
    template_name = "core/erp/boletos_manual.html"
    success_url = reverse_lazy("core:boletos_dashboard")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["active_tab"] = "boletos_manual"
        return context


class ExportarBoletosExcelView(SaaSMixin, LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        agencia = get_agencia_from_request(request)
        fecha_inicio = request.GET.get("fecha_inicio")
        fecha_fin = request.GET.get("fecha_fin")
        aerolinea = request.GET.get("aerolinea")

        excel_file = AnalyticsService.exportar_reporte_boletos_excel(
            agencia=agencia, fecha_inicio=fecha_inicio, fecha_fin=fecha_fin, aerolinea=aerolinea
        )

        filename = f"reporte_boletos_{timezone.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        response = HttpResponse(
            excel_file.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
