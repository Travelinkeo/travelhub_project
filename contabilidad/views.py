# contabilidad/views.py
"""
Vistas para reportes contables en el admin.
"""

from datetime import date, timedelta
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.http import JsonResponse

from .reportes import ReportesContables
from .models import PlanContable


@staff_member_required
def reporte_balance_comprobacion(request):
    """Vista para Balance de Comprobación"""
    
    # Fechas por defecto: mes actual
    hoy = date.today()
    fecha_desde = request.GET.get('desde', hoy.replace(day=1))
    fecha_hasta = request.GET.get('hasta', hoy)
    moneda = request.GET.get('moneda', 'USD')
    
    if isinstance(fecha_desde, str):
        fecha_desde = date.fromisoformat(fecha_desde)
    if isinstance(fecha_hasta, str):
        fecha_hasta = date.fromisoformat(fecha_hasta)
    
    resultado = ReportesContables.balance_comprobacion(fecha_desde, fecha_hasta, moneda)
    
    return render(request, 'contabilidad/balance_comprobacion.html', {
        'resultado': resultado,
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
        'moneda': moneda
    })


@staff_member_required
def reporte_estado_resultados(request):
    """Vista para Estado de Resultados"""
    
    hoy = date.today()
    fecha_desde = request.GET.get('desde', hoy.replace(day=1))
    fecha_hasta = request.GET.get('hasta', hoy)
    moneda = request.GET.get('moneda', 'USD')
    
    if isinstance(fecha_desde, str):
        fecha_desde = date.fromisoformat(fecha_desde)
    if isinstance(fecha_hasta, str):
        fecha_hasta = date.fromisoformat(fecha_hasta)
    
    resultado = ReportesContables.estado_resultados(fecha_desde, fecha_hasta, moneda)
    
    return render(request, 'contabilidad/estado_resultados.html', {
        'resultado': resultado,
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
        'moneda': moneda
    })


@staff_member_required
def reporte_balance_general(request):
    """Vista para Balance General"""
    
    hoy = date.today()
    fecha_corte = request.GET.get('fecha', hoy)
    moneda = request.GET.get('moneda', 'USD')
    
    if isinstance(fecha_corte, str):
        fecha_corte = date.fromisoformat(fecha_corte)
    
    resultado = ReportesContables.balance_general(fecha_corte, moneda)
    
    return render(request, 'contabilidad/balance_general.html', {
        'resultado': resultado,
        'fecha_corte': fecha_corte,
        'moneda': moneda
    })


@staff_member_required
def reporte_libro_diario(request):
    """Vista para Libro Diario"""
    
    hoy = date.today()
    fecha_desde = request.GET.get('desde', hoy.replace(day=1))
    fecha_hasta = request.GET.get('hasta', hoy)
    moneda = request.GET.get('moneda', 'USD')
    
    if isinstance(fecha_desde, str):
        fecha_desde = date.fromisoformat(fecha_desde)
    if isinstance(fecha_hasta, str):
        fecha_hasta = date.fromisoformat(fecha_hasta)
    
    asientos = ReportesContables.libro_diario(fecha_desde, fecha_hasta, moneda)
    
    return render(request, 'contabilidad/libro_diario.html', {
        'asientos': asientos,
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
        'moneda': moneda
    })


@staff_member_required
def reporte_libro_mayor(request):
    """Vista para Libro Mayor"""
    
    cuenta_id = request.GET.get('cuenta')
    if not cuenta_id:
        # Mostrar selector de cuenta
        cuentas = PlanContable.objects.filter(permite_movimientos=True).order_by('codigo_cuenta')
        return render(request, 'contabilidad/libro_mayor_selector.html', {'cuentas': cuentas})
    
    hoy = date.today()
    fecha_desde = request.GET.get('desde', hoy.replace(day=1))
    fecha_hasta = request.GET.get('hasta', hoy)
    moneda = request.GET.get('moneda', 'USD')
    
    if isinstance(fecha_desde, str):
        fecha_desde = date.fromisoformat(fecha_desde)
    if isinstance(fecha_hasta, str):
        fecha_hasta = date.fromisoformat(fecha_hasta)
    
    resultado = ReportesContables.libro_mayor(int(cuenta_id), fecha_desde, fecha_hasta, moneda)
    
    return render(request, 'contabilidad/libro_mayor.html', {
        'resultado': resultado,
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
        'moneda': moneda
    })
