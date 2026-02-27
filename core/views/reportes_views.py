# core/views/reportes_views.py
from datetime import datetime
from decimal import Decimal
from django.db.models import Sum, Q, F
from django.http import HttpResponse
from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.models import AsientoContable, DetalleAsiento, Venta
from apps.finance.models import Factura


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def libro_diario(request):
    """
    Libro diario contable con filtros por fecha.
    """
    fecha_desde = request.GET.get('fecha_desde')
    fecha_hasta = request.GET.get('fecha_hasta')
    
    asientos_qs = AsientoContable.objects.all().prefetch_related('detalles_asiento__cuenta_contable')
    
    if fecha_desde:
        asientos_qs = asientos_qs.filter(fecha_contable__gte=fecha_desde)
    if fecha_hasta:
        asientos_qs = asientos_qs.filter(fecha_contable__lte=fecha_hasta)
    
    asientos_qs = asientos_qs.order_by('fecha_contable', 'numero_asiento')
    
    libro = []
    for asiento in asientos_qs:
        libro.append({
            'numero_asiento': asiento.numero_asiento,
            'fecha': asiento.fecha_contable,
            'descripcion': asiento.descripcion_general,
            'total_debe': asiento.total_debe,
            'total_haber': asiento.total_haber,
            'esta_cuadrado': asiento.esta_cuadrado,
            'estado': asiento.estado,
            'detalles': [
                {
                    'cuenta': detalle.cuenta_contable.codigo_cuenta,
                    'cuenta_nombre': detalle.cuenta_contable.nombre_cuenta,
                    'descripcion': detalle.descripcion_linea,
                    'debe': detalle.debe,
                    'haber': detalle.haber
                }
                for detalle in asiento.detalles_asiento.all()
            ]
        })
    
    if request.accepted_renderer.format == 'json':
        return Response({
            'periodo': {
                'desde': fecha_desde,
                'hasta': fecha_hasta
            },
            'total_asientos': len(libro),
            'asientos': libro
        })
    
    return render(request, 'core/reportes/libro_diario.html', {
        'asientos': libro,
        'active_tab': 'reportes'
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def balance_comprobacion(request):
    """
    Balance de comprobación (sumas y saldos).
    """
    fecha_hasta = request.GET.get('fecha_hasta')
    
    detalles_qs = DetalleAsiento.objects.select_related('cuenta_contable', 'asiento')
    
    if fecha_hasta:
        detalles_qs = detalles_qs.filter(asiento__fecha_contable__lte=fecha_hasta)
    
    # Agrupar por cuenta
    from collections import defaultdict
    cuentas = defaultdict(lambda: {'debe': Decimal('0'), 'haber': Decimal('0')})
    
    for detalle in detalles_qs:
        cuenta_codigo = detalle.cuenta_contable.codigo_cuenta
        cuentas[cuenta_codigo]['nombre'] = detalle.cuenta_contable.nombre_cuenta
        cuentas[cuenta_codigo]['debe'] += detalle.debe
        cuentas[cuenta_codigo]['haber'] += detalle.haber
    
    balance = []
    total_debe = Decimal('0')
    total_haber = Decimal('0')
    
    for codigo, datos in sorted(cuentas.items()):
        debe = datos['debe']
        haber = datos['haber']
        saldo = debe - haber
        
        balance.append({
            'cuenta': codigo,
            'nombre': datos['nombre'],
            'debe': debe,
            'haber': haber,
            'saldo': saldo,
            'naturaleza': 'Deudora' if saldo > 0 else 'Acreedora' if saldo < 0 else 'Saldada'
        })
        
        total_debe += debe
        total_haber += haber
    
    context = {
        'fecha_corte': fecha_hasta,
        'balance': balance,
        'totales': {
            'debe': total_debe,
            'haber': total_haber,
            'diferencia': total_debe - total_haber
        },
        'active_tab': 'reportes'
    }

    if request.accepted_renderer.format == 'json':
        return Response(context)
        
    return render(request, 'core/reportes/balance.html', context)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def validar_cuadre(request):
    """
    Valida que todos los asientos estén cuadrados.
    """
    if request.method == 'GET' and request.accepted_renderer.format != 'json':
         return render(request, 'core/reportes/validacion.html', {'active_tab': 'reportes'})

    asientos_descuadrados = AsientoContable.objects.filter(
        Q(total_debe__gt=0) | Q(total_haber__gt=0)
    ).exclude(total_debe=F('total_haber'))
    
    from django.db.models import F
    asientos_descuadrados = AsientoContable.objects.annotate(
        diferencia=F('total_debe') - F('total_haber')
    ).exclude(diferencia=0)
    
    problemas = []
    for asiento in asientos_descuadrados:
        problemas.append({
            'numero_asiento': asiento.numero_asiento,
            'fecha': asiento.fecha_contable,
            'debe': asiento.total_debe,
            'haber': asiento.total_haber,
            'diferencia': asiento.total_debe - asiento.total_haber
        })
    
    context = {
        'cuadrado': len(problemas) == 0,
        'asientos_con_problemas': len(problemas),
        'problemas': problemas,
        'active_tab': 'reportes'
    }

    if request.accepted_renderer.format == 'json':
        return Response(context)
        
    return render(request, 'core/reportes/validacion.html', {'validacion': context, 'active_tab': 'reportes'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def exportar_excel(request):
    """
    Exporta libro diario a Excel (requiere openpyxl).
    """
    try:
        import openpyxl
        from openpyxl.styles import Font, Alignment
    except ImportError:
        return Response(
            {'error': 'openpyxl no instalado. Ejecute: pip install openpyxl'},
            status=500
        )
    
    fecha_desde = request.GET.get('fecha_desde')
    fecha_hasta = request.GET.get('fecha_hasta')
    
    asientos_qs = AsientoContable.objects.all().prefetch_related('detalles_asiento')
    
    if fecha_desde:
        asientos_qs = asientos_qs.filter(fecha_contable__gte=fecha_desde)
    if fecha_hasta:
        asientos_qs = asientos_qs.filter(fecha_contable__lte=fecha_hasta)
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Libro Diario"
    
    # Encabezados
    headers = ['Fecha', 'Nro Asiento', 'Cuenta', 'Descripción', 'Debe', 'Haber']
    ws.append(headers)
    
    for cell in ws[1]:
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='center')
    
    # Datos
    for asiento in asientos_qs.order_by('fecha_contable'):
        for detalle in asiento.detalles_asiento.all():
            ws.append([
                asiento.fecha_contable.strftime('%Y-%m-%d'),
                asiento.numero_asiento,
                detalle.cuenta_contable.codigo_cuenta,
                detalle.descripcion_linea,
                float(detalle.debe),
                float(detalle.haber)
            ])
    
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="libro_diario_{datetime.now().strftime("%Y%m%d")}.xlsx"'
    wb.save(response)
    
    return response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def estado_resultados(request):
    """
    Estado de Resultados (P&L) - Ingresos vs Gastos
    Basado estrictamente en Movimientos Contables (Clases 4, 5, 6)
    """
    fecha_desde = request.GET.get('fecha_desde')
    fecha_hasta = request.GET.get('fecha_hasta')
    
    # Base Query: Todos los detalles de asientos confirmados
    detalles = DetalleAsiento.objects.filter(asiento__estado='CON').select_related('cuenta_contable')
    
    if fecha_desde:
        detalles = detalles.filter(asiento__fecha_contable__gte=fecha_desde)
    if fecha_hasta:
        detalles = detalles.filter(asiento__fecha_contable__lte=fecha_hasta)
        
    # Estructuras de Acumulación
    ingresos = []     # Clase 4 (Naturaleza Acreedora: Haber - Debe)
    costos = []       # Clase 5 (Naturaleza Deudora: Debe - Haber)
    gastos = []       # Clase 6 (Naturaleza Deudora: Debe - Haber)
    
    total_ingresos = Decimal('0')
    total_costos = Decimal('0')
    total_gastos = Decimal('0')
    
    # Agrupación por cuenta mayor (2 dígitos) o auxiliar
    from collections import defaultdict
    agrupador = defaultdict(lambda: {'nombre': '', 'saldo': Decimal('0'), 'tipo': ''})
    
    for d in detalles:
        codigo = d.cuenta_contable.codigo_cuenta
        nombre = d.cuenta_contable.nombre_cuenta
        tipo = codigo[0] # 4, 5, 6
        
        # Calcular saldo según naturaleza
        if tipo == '4': # Ingresos (Haber suma)
            saldo = d.haber - d.debe
        else: # Costos/Gastos (Debe suma)
            saldo = d.debe - d.haber
            
        if saldo == 0: continue
        
        agrupador[codigo]['nombre'] = nombre
        agrupador[codigo]['tipo'] = tipo
        agrupador[codigo]['saldo'] += saldo

    # Clasificar resultados
    for codigo, data in agrupador.items():
        item = {'cuenta': codigo, 'nombre': data['nombre'], 'monto': data['saldo']}
        
        if data['tipo'] == '4':
            ingresos.append(item)
            total_ingresos += data['saldo']
        elif data['tipo'] == '5':
            costos.append(item)
            total_costos += data['saldo']
        elif data['tipo'] == '6':
            gastos.append(item)
            total_gastos += data['saldo']
            
    # Cálculos Finales
    utilidad_bruta = total_ingresos - total_costos
    utilidad_neta = utilidad_bruta - total_gastos
    
    context = {
        'periodo': {'desde': fecha_desde, 'hasta': fecha_hasta},
        'ingresos': sorted(ingresos, key=lambda x: x['cuenta']),
        'total_ingresos': total_ingresos,
        'costos': sorted(costos, key=lambda x: x['cuenta']),
        'total_costos': total_costos,
        'utilidad_bruta': utilidad_bruta,
        'gastos': sorted(gastos, key=lambda x: x['cuenta']),
        'total_gastos': total_gastos,
        'utilidad_neta': utilidad_neta,
        'margen_bruto_pct': (utilidad_bruta / total_ingresos * 100) if total_ingresos > 0 else 0,
        'margen_neto_pct': (utilidad_neta / total_ingresos * 100) if total_ingresos > 0 else 0,
        'active_tab': 'reportes'
    }
    
    if request.accepted_renderer.format == 'json':
        return Response(context)
        
    return render(request, 'core/reportes/estado_resultados.html', context)
