import logging
from collections import defaultdict
from datetime import date, timedelta

from dateutil.relativedelta import relativedelta
from django.db.models import Count, Sum

logger = logging.getLogger(__name__)


def _get_model(model_path):
    """_get_model."""
    from django.apps import apps

    return apps.get_model(model_path)


class KPIMetrics:
    """Cálculo centralizado de todas las métricas KPI."""

    def __init__(self, agencia, hoy=None):
        """__init__."""
        self.agencia = agencia
        self.hoy = hoy or date.today()

    # ── Ventas ──────────────────────────────────────────

    def ventas_totales(self):
        """ventas_totales."""
        Venta = _get_model("bookings.Venta")
        return Venta.objects.filter(agencia=self.agencia).count()

    def ventas_diarias(self, dias=30):
        """ventas_diarias."""
        Venta = _get_model("bookings.Venta")
        desde = self.hoy - timedelta(days=dias)
        return Venta.objects.filter(agencia=self.agencia, fecha_venta__date__gte=desde).count()

    def ventas_mensuales(self):
        """ventas_mensuales."""
        Venta = _get_model("bookings.Venta")
        desde = self.hoy - relativedelta(months=1)
        return Venta.objects.filter(agencia=self.agencia, fecha_venta__date__gte=desde).count()

    def ventas_por_dia(self, dias=30):
        """ventas_por_dia."""
        Venta = _get_model("bookings.Venta")
        desde = self.hoy - timedelta(days=dias)
        qs = Venta.objects.filter(agencia=self.agencia, fecha_venta__date__gte=desde)
        counts = defaultdict(int)
        for v in qs.iterator():
            d = v.fecha_venta.date() if hasattr(v.fecha_venta, "date") else v.fecha_venta
            counts[d.isoformat()] += 1
        return dict(sorted(counts.items()))

    def ventas_por_vendedor(self):
        """ventas_por_vendedor."""
        Venta = _get_model("bookings.Venta")
        qs = (
            Venta.objects.filter(agencia=self.agencia)
            .values("creado_por__email")
            .annotate(total=Count("id"), monto=Sum("total_venta"))
        )
        return list(qs)

    def ticket_promedio(self):
        """ticket_promedio."""
        Venta = _get_model("bookings.Venta")
        qs = Venta.objects.filter(agencia=self.agencia)
        total = qs.count()
        if total == 0:
            return 0
        suma = sum(v.total_venta or 0 for v in qs.iterator())
        return suma / total

    # ── Rentabilidad ────────────────────────────────────

    def margen_bruto(self):
        """margen_bruto."""
        Venta = _get_model("bookings.Venta")
        FeeVenta = _get_model("bookings.FeeVenta")
        total_ingresos = sum(
            v.total_venta or 0 for v in Venta.objects.filter(agencia=self.agencia).iterator()
        )
        total_costos = sum(
            f.monto or 0 for f in FeeVenta.objects.filter(agencia=self.agencia).iterator()
        )
        if total_ingresos == 0:
            return 0, 0
        utilidad = total_ingresos - total_costos
        margen = (utilidad / total_ingresos) * 100
        return utilidad, margen

    # ── Tickets / Boletos ────────────────────────────────

    def boletos_importados(self, dias=30):
        """boletos_importados."""
        Boleto = _get_model("bookings.BoletoImportado")
        desde = self.hoy - timedelta(days=dias)
        return Boleto.objects.filter(agencia=self.agencia, created_at__date__gte=desde).count()

    def boletos_por_aerolinea(self):
        """boletos_por_aerolinea."""
        Boleto = _get_model("bookings.BoletoImportado")
        qs = (
            Boleto.objects.filter(agencia=self.agencia)
            .values("aerolinea__nombre")
            .annotate(total=Count("id"))
        )
        return {r["aerolinea__nombre"] or "Sin aerolínea": r["total"] for r in qs}

    # ── Clientes ─────────────────────────────────────────

    def clientes_nuevos(self, dias=30):
        """clientes_nuevos."""
        Cliente = _get_model("crm.Cliente")
        desde = self.hoy - timedelta(days=dias)
        return Cliente.objects.filter(agencia=self.agencia, created_at__date__gte=desde).count()

    def clientes_totales(self):
        """clientes_totales."""
        Cliente = _get_model("crm.Cliente")
        return Cliente.objects.filter(agencia=self.agencia).count()

    def clientes_por_vendedor(self):
        """clientes_por_vendedor."""
        Cliente = _get_model("crm.Cliente")
        qs = (
            Cliente.objects.filter(agencia=self.agencia)
            .values("creado_por__email")
            .annotate(total=Count("id"))
        )
        return {r["creado_por__email"] or "Sin asignar": r["total"] for r in qs}

    # ── Comisiones ───────────────────────────────────────

    def comisiones_pendientes(self):
        """comisiones_pendientes."""
        Comision = _get_model("finance.ComisionVenta")
        qs = Comision.objects.filter(agencia=self.agencia, estado="PEN")
        return qs.count(), sum(c.monto_comision or 0 for c in qs.iterator())

    def comisiones_liquidadas(self):
        """comisiones_liquidadas."""
        Comision = _get_model("finance.ComisionVenta")
        qs = Comision.objects.filter(agencia=self.agencia, estado="LIQ")
        return qs.count(), sum(c.monto_comision or 0 for c in qs.iterator())

    # ── Panorama general ─────────────────────────────────

    def resumen(self):
        """resumen."""
        Venta = _get_model("bookings.Venta")
        ventas_qs = Venta.objects.filter(agencia=self.agencia)
        total_ventas = ventas_qs.count()
        monto_total = ventas_qs.aggregate(total=Sum("total_venta"))["total"] or 0
        ticket_prom = monto_total / total_ventas if total_ventas else 0
        utilidad, margen = self.margen_bruto()

        return {
            "total_ventas": total_ventas,
            "monto_total": monto_total,
            "ticket_promedio": ticket_prom,
            "utilidad": utilidad,
            "margen_bruto": margen,
            "clientes": self.clientes_totales(),
            "boletos": self.boletos_importados(dias=9999),
            "comisiones_pendientes": self.comisiones_pendientes()[0],
            "comisiones_liquidadas": self.comisiones_liquidadas()[0],
        }
