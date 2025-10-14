# core/views/reportes_views.py
from datetime import datetime
from decimal import Decimal
from django.db.models import Sum, Q
from django.http import HttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.models import AsientoContable, DetalleAsiento, Venta, Factura


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def libro_diario(request):
    """
    Libro diario contable con filtros por fecha.
    """
    fecha_desde = request.GET.get('fecha_desde')
    fecha_hasta = request.GET.get('fecha_hasta')
    
    asientos_qs = AsientoContable.objects.all().prefetch_related('detalles_asiento')
    
    if fecha_desde:
        asientos_qs = asientos_qs.filter(fecha_contable__gte=fecha_desde)
    if fecha_hasta:
        asientos_qs = asientos_qs.filter(fecha_contable__lte=fecha_hasta)
    
    asientos_qs = asientos_qs.order_by('fecha_contable', 'numero_asiento')
    
    libro = []
    for asiento in asientos_qs:
        libro.append({
            'numero_asiento': asiento.numero_asiento,
            'fecha': asiento.fecha_contable.isoformat(),
            'descripcion': asiento.descripcion_general,
            'total_debe': float(asiento.total_debe),
            'total_haber': float(asiento.total_haber),
            'esta_cuadrado': asiento.esta_cuadrado,
            'estado': asiento.estado,
            'detalles': [
                {
                    'cuenta': detalle.cuenta_contable.codigo_cuenta,
                    'cuenta_nombre': detalle.cuenta_contable.nombre_cuenta,
                    'descripcion': detalle.descripcion_linea,
                    'debe': float(detalle.debe),
                    'haber': float(detalle.haber)
                }
                for detalle in asiento.detalles_asiento.all()
            ]
        })
    
    return Response({
        'periodo': {
            'desde': fecha_desde,
            'hasta': fecha_hasta
        },
        'total_asientos': len(libro),
        'asientos': libro
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
            'debe': float(debe),
            'haber': float(haber),
            'saldo': float(saldo),
            'naturaleza': 'Deudora' if saldo > 0 else 'Acreedora' if saldo < 0 else 'Saldada'
        })
        
        total_debe += debe
        total_haber += haber
    
    return Response({
        'fecha_corte': fecha_hasta,
        'balance': balance,
        'totales': {
            'debe': float(total_debe),
            'haber': float(total_haber),
            'diferencia': float(total_debe - total_haber)
        }
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def validar_cuadre(request):
    """
    Valida que todos los asientos estén cuadrados.
    """
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
            'fecha': asiento.fecha_contable.isoformat(),
            'debe': float(asiento.total_debe),
            'haber': float(asiento.total_haber),
            'diferencia': float(asiento.total_debe - asiento.total_haber)
        })
    
    return Response({
        'cuadrado': len(problemas) == 0,
        'asientos_con_problemas': len(problemas),
        'problemas': problemas
    })


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
