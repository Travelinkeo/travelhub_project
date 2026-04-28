
from django.db.models.functions import ExtractYear
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from core.models.ventas import Venta
from core.services.analytics_service import AnalyticsService

class ReportesVentasView(LoginRequiredMixin, TemplateView):
    template_name = "reports/dashboard_reports_v3.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Filtros
        year_param = self.request.GET.get('year')
        current_year = timezone.now().year
        selected_year = int(year_param) if year_param and year_param.isdigit() else current_year

        # Data Services
        print(f"DEBUG: ReportesVentasView - Selected Year: {selected_year} (Type: {type(selected_year)})")
        
        # Direct Query Debug
        direct_count = Venta.objects.filter(fecha_venta__year=selected_year).count()
        print(f"DEBUG: Direct Query Count in View for {selected_year}: {direct_count}")
        
        context['sales_chart'] = AnalyticsService.get_ventas_mensuales(selected_year)
        context['top_airlines'] = AnalyticsService.get_top_aerolineas(selected_year)
        context['top_sellers'] = AnalyticsService.get_top_vendedores(selected_year)
        context['kpis'] = AnalyticsService.get_kpis_resumen(selected_year)
        print(f"DEBUG: KPIs: {context['kpis']}")
        print(f"DEBUG: Sales Chart: {context['sales_chart']}")
        
        # Selectores
        # Obtener lista de años disponibles
        available_years = Venta.objects.annotate(year=ExtractYear('fecha_venta')).values_list('year', flat=True).order_by('-year').distinct()
        # Fallback for SQLite distinct issue if any
        context['available_years'] = sorted(list(set(available_years)), reverse=True) if available_years else [current_year]
        context['selected_year'] = selected_year
        
        return context
