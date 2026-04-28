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
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@require_http_methods(["GET"])
def dashboard_metricas_api(request):
    """
    API para obtener métricas del dashboard de boletos.
    """
    from django.utils import timezone
    from datetime import timedelta
    from django.db.models import Count, Q

    hoy = timezone.now().date()
    inicio_semana = hoy - timedelta(days=hoy.weekday())
    inicio_mes = hoy.replace(day=1)

    # Métricas de procesados
    procesados_hoy = BoletoImportado.objects.filter(fecha_subida__date=hoy).count()
    procesados_semana = BoletoImportado.objects.filter(fecha_subida__date__gte=inicio_semana).count()
    procesados_mes = BoletoImportado.objects.filter(fecha_subida__date__gte=inicio_mes).count()

    # Top Aerolíneas (del mes actual)
    top_aerolineas = BoletoImportado.objects.filter(
        fecha_subida__date__gte=inicio_mes
    ).values('aerolinea_emisora').annotate(
        cantidad=Count('id_boleto_importado')
    ).order_by('-cantidad')[:5]

    # Estado de ventas
    pendientes = Venta.objects.filter(estado='PEN').count()
    errores = BoletoImportado.objects.filter(venta_asociada__isnull=True).count() # Asumiendo que sin venta es un error o pendiente de procesar

    return JsonResponse({
        'procesados': {
            'hoy': procesados_hoy,
            'semana': procesados_semana,
            'mes': procesados_mes
        },
        'top_aerolineas': list(top_aerolineas),
        'pendientes': pendientes,
        'errores': errores
    })


@require_http_methods(["GET"])
def buscar_boletos_api(request):
    """
    API para búsqueda avanzada de boletos.
    """
    nombre = request.GET.get('nombre')
    pnr = request.GET.get('pnr')
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    origen = request.GET.get('origen')
    destino = request.GET.get('destino')
    
    queryset = BoletoImportado.objects.all().select_related('venta_asociada')
    
    if nombre:
        queryset = queryset.filter(nombre_pasajero_completo__icontains=nombre)
    if pnr:
        queryset = queryset.filter(localizador_pnr__icontains=pnr)
    if fecha_inicio:
        queryset = queryset.filter(fecha_emision_boleto__gte=fecha_inicio)
    if fecha_fin:
        queryset = queryset.filter(fecha_emision_boleto__lte=fecha_fin)
    if origen:
        queryset = queryset.filter(ruta_vuelo__icontains=origen)
    if destino:
        queryset = queryset.filter(ruta_vuelo__icontains=destino)
        
    resultados = []
    for boleto in queryset.order_by('-fecha_emision_boleto')[:50]: # Limit to 50 results
        resultados.append({
            'id_boleto_importado': boleto.id_boleto_importado,
            'numero_boleto': boleto.numero_boleto,
            'nombre_pasajero_procesado': boleto.nombre_pasajero_completo,
            'aerolinea_emisora': boleto.aerolinea_emisora,
            'total_boleto': float(boleto.total_boleto or 0),
            'localizador_pnr': boleto.localizador_pnr,
            'fecha_emision': boleto.fecha_emision_boleto.isoformat() if boleto.fecha_emision_boleto else None,
            'ruta': boleto.ruta_vuelo
        })
        
    return JsonResponse(resultados, safe=False)


@require_http_methods(["GET"])
def reporte_comisiones_api(request):
    """
    API para reporte de comisiones.
    """
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    
    queryset = BoletoImportado.objects.filter(venta_asociada__isnull=False)
    
    if fecha_inicio:
        queryset = queryset.filter(fecha_emision_boleto__gte=fecha_inicio)
    if fecha_fin:
        queryset = queryset.filter(fecha_emision_boleto__lte=fecha_fin)
        
    # Agrupar por aerolínea
    por_aerolinea = []
    aerolineas = queryset.values('aerolinea_emisora').annotate(
        cantidad=Count('id_boleto_importado'),
        total_ventas=Sum('venta_asociada__total_venta')
    )
    
    total_boletos = 0
    total_ventas = 0
    total_comisiones = 0
    
    for item in aerolineas:
        # Calcular comisión estimada (esto es un ejemplo, ajustar según lógica real)
        # Asumiendo que la comisión está en la venta o se calcula
        ventas_aerolinea = queryset.filter(aerolinea_emisora=item['aerolinea_emisora'])
        comision_aerolinea = sum(v.venta_asociada.comision for v in ventas_aerolinea if v.venta_asociada.comision)
        
        por_aerolinea.append({
            'aerolinea': item['aerolinea_emisora'],
            'cantidad_boletos': item['cantidad'],
            'total_ventas': float(item['total_ventas'] or 0),
            'total_comisiones': float(comision_aerolinea)
        })
        
        total_boletos += item['cantidad']
        total_ventas += float(item['total_ventas'] or 0)
        total_comisiones += float(comision_aerolinea)
        
    return JsonResponse({
        'totales': {
            'total_boletos': total_boletos,
            'total_ventas': total_ventas,
            'total_comisiones': total_comisiones
        },
        'por_aerolinea': por_aerolinea
    })


@csrf_exempt
@require_http_methods(["POST"])
def solicitar_anulacion_api(request):
    """
    API para solicitar anulación de boleto.
    """
    try:
        data = json.loads(request.body)
        boleto_id = data.get('boleto')
        
        # Validar existencia del boleto
        try:
            boleto = BoletoImportado.objects.get(pk=boleto_id)
        except BoletoImportado.DoesNotExist:
            return JsonResponse({'error': 'Boleto no encontrado'}, status=404)
            
        # Crear registro de anulación
        from core.models.anulaciones import AnulacionBoleto
        
        anulacion = AnulacionBoleto.objects.create(
            boleto=boleto,
            tipo_anulacion=data.get('tipo_anulacion', 'VOL'),
            motivo=data.get('motivo', ''),
            monto_original=Decimal(str(data.get('monto_original', 0))),
            penalidad_aerolinea=Decimal(str(data.get('penalidad_aerolinea', 0))),
            fee_agencia=Decimal(str(data.get('fee_agencia', 0))),
            solicitado_por=request.user if request.user.is_authenticated else None
        )
        
        return JsonResponse({
            'status': 'success',
            'id_anulacion': anulacion.id_anulacion,
            'monto_reembolso': float(anulacion.monto_reembolso)
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
