from django.shortcuts import render
from django.db.models import Sum
from core.models import DetalleAsiento
from decimal import Decimal
from django.utils import timezone
from datetime import datetime

def finance_analytics_view(request):
    """
    HTMX partial for the Finance Analytics tab (Mini P&L).
    """
    fecha_desde = request.GET.get('fecha_desde')
    fecha_hasta = request.GET.get('fecha_hasta')
    
    # Defaults to current month if no dates
    if not fecha_desde:
         fecha_desde = timezone.now().replace(day=1).strftime('%Y-%m-%d')
    if not fecha_hasta:
         fecha_hasta = timezone.now().strftime('%Y-%m-%d')
    
    # Base Query: Movimientos confirmados
    detalles = DetalleAsiento.objects.filter(asiento__estado='CON').select_related('cuenta_contable')
    
    detalles = detalles.filter(asiento__fecha_contable__gte=fecha_desde)
    detalles = detalles.filter(asiento__fecha_contable__lte=fecha_hasta)
        
    total_ingresos = Decimal('0')
    total_costos = Decimal('0')
    total_gastos = Decimal('0')
    
    for d in detalles:
        codigo = d.cuenta_contable.codigo_cuenta
        tipo = codigo[0] # 4, 5, 6
        
        if tipo == '4': # Ingresos (Haber suma)
            saldo = d.haber - d.debe
            total_ingresos += saldo
        elif tipo == '5': # Costos (Debe suma)
            saldo = d.debe - d.haber
            total_costos += saldo
        elif tipo == '6': # Gastos (Debe suma)
            saldo = d.debe - d.haber
            total_gastos += saldo

    utilidad_bruta = total_ingresos - total_costos
    utilidad_neta = utilidad_bruta - total_gastos
    
    context = {
        'finance_summary': {
            'ingresos': total_ingresos,
            'costos': total_costos,
            'gastos': total_gastos,
            'utilidad_bruta': utilidad_bruta,
            'utilidad_neta': utilidad_neta
        },
        'filtros': {
            'fecha_desde': fecha_desde,
            'fecha_hasta': fecha_hasta
        }
    }
    
    return render(request, 'analytics/partials/finance_tab.html', context)
