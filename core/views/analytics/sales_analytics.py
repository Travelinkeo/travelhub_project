from django.shortcuts import render
from django.utils import timezone
from django.db.models.functions import ExtractYear
from apps.bookings.models import Venta
from core.services.analytics_service import AnalyticsService

def sales_analytics_view(request):
    """
    HTMX partial for the Sales Analytics tab.
    """
    year_param = request.GET.get('year')
    current_year = timezone.now().year
    selected_year = int(year_param) if year_param and year_param.isdigit() else current_year

    context = {}
    
    # Data Services using existing AnalyticsService
    context['sales_chart'] = AnalyticsService.get_ventas_mensuales(selected_year)
    context['top_airlines'] = AnalyticsService.get_top_aerolineas(selected_year)
    context['top_sellers'] = AnalyticsService.get_top_vendedores(selected_year)
    context['kpis'] = AnalyticsService.get_kpis_resumen(selected_year)
    
    # Available years for filter
    available_years = Venta.objects.annotate(year=ExtractYear('fecha_venta')).values_list('year', flat=True).order_by('-year').distinct()
    context['available_years'] = sorted(list(set(available_years)), reverse=True) if available_years else [current_year]
    context['selected_year'] = selected_year
    
    # If HTMX request, return partial, else it might be included in main dashboard
    return render(request, 'analytics/partials/sales_tab.html', context)
