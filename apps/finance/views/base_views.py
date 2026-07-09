import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import DetailView, ListView, TemplateView, View

from apps.common.mixins.export_mixin import ExportMixin
from apps.finance.models import Factura
from apps.finance.models.reconciliacion import (
    ConciliacionBoleto,
    ReporteReconciliacion,
)
from apps.finance.services.analytics_service import FinancialAnalyticsService
from apps.finance.services.smart_reconciliation_service import SmartReconciliationService
from core.api import AuditLog, SaaSMixin

logger = logging.getLogger(__name__)


class InvoiceListView(ExportMixin, SaaSMixin, LoginRequiredMixin, ListView):
    model = Factura
    template_name = "finance/invoice_list.html"
    context_object_name = "invoices"
    paginate_by = 20
    export_fields = [
        "numero_factura",
        "cliente_nombre",
        "cliente_rif",
        "fecha_emision",
        "tipo_factura",
        "monto_total",
        "saldo_pendiente",
        "estado",
    ]
    export_filename = "facturas"

    def get_queryset(self):
        qs = super().get_queryset()
        estado = self.request.GET.get("estado")
        if estado:
            qs = qs.filter(estado=estado)
        return qs.select_related("cliente", "agencia").order_by("-fecha_emision", "-id_factura")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filtros"] = {"estado": self.request.GET.get("estado", "")}
        return context


class InvoiceDetailView(SaaSMixin, LoginRequiredMixin, DetailView):
    model = Factura
    template_name = "finance/partials/invoice_detail_modal.html"
    context_object_name = "invoice"
    pk_url_kwarg = "pk"

    def get(self, request, *args, **kwargs):
        # Si es una petición HTMX, devolvemos el partial
        if request.headers.get("HX-Request"):
            return super().get(request, *args, **kwargs)
        # Si no, redirigimos al listado (o podríamos tener una página dedicada)
        return redirect("finance:invoice_list")


class InvoiceIssueView(SaaSMixin, LoginRequiredMixin, View):
    """
    Cambia el estado de la factura de BORRADOR a EMITIDA.
    """

    model = Factura

    def post(self, request, pk):
        factura = self.get_object()
        if factura.estado == Factura.EstadoFactura.BORRADOR:
            factura.estado = Factura.EstadoFactura.EMITIDA
            # Aquí se podría disparar la generación real del PDF fiscal o el envío a un PAC
            factura.save()

            # --- AGREGAR ASIENTO CONTABLE ---
            try:
                from django.utils.module_loading import import_string

                contabilidad_service = import_string(
                    "apps.contabilidad.services.ContabilidadService"
                )
                contabilidad_service.generar_asiento_desde_factura(factura)
            except Exception as e:
                logger.error(f"Error generando asiento contable para factura {factura.pk}: {e}")
                # Opcional: Podrías revertir la emisión si la contabilidad es crítica
                # factura.estado = Factura.EstadoFactura.BORRADOR
                # factura.save()
                # return HttpResponse(f"Error en contabilidad: {e}", status=500)

            if request.headers.get("HX-Request"):
                # Devolvemos una fila actualizada o un snippet de éxito
                return render(request, "finance/partials/invoice_row.html", {"invoice": factura})

            return redirect("finance:invoice_list")

        return HttpResponse("Solo se pueden emitir facturas en borrador.", status=400)


class InvoiceUpdateView(SaaSMixin, LoginRequiredMixin, View):
    """
    Permite actualizaciones rápidas de campos no críticos en el borrador.
    """

    model = Factura

    def post(self, request, pk):
        factura = self.get_object()
        if factura.estado == Factura.EstadoFactura.BORRADOR:
            # Ejemplo: actualizar notas
            notas = request.POST.get("notas")
            if notas is not None:
                factura.notas = notas
                factura.save()

            return HttpResponse("Factura actualizada", status=200)
        return HttpResponse("No se puede editar una factura emitida.", status=400)


# --- RECONCILIACIÓN ---


class ReportListView(SaaSMixin, LoginRequiredMixin, ListView):
    model = ReporteReconciliacion
    template_name = "finance/reconciliation/report_list.html"
    context_object_name = "reports"
    ordering = ["-fecha_subida"]

    def get_queryset(self):
        return super().get_queryset().select_related("agencia")


class ReportUploadView(LoginRequiredMixin, View):
    def post(self, request):
        proveedor = request.POST.get("proveedor", "Desconocido")
        archivo = request.FILES.get("archivo")

        if not archivo:
            return HttpResponse("Faltan campos obligatorios", status=400)

        reporte = ReporteReconciliacion.objects.create(
            agencia=request.agencia, archivo=archivo, proveedor=proveedor, estado="PENDIENTE"
        )

        try:
            SmartReconciliationService.procesar_reporte(str(reporte.id_reporte))
            return redirect("finance:report_detail", pk=reporte.pk)
        except Exception as e:
            logger.error(f"Error procesando reporte: {e}")
            return HttpResponse(f"Error procesando: {str(e)}", status=500)


class ReconciliationDetailView(SaaSMixin, LoginRequiredMixin, DetailView):
    model = ReporteReconciliacion
    template_name = "finance/reconciliation/report_detail.html"
    context_object_name = "report"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["lineas"] = self.object.lineas.all().order_by("numero_boleto_reportado")
        context["conciliaciones"] = (
            self.object.conciliaciones.all().select_related("boleto_local").order_by("estado")
        )
        return context


class ResolveDiscrepancyAIView(LoginRequiredMixin, View):
    """
    Endpoint HTMX para obtener sugerencia de la IA.
    """

    def get(self, request, pk):
        conciliacion = get_object_or_404(ConciliacionBoleto, pk=pk)

        suggestion = conciliacion.ia_razonamiento or "Sin sugerencia de IA disponible."

        return render(
            request,
            "finance/reconciliation/partials/ai_suggestion.html",
            {"suggestion": suggestion, "diff": conciliacion},
        )


class ProfitabilityDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "finance/profitability_dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["metrics"] = FinancialAnalyticsService.get_real_time_metrics()
        context["monthly_stats"] = FinancialAnalyticsService.get_monthly_profitability()
        context["category_stats"] = FinancialAnalyticsService.get_profit_by_category()
        return context


class ProfitSeriesDataView(LoginRequiredMixin, View):
    def get(self, request):
        data = FinancialAnalyticsService.get_monthly_profitability()
        return JsonResponse(data, safe=False)


class BIDashboardView(SaaSMixin, LoginRequiredMixin, TemplateView):
    template_name = "finance/dashboard_bi.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from decimal import Decimal

        from django.db.models import Avg, Sum
        from django.db.models.functions import TruncMonth

        from apps.bookings.models.pagos import PagoVenta
        from apps.bookings.models.venta import Venta
        from core.api import get_user_active_agency

        user = self.request.user
        agencia = get_user_active_agency(user)

        if not agencia:
            context["ventas"] = Venta.objects.none()
            context["metrics"] = {
                "total_neto_proveedor": Decimal("0.00"),
                "total_venta_cliente": Decimal("0.00"),
                "comision_promedio": Decimal("0.00"),
                "markup_bruto_total": Decimal("0.00"),
                "retenciones_igtf_total": Decimal("0.00"),
                "utilidad_neta_total": Decimal("0.00"),
            }
            context["monthly_chart_data"] = []
            context["filters"] = {"fecha_inicio": "", "fecha_fin": "", "pnr": ""}
            return context

        # Base querysets
        ventas_qs = (
            Venta.objects.select_related("agencia", "cliente")
            .filter(agencia=agencia)
            .exclude(estado=Venta.EstadoVenta.CANCELADA)
        )

        # Apply filters
        fecha_inicio = self.request.GET.get("fecha_inicio")
        fecha_fin = self.request.GET.get("fecha_fin")
        pnr = self.request.GET.get("pnr")

        if fecha_inicio:
            ventas_qs = ventas_qs.filter(fecha_venta__date__gte=fecha_inicio)
        if fecha_fin:
            ventas_qs = ventas_qs.filter(fecha_venta__date__lte=fecha_fin)
        if pnr:
            ventas_qs = ventas_qs.filter(localizador__icontains=pnr)

        # Aggregate metrics
        aggregates = ventas_qs.aggregate(
            total_neto=Sum("monto_neto_proveedor"),
            total_venta=Sum("monto_venta_cliente"),
            comision_promedio=Avg("porcentaje_comision_agente"),
        )

        total_neto = aggregates["total_neto"] or Decimal("0.00")
        total_venta = aggregates["total_venta"] or Decimal("0.00")
        comision_promedio = aggregates["comision_promedio"] or Decimal("0.00")
        markup_bruto_total = total_venta - total_neto

        # Cash payments for the filtered sales to estimate IGTF
        pagos_cash_total = PagoVenta.objects.filter(
            venta__in=ventas_qs, metodo="EFE", confirmado=True
        ).aggregate(s=Sum("monto"))["s"] or Decimal("0.00")

        retenciones_igtf_total = pagos_cash_total * Decimal("0.03")
        utilidad_neta_total = markup_bruto_total - retenciones_igtf_total

        context["metrics"] = {
            "total_neto_proveedor": total_neto,
            "total_venta_cliente": total_venta,
            "comision_promedio": comision_promedio,
            "markup_bruto_total": markup_bruto_total,
            "retenciones_igtf_total": retenciones_igtf_total,
            "utilidad_neta_total": utilidad_neta_total,
        }

        # Monthly breakdown for Chart.js
        monthly_stats = (
            ventas_qs.annotate(month=TruncMonth("fecha_venta"))
            .values("month")
            .annotate(
                neto=Sum("monto_neto_proveedor"),
                venta=Sum("monto_venta_cliente"),
            )
            .order_by("month")
        )

        monthly_chart_data = []
        for s in monthly_stats:
            month_date = s["month"]
            if not month_date:
                continue
            month_str = month_date.strftime("%b %Y")
            m_neto = s["neto"] or Decimal("0.00")
            m_venta = s["venta"] or Decimal("0.00")
            m_markup = m_venta - m_neto

            m_pagos_cash = PagoVenta.objects.filter(
                venta__in=ventas_qs.filter(
                    fecha_venta__month=month_date.month, fecha_venta__year=month_date.year
                ),
                metodo="EFE",
                confirmado=True,
            ).aggregate(s=Sum("monto"))["s"] or Decimal("0.00")
            m_igtf = m_pagos_cash * Decimal("0.03")
            m_utilidad = m_markup - m_igtf

            monthly_chart_data.append(
                {
                    "month": month_str,
                    "neto": float(m_neto),
                    "venta": float(m_venta),
                    "markup": float(m_markup),
                    "igtf": float(m_igtf),
                    "utilidad": float(m_utilidad),
                }
            )

        context["monthly_chart_data"] = monthly_chart_data
        context["ventas"] = (
            ventas_qs.select_related("cliente", "moneda")
            .prefetch_related("pagos_venta")
            .order_by("-fecha_venta")
        )
        context["filters"] = {
            "fecha_inicio": fecha_inicio or "",
            "fecha_fin": fecha_fin or "",
            "pnr": pnr or "",
        }
        return context


class AuditTimelineView(SaaSMixin, LoginRequiredMixin, ListView):
    model = AuditLog
    template_name = "finance/audit_timeline.html"
    context_object_name = "logs"
    paginate_by = 30

    def get_queryset(self):
        qs = super().get_queryset()

        accion = self.request.GET.get("accion")
        modelo = self.request.GET.get("modelo")
        fecha_inicio = self.request.GET.get("fecha_inicio")
        fecha_fin = self.request.GET.get("fecha_fin")
        q = self.request.GET.get("q")

        if accion:
            qs = qs.filter(accion=accion)
        if modelo:
            qs = qs.filter(modelo__icontains=modelo)
        if fecha_inicio:
            qs = qs.filter(creado__date__gte=fecha_inicio)
        if fecha_fin:
            qs = qs.filter(creado__date__lte=fecha_fin)
        if q:
            qs = qs.filter(descripcion__icontains=q)

        return qs.select_related("user").order_by("-creado")

    def get_context_data(self, **kwargs):
        from core.api import AuditLog

        context = super().get_context_data(**kwargs)
        context["filtros"] = {
            "accion": self.request.GET.get("accion", ""),
            "modelo": self.request.GET.get("modelo", ""),
            "fecha_inicio": self.request.GET.get("fecha_inicio", ""),
            "fecha_fin": self.request.GET.get("fecha_fin", ""),
            "q": self.request.GET.get("q", ""),
        }
        context["acciones_choices"] = AuditLog.Accion.choices
        context["active_tab"] = "audit_timeline"
        return context
