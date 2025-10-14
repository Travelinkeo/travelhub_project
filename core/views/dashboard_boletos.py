# core/views/dashboard_boletos.py
"""
API y Vista HTML para el Dashboard de Ventas de Boletos.
"""

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Sum
from decimal import Decimal
import json

from core.models import Venta, ItemVenta, BoletoImportado
from personas.models import Pasajero


def dashboard_boletos_html(request):
    """
    Vista HTML del dashboard de ventas de boletos.
    """
    return render(request, 'core/dashboard_ventas_boletos.html')


@require_http_methods(["GET"])
def ventas_boletos_api(request):
    """
    API REST para obtener TODOS los boletos (con y sin venta).
    """
    # Filtros
    localizador = request.GET.get('localizador', '')
    fecha_desde = request.GET.get('fecha_desde', '')
    fecha_hasta = request.GET.get('fecha_hasta', '')
    
    # Query base: TODOS los boletos importados
    boletos = BoletoImportado.objects.all().select_related('venta_asociada')
    
    # Aplicar filtros
    if localizador:
        boletos = boletos.filter(localizador__icontains=localizador)
    if fecha_desde:
        boletos = boletos.filter(fecha_subida__gte=fecha_desde)
    if fecha_hasta:
        boletos = boletos.filter(fecha_subida__lte=fecha_hasta)
    
    # Construir datos
    ventas_data = []
    for boleto in boletos.order_by('-fecha_subida'):
        # Datos del parseo
        parseo = boleto.datos_parseados or {}
        
        # Datos de venta (si existe)
        venta = boleto.venta_asociada
        
        # Datos del boleto
        boleto_data = {
            'id': boleto.id_boleto_importado,
            'localizador': boleto.localizador_pnr or 'N/A',
            'numero_boleto': boleto.numero_boleto or 'N/A',
            'fecha': boleto.fecha_subida.isoformat(),
            'cliente': venta.cliente.get_nombre_completo() if venta and venta.cliente else 'Sin asignar',
            'pasajeros': [{
                'id': 0,
                'apellidos': boleto.nombre_pasajero_completo or 'N/A',
                'nombres': '',
                'tipo': 'PASS',
                'documento': boleto.foid_pasajero or 'N/A'
            }],
            'cantidad_boletos': 1,
            'aerolinea': boleto.aerolinea_emisora or 'N/A',
            'proveedores': [parseo.get('proveedor', 'N/A')] if isinstance(parseo.get('proveedor'), str) else ['N/A'],
            'total_venta': float(parseo.get('total', 0)) if isinstance(parseo.get('total'), (int, float)) else 0,
            'costo_neto': float(venta.total_venta if venta else 0),
            'fee_proveedor': 0,
            'comision': 0,
            'fee_agencia': 0,
            'margen': 0,
            'estado': venta.estado if venta else 'N/A',
            'estado_display': venta.get_estado_display() if venta else 'Sin venta',
            'moneda': parseo.get('moneda', 'USD') if isinstance(parseo.get('moneda'), str) else 'USD',
            'items': []
        }
        
        ventas_data.append(boleto_data)
    
    # Estadísticas
    stats = {
        'total_ventas': len(ventas_data),
        'total_boletos': len(ventas_data),
        'total_ingresos': sum(v['total_venta'] for v in ventas_data),
        'total_margen': sum(v['margen'] for v in ventas_data)
    }
    
    return JsonResponse({
        'ventas': ventas_data,
        'stats': stats,
        'filtros': {
            'localizador': localizador,
            'fecha_desde': fecha_desde,
            'fecha_hasta': fecha_hasta
        }
    })


@csrf_exempt
@require_http_methods(["POST"])
def actualizar_item_boleto(request):
    """
    API para actualizar información financiera de un item de boleto.
    """
    try:
        data = json.loads(request.body)
        item_id = data.get('item_id')
        campo = data.get('campo')
        valor = data.get('valor')
        
        # Validar
        if not item_id or not campo:
            return JsonResponse({'error': 'Parámetros requeridos'}, status=400)
        
        # Obtener item
        item = ItemVenta.objects.get(id_item_venta=item_id)
        
        # Campos permitidos
        campos_permitidos = {
            'costo_neto_proveedor': Decimal,
            'fee_proveedor': Decimal,
            'comision_agencia_monto': Decimal,
            'fee_agencia_interno': Decimal,
        }
        
        if campo not in campos_permitidos:
            return JsonResponse({'error': 'Campo no permitido'}, status=400)
        
        # Actualizar
        valor_convertido = campos_permitidos[campo](valor or '0')
        setattr(item, campo, valor_convertido)
        item.save()
        
        # Recalcular finanzas
        item.venta.recalcular_finanzas()
        
        return JsonResponse({
            'success': True,
            'nuevo_valor': float(valor_convertido),
            'total_venta': float(item.venta.total_venta),
            'margen': float(item.venta.margen_estimado or 0)
        })
        
    except ItemVenta.DoesNotExist:
        return JsonResponse({'error': 'Item no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
