"""
Vistas de reporte y fiscalidad especializada para turismo en Venezuela.
Implementa:
  - Libro de Ventas Fiscal Sentencia TSJ 00256.
  - Guía de Doble Retención SPE (PDF/HTML).
  - Dashboard de Regulaciones (INATUR 1%, LOCTEM 3%, IGTF 3%, Coeficiente Ce).
"""

import logging
from decimal import Decimal

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.generic import TemplateView

from apps.finance.models import Factura
from apps.finance.services.fiscal_service import FiscalTurismoService
from core.api import SaaSMixin

logger = logging.getLogger(__name__)


class LibroVentasTSJ256View(SaaSMixin, LoginRequiredMixin, TemplateView):
    """
    Libro de Ventas Fiscal blindado bajo la Sentencia TSJ N° 00256 (Caso Viajes Escala, C.A.).
    Segrega explícitamente Ventas por Cuenta de Terceros de Ingresos Propios por Intermediación.
    """

    template_name = "finance/reports/libro_ventas_tsj256.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        agencia = self.request.agencia

        # Filtrado por rango de fechas (default: mes actual)
        now = timezone.localtime(timezone.now())
        fecha_inicio_str = self.request.GET.get("fecha_inicio")
        fecha_fin_str = self.request.GET.get("fecha_fin")

        qs = Factura.objects.filter(
            agencia=agencia,
            estado=Factura.EstadoFactura.EMITIDA,
        ).select_related("cliente")

        if fecha_inicio_str:
            qs = qs.filter(fecha_emision__gte=fecha_inicio_str)
        else:
            qs = qs.filter(fecha_emision__month=now.month, fecha_emision__year=now.year)

        if fecha_fin_str:
            qs = qs.filter(fecha_emision__lte=fecha_fin_str)

        facturas = list(qs.order_by("-fecha_emision", "-numero_control"))

        # Totales acumulados del período
        total_ventas_usd = sum(f.gran_total_usd for f in facturas)
        total_terceros_usd = sum(f.monto_cuenta_terceros_usd for f in facturas)
        total_ingresos_usd = sum(f.ingreso_propio_agencia_usd for f in facturas)
        total_iva_usd = sum(f.total_iva_usd for f in facturas)
        total_inatur_usd = sum(f.monto_inatur_1_usd for f in facturas)
        total_loctem_usd = sum(f.monto_impuesto_municipal_usd for f in facturas)

        total_ventas_ves = sum(f.gran_total_ves for f in facturas)
        total_terceros_ves = sum(f.monto_cuenta_terceros_ves for f in facturas)
        total_ingresos_ves = sum(f.ingreso_propio_agencia_ves for f in facturas)
        total_iva_ves = sum(f.total_iva_ves for f in facturas)
        total_inatur_ves = sum(f.monto_inatur_1_ves for f in facturas)
        total_loctem_ves = sum(f.monto_impuesto_municipal_ves for f in facturas)

        context.update(
            {
                "facturas": facturas,
                "fecha_inicio": fecha_inicio_str or f"{now.year}-{now.month:02d}-01",
                "fecha_fin": fecha_fin_str or now.strftime("%Y-%m-%d"),
                "total_ventas_usd": total_ventas_usd,
                "total_terceros_usd": total_terceros_usd,
                "total_ingresos_usd": total_ingresos_usd,
                "total_iva_usd": total_iva_usd,
                "total_inatur_usd": total_inatur_usd,
                "total_loctem_usd": total_loctem_usd,
                "total_ventas_ves": total_ventas_ves,
                "total_terceros_ves": total_terceros_ves,
                "total_ingresos_ves": total_ingresos_ves,
                "total_iva_ves": total_iva_ves,
                "total_inatur_ves": total_inatur_ves,
                "total_loctem_ves": total_loctem_ves,
            }
        )
        return context


class GuiaRetencionSPEView(SaaSMixin, LoginRequiredMixin, TemplateView):
    """
    Vista de Guía e Instructivo de Doble Retención para Clientes Institucionales / SPE.
    """

    template_name = "finance/vouchers/guia_retencion_spe.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        factura_id = self.kwargs.get("factura_id")
        factura = get_object_or_404(Factura, pk=factura_id, agencia=self.request.agencia)

        guia_data = FiscalTurismoService.generar_guia_retencion_spe(factura)
        context.update(
            {
                "factura": factura,
                "guia": guia_data,
            }
        )
        return context


class DashboardRegulacionesView(SaaSMixin, LoginRequiredMixin, TemplateView):
    """
    Tablero Ejecutivo de Regulaciones y Finanzas Turísticas.
    Monitorea el 1% INATUR, LOCTEM (3% máx), IGTF (3%) y Coeficiente de Estima (Ce).
    """

    template_name = "finance/reports/dashboard_regulaciones.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        agencia = self.request.agencia
        now = timezone.localtime(timezone.now())

        # Facturas del mes actual
        facturas_mes = Factura.objects.filter(
            agencia=agencia,
            estado=Factura.EstadoFactura.EMITIDA,
            fecha_emision__month=now.month,
            fecha_emision__year=now.year,
        )

        inatur_acumulado_usd = facturas_mes.aggregate(s=Sum("monto_inatur_1_usd"))["s"] or Decimal(
            "0"
        )
        inatur_acumulado_ves = facturas_mes.aggregate(s=Sum("monto_inatur_1_ves"))["s"] or Decimal(
            "0"
        )

        base_loctem_usd = facturas_mes.aggregate(s=Sum("base_impuesto_municipal_usd"))[
            "s"
        ] or Decimal("0")
        loctem_estimado_usd = facturas_mes.aggregate(s=Sum("monto_impuesto_municipal_usd"))[
            "s"
        ] or Decimal("0")

        igtf_acumulado_usd = facturas_mes.aggregate(s=Sum("total_igtf_usd"))["s"] or Decimal("0")
        igtf_acumulado_ves = facturas_mes.aggregate(s=Sum("total_igtf_ves"))["s"] or Decimal("0")

        # Coeficiente de Estima (Ce = Ventas Históricas Acumuladas / Ventas Año Actual)
        ventas_ano_actual = Factura.objects.filter(
            agencia=agencia,
            estado=Factura.EstadoFactura.EMITIDA,
            fecha_emision__year=now.year,
        ).aggregate(s=Sum("gran_total_usd"))["s"] or Decimal("0")

        ventas_mes_actual = facturas_mes.aggregate(s=Sum("gran_total_usd"))["s"] or Decimal("0")

        coeficiente_estima = Decimal("1.00")
        if ventas_ano_actual > 0:
            coeficiente_estima = (
                ventas_mes_actual / (ventas_ano_actual / Decimal(str(now.month)))
            ).quantize(Decimal("0.01"))

        context.update(
            {
                "mes_nombre": now.strftime("%B %Y"),
                "inatur_acumulado_usd": inatur_acumulado_usd,
                "inatur_acumulado_ves": inatur_acumulado_ves,
                "base_loctem_usd": base_loctem_usd,
                "loctem_estimado_usd": loctem_estimado_usd,
                "igtf_acumulado_usd": igtf_acumulado_usd,
                "igtf_acumulado_ves": igtf_acumulado_ves,
                "ventas_mes_actual": ventas_mes_actual,
                "ventas_ano_actual": ventas_ano_actual,
                "coeficiente_estima": coeficiente_estima,
            }
        )
        return context
