from django.shortcuts import render
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
from apps.bookings.models import BoletoImportado, Venta
from django.contrib.auth import get_user_model

User = get_user_model()

def ops_analytics_view(request):
    """
    HTMX partial for the Operations Analytics tab.
    """
    hoy = timezone.now().date()
    inicio_mes = hoy.replace(day=1)
    
    # 1. Productividad General
    boletos_mes = BoletoImportado.objects.filter(fecha_subida__date__gte=inicio_mes).count()
    ventas_mes = Venta.objects.filter(fecha_venta__date__gte=inicio_mes).count()
    
    # 2. Top Usuarios (Productividad)
    top_users = Venta.objects.filter(
        fecha_venta__date__gte=inicio_mes
    ).values(
        'creado_por__username', 
        'creado_por__first_name', 
        'creado_por__last_name'
    ).annotate(
        total_ventas=Count('id_venta')
    ).order_by('-total_ventas')[:5]
    
    # 3. Errores / Pendientes
    boletos_sin_venta = BoletoImportado.objects.filter(venta_asociada__isnull=True).count()
    
    context = {
        'ops_stats': {
            'boletos_mes': boletos_mes,
            'ventas_mes': ventas_mes,
            'boletos_pendientes': boletos_sin_venta
        },
        'top_users': top_users,
        'periodo': 'Mes Actual'
    }
    
    return render(request, 'analytics/partials/ops_tab.html', context)
