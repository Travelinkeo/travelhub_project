import logging
import json
logger = logging.getLogger(__name__)
from decimal import Decimal
from django.db import models, transaction
from django.utils import timezone

# Modelos del Core

from core.models_catalogos import Ciudad, Moneda, ProductoServicio, Proveedor
from core.models.tarifario_hoteles import TarifarioProveedor
from apps.crm.models import Cliente, Pasajero
from apps.bookings.models import Venta, BoletoImportado, ItemVenta, SegmentoVuelo

# SERVICIOS
from core.services.catalog_service import CatalogNormalizationService

class VentaAutomationService:
    
    @classmethod
    def crear_venta_desde_parser(cls, parsed_data, agencia, usuario=None, forced_cliente_id=None, proveedor_id=None, boleto_obj=None):
        """
        Crea o actualiza una venta calculando automáticamente la deuda con la Consolidadora.
        
        Args:
            parsed_data: Diccionario con datos del parser.
            agencia: Instancia de la Agencia.
            usuario: Usuario que realiza la acción.
            forced_cliente_id: ID del cliente forzado (manual).
            proveedor_id: ID del consolidador.
            boleto_obj: La instancia de BoletoImportado (Opcional, pero vital para evitar duplicados).
        """
        # 0. Normalización de entrada (🛡️ ESCUDO DE VIBRANIUM)
        data = parsed_data
        
        # Si es un string (JSON), lo parseamos primero
        if isinstance(data, str):
            import json
            try: data = json.loads(data)
            except: data = {}

        if hasattr(data, 'to_dict'):
            data = data.to_dict()
        elif not isinstance(data, dict):
             try: data = vars(data)
             except: data = {}

        # 1. Extracción Financiera (GOD MODE 4.1: Prioridad Manual)
        # Si tenemos el objeto boleto, usamos sus montos porque son los que el usuario auditó en el Buffer.
        if boleto_obj and (boleto_obj.total_boleto or 0) > 0:
            monto_base = boleto_obj.tarifa_base or Decimal(0)
            monto_total = boleto_obj.total_boleto or Decimal(0)
            monto_iva_yn = boleto_obj.impuestos_total_calculado or Decimal(0)
            monto_otros_tax = Decimal(0)
            codigo_moneda = data.get('total_currency') or data.get('moneda') or 'USD'
            logger.info(f"💰 Usando montos MANUALES del Boleto {boleto_obj.pk}: Total {monto_total}")
        else:
            # Fallback a la extracción desde el diccionario (IA/Regex)
            monto_base = Decimal(str(data.get('tarifa') or data.get('fare_amount') or 0))
            monto_total = Decimal(str(data.get('total') or data.get('total_amount') or 0))
            monto_iva_yn = Decimal(str(data.get('impuestos') or data.get('tax_details', {}).get('iva_yn') or 0))
            monto_otros_tax = Decimal(str(data.get('tax_details', {}).get('other_taxes') or 0))
            codigo_moneda = data.get('moneda') or data.get('total_currency') or 'USD'

        # Corrección rápida para monedas
        codigo_moneda = str(codigo_moneda).strip().upper()
        if not codigo_moneda or len(codigo_moneda) != 3: 
            codigo_moneda = 'USD'

        moneda_obj, _ = Moneda.objects.get_or_create(codigo_iso=codigo_moneda, defaults={'nombre': codigo_moneda})

        # 2. Lógica de Negocio (Agencia Satélite / Nivel 4)
        # Objetivo: Calcular cuánto le debemos al consolidador y cuánto nos queda.
        
        proveedor_obj = None
        porcentaje_comision = Decimal("0.00")
        comision_monto = Decimal("0.00")
        costo_neto_pagar = monto_total # Por defecto, debemos todo si no hay comisión
        
        if proveedor_id:
            try:
                proveedor_obj = Proveedor.objects.get(pk=proveedor_id)
                
                # Buscamos el tarifario activo para este proveedor
                tarifario = TarifarioProveedor.objects.filter(
                    proveedor=proveedor_obj,
                    activo=True,
                    fecha_vigencia_fin__gte=timezone.now().date()
                ).order_by('-fecha_carga').first()
                
                if tarifario:
                    porcentaje_comision = tarifario.comision_estandar
                    
                    # --- NUEVO: Motor de Overrides (Audit Point 3) ---
                    # Buscamos si hay una comisión especial para la aerolínea del boleto
                    nombre_air = data.get('nombre_aerolinea') or data.get('NOMBRE_AEROLINEA')
                    if nombre_air:
                        from core.models_catalogos import Aerolinea
                        from core.models.tarifario_hoteles import ComisionOverrideAerolinea
                        
                        # Búsqueda por nombre o código IATA (Soporte Multi-GDS)
                        air_obj = Aerolinea.objects.filter(
                            models.Q(nombre__icontains=nombre_air) | 
                            models.Q(codigo_iata__icontains=nombre_air[:2])
                        ).first()
                        
                        if air_obj:
                            override = ComisionOverrideAerolinea.objects.filter(
                                tarifario=tarifario,
                                aerolinea=air_obj
                            ).first()
                            
                            if override:
                                logger.info(f"🎯 Aplicando OVERRIDE de comisión: {override.comision_porcentaje}% para {air_obj.nombre}")
                                porcentaje_comision = override.comision_porcentaje

                    # Cálculo: Ganancia = Total * % Comisión
                    comision_monto = monto_total * (porcentaje_comision / 100)
                    # Cálculo: Deuda = Total - Ganancia
                    costo_neto_pagar = monto_total - comision_monto
                    
            except Proveedor.DoesNotExist:
                pass

        # 3. Guardado en Base de Datos
        with transaction.atomic():
            
            # A. Cliente (Búsqueda inteligente o creación)
            cliente = None
            if forced_cliente_id:
                try:
                    cliente = Cliente.objects.get(pk=forced_cliente_id)
                except Cliente.DoesNotExist:
                    pass

            if not cliente:
                # 1. Búsqueda por Documento (Prioridad Máxima)
                doc_pax = data.get('passenger_document') or data.get('foid') or data.get('CODIGO_IDENTIFICACION')
                
                if doc_pax:
                    import re
                    from hashlib import sha256
                    doc_clean = re.sub(r'[^A-Z0-9]', '', str(doc_pax).upper())
                    doc_hash = sha256(doc_clean.encode()).hexdigest()
                    # Buscar por hash o por texto plano normalizado
                    cliente = Cliente.objects.filter(agencia=agencia).filter(
                        models.Q(documento_hash=doc_hash) | models.Q(cedula_identidad__icontains=doc_clean)
                    ).first()

                # 2. Búsqueda por Nombre (Respaldo)
                if not cliente:
                    nombre_pax = data.get('passenger_name') or "PASAJERO DESCONOCIDO"
                    # Limpiamos nombre (Apellido/Nombre -> Apellido)
                    nombre_search = nombre_pax.split('/')[0].strip() if '/' in nombre_pax else nombre_pax.strip()
                    if len(nombre_search) > 3:
                        cliente = Cliente.objects.filter(agencia=agencia, nombres__icontains=nombre_search).first()
                
                # 3. Creación Atómica
                if not cliente:
                    cliente = Cliente.objects.create(
                        agencia=agencia,
                        nombres=data.get('passenger_name') or "PASAJERO",
                        apellidos='(Auto-Generado)',
                        tipo_cliente='IND'
                    )
                    if doc_pax:
                        cliente.cedula_identidad = doc_pax
                        import re
                        from hashlib import sha256
                        doc_clean = re.sub(r'[^A-Z0-9]', '', str(doc_pax).upper())
                        cliente.documento_hash = sha256(doc_clean.encode()).hexdigest()
                        cliente.save()
            else:
                nombre_pax = f"{cliente.apellidos}, {cliente.nombres}"

            # Extraer PNR y Ticket
            pnr = data.get('pnr') or data.get('CODIGO_RESERVA') or data.get('localizador') or "SIN-PNR"
            ticket_num = data.get('ticket_number') or data.get('numero_boleto') or data.get('NUMERO_DE_BOLETO') or "SIN-TICKET"
            
            # Extraer Aerolinea
            aerolinea = "N/A"
            raw_data_dict = data.get('raw_data', {}) or {}
            # Si data es plano, raw_data podría no existir o estar mezclado
            if 'NOMBRE_AEROLINEA' in data: aerolinea = data['NOMBRE_AEROLINEA']
            elif 'aerolinea_emisora' in data.get('reserva', {}): aerolinea = data['reserva']['aerolinea_emisora']
            else: aerolinea = raw_data_dict.get('NOMBRE_AEROLINEA', 'Aéreo')

            fecha_emision = timezone.now() # Fallback
            # Intentar parsear fecha issue_date
            issue_date_str = data.get('issue_date') or data.get('fecha_emision') or data.get('FECHA_DE_EMISION')
            # B. Venta (Cabecera) - Lógica de Idempotencia y Protección (Audit Point 1)
            pnr = data.get('pnr') or data.get('CODIGO_RESERVA') or data.get('localizador') or "SIN-PNR"
            
            venta = None
            created = False

            # 🛡️ FIX DUPLICADOS: Prioridad 1 - Relación directa del boleto
            if boleto_obj and boleto_obj.venta_asociada:
                venta = boleto_obj.venta_asociada
                logger.info(f"🔗 Usando venta ya asociada al boleto: ID {venta.pk}")
            
            # Prioridad 2 - Búsqueda por PNR si no hay asociación previa
            if not venta:
                manager = getattr(Venta, 'all_objects', Venta.objects)
                venta_existente = manager.filter(agencia=agencia, localizador=pnr).order_by('-fecha_venta').first()
                
                if venta_existente:
                    # ¿Es un PNR reciclado? 
                    import datetime
                    seis_meses = datetime.timedelta(days=180)
                    es_reciclado = False
                    
                    if (timezone.now() - venta_existente.fecha_venta) > seis_meses:
                        es_reciclado = True
                    elif venta_existente.cliente and cliente and venta_existente.cliente_id != cliente.id:
                        es_reciclado = True
                    
                    if not es_reciclado:
                        venta = venta_existente
                        if hasattr(venta, 'deleted_at') and venta.deleted_at:
                            venta.deleted_at = None
                            venta.save(update_fields=['deleted_at'])

            if not venta:
                # Crear venta nueva
                venta = Venta.objects.create(
                    agencia=agencia,
                    localizador=pnr,
                    cliente=cliente,
                    creado_por=usuario,
                    moneda=moneda_obj,
                    fecha_venta=timezone.now(),
                    estado=Venta.EstadoVenta.PENDIENTE_PAGO,
                    tipo_venta=Venta.TipoVenta.B2C,
                    canal_origen=Venta.CanalOrigen.IMPORTACION,
                    subtotal=monto_base,
                    impuestos=monto_iva_yn + monto_otros_tax,
                    total_venta=monto_total,
                    saldo_pendiente=monto_total,
                    descripcion_general=f"Emisión {aerolinea} - Pax: {nombre_pax}"
                )
                created = True
            else:
                # 🔄 SINCRONIZACIÓN: Si la venta ya existía, actualizamos sus montos totales 
                # para que coincidan con la revisión manual.
                venta.subtotal = monto_base
                venta.impuestos = monto_iva_yn + monto_otros_tax
                venta.total_venta = monto_total
                venta.saldo_pendiente = monto_total # Asumimos que si re-extrae, el pago se re-valida
                venta.save(update_fields=['subtotal', 'impuestos', 'total_venta', 'saldo_pendiente'])

            if not created:
                # Si la venta ya existía, actualizamos el cliente si era huérfano
                if not venta.cliente:
                    venta.cliente = cliente
                    venta.save(update_fields=['cliente'])

            # C. Boleto Importado (El PDF procesado)
            # 🚨 FIX: Usar filter().first() para evitar MultipleObjectsReturned si hay duplicados físicos.
            # Filtrar estrictamente por agencia para seguridad multi-tenant.
            boleto_obj = BoletoImportado.objects.filter(
                agencia=agencia, 
                numero_boleto=ticket_num
            ).order_by('-id_boleto_importado').first() # El más reciente si hay duplicados
            
            if not boleto_obj:
                logger.info(f"🆕 Creando nuevo registro de BoletoImportado para: {ticket_num}")
                boleto_obj = BoletoImportado.objects.create(
                    agencia=agencia,
                    numero_boleto=ticket_num,
                    estado_parseo=BoletoImportado.EstadoParseo.COMPLETADO
                )
            else:
                logger.info(f"♻️ Reutilizando registro de BoletoImportado ID {boleto_obj.pk}")
            
            # Actualizamos datos del boleto
            boleto_obj.venta_asociada = venta
            boleto_obj.localizador_pnr = pnr
            boleto_obj.nombre_pasajero_procesado = nombre_pax
            boleto_obj.aerolinea_emisora = aerolinea
            # boleto_obj.fecha_emision_boleto = ... (requiere objeto fecha)
            
            # Guardamos la data financiera en el boleto también
            boleto_obj.tarifa_base = monto_base
            boleto_obj.impuestos_total_calculado = monto_iva_yn + monto_otros_tax
            boleto_obj.total_boleto = monto_total
            boleto_obj.comision_agencia = comision_monto # Dato informativo
            
            boleto_obj.datos_parseados = data
            boleto_obj.estado_parseo = BoletoImportado.EstadoParseo.COMPLETADO
            boleto_obj.save()

            # D. Item Venta (IDEMPOTENCIA FINANCIERA)
            # Evitamos duplicar cobros/deudas si se re-parsea el mismo boleto en la misma venta.
            producto_servicio, _ = ProductoServicio.objects.get_or_create(
                nombre="Boleto Aéreo Internacional",
                defaults={'tipo_producto': 'AIR'}
            )

            # Buscamos si ya existe un item para este número de boleto en esta venta
            item_existente = ItemVenta.objects.filter(
                venta=venta,
                descripcion_personalizada__icontains=ticket_num
            ).first()

            item_data = {
                'agencia': agencia,
                'venta': venta,
                'producto_servicio': producto_servicio,
                'descripcion_personalizada': f"Boleto {ticket_num} ({aerolinea})",
                'cantidad': 1,
                'precio_unitario_venta': monto_total,
                'impuestos_item_venta': 0, 
                'subtotal_item_venta': monto_total,
                'total_item_venta': monto_total,
                'proveedor_servicio': proveedor_obj,
                'costo_neto_proveedor': costo_neto_pagar, 
                'comision_agencia_monto': comision_monto,
                'estado_item': ItemVenta.EstadoItemVenta.CONFIRMADO
            }

            if item_existente:
                logger.info(f"♻️ Actualizando ItemVenta existente para boleto {ticket_num}")
                for key, value in item_data.items():
                    setattr(item_existente, key, value)
                item_existente.save()
            else:
                ItemVenta.objects.create(**item_data)

            # E. Sincronización de Pasajeros (ManyToManyField)
            pax_obj, _ = Pasajero.objects.get_or_create(
                agencia=agencia,
                nombres=nombre_pax,
                defaults={'apellidos': '.'}
            )
            venta.pasajeros.add(pax_obj)

            # F. Segmentos de Vuelo (Itinerario)
            # Sincronización de llaves: AI (segmentos/itinerario) vs Schema (flights)
            itinerario = data.get('segmentos') or data.get('itinerario') or data.get('flights', [])
            for seg in itinerario:
                try:
                    # 1. Normalización Determinística de Ciudades (Audit Point 1: IATA Master)
                    # El DataNormalizationService ya resolvió los códigos IATA

                    # Prioridad: Campos explícitos del parser -> Extracción de texto
                    iata_dep = seg.get('codigo_iata_origen')
                    iata_arr = seg.get('codigo_iata_destino')

                    ciudad_dep = None
                    ciudad_arr = None

                    if iata_dep:
                        ciudad_dep = CatalogNormalizationService.get_or_create_ciudad_by_iata(iata_dep)
                    if iata_arr:
                        ciudad_arr = CatalogNormalizationService.get_or_create_ciudad_by_iata(iata_arr)

                    # Fallback 2: Por nombre solo si IATA falló (Retrocompatibilidad / Low Cost)
                    if not ciudad_dep:
                        dep_loc = seg.get('origen') or seg.get('departure', {}).get('location') or 'N/A'
                        # Limpiar nombre (Ej: "BOGOTA, COLOMBIA" -> "BOGOTA")
                        clean_name = str(dep_loc).split(',')[0].split('(')[0].strip()
                        ciudad_dep = Ciudad.objects.filter(nombre__icontains=clean_name).first()
                    
                    if not ciudad_arr:
                        arr_loc = seg.get('destino') or seg.get('arrival', {}).get('location') or 'N/A'
                        clean_name = str(arr_loc).split(',')[0].split('(')[0].strip()
                        ciudad_arr = Ciudad.objects.filter(nombre__icontains=clean_name).first()

                    # Sincronización de Segmentos (IDEMPOTENCIA)
                    vuelo_num = str(seg.get('vuelo') or seg.get('flightNumber') or seg.get('flight_number') or "N/A")
                    f_salida = self._parse_seg_date(seg.get('fecha_salida') or seg.get('date'))
                    
                    seg_existente = SegmentoVuelo.objects.filter(
                        venta=venta,
                        numero_vuelo=vuelo_num,
                        fecha_salida=f_salida
                    ).first()

                    seg_data = {
                        'agencia': agencia,
                        'venta': venta,
                        'origen': ciudad_dep,
                        'destino': ciudad_arr,
                        'aerolinea': seg.get('airline') or seg.get('aerolinea') or aerolinea,
                        'numero_vuelo': vuelo_num,
                        'clase_reserva': str(seg.get('details', {}).get('cabin') or seg.get('clase') or 'Y')[:5],
                        'fecha_salida': f_salida,
                        'fecha_llegada': self._parse_seg_date(seg.get('fecha_llegada')),
                    }

                    if seg_existente:
                        for key, value in seg_data.items():
                            setattr(seg_existente, key, value)
                        seg_existente.save()
                    else:
                        SegmentoVuelo.objects.create(**seg_data)

                except Exception as seg_err:
                    logger.error(f"Error procesando segmento de vuelo: {seg_err}")

            # 7. INTELIGENCIA DE VENTAS (IA PROACTIVA)
            try:
                from core.services.sales_intelligence_service import SalesIntelligenceService
                ai_report = SalesIntelligenceService.analyze_booking_for_upselling(data, agencia=agencia)
                if ai_report:
                    # Guardar reporte estructurado en las notas de la venta
                    # Nota: ai_report es el resultado de ai_engine.parse_structured_data (un dict o Schema)
                    report_dict = ai_report if isinstance(ai_report, dict) else ai_report.dict()
                    
                    if not venta.notas:
                        venta.notas = ""
                    
                    summary = report_dict.get('summary', 'Estrategia generada con éxito.')
                    venta.notas += f"\n\n[IA SALES REPORT]\n{summary}\n"
                    
                    # Log de auditoría silente
                    logger.info(f"✨ Inteligencia de ventas adjuntada a Venta {venta.pk}")
                    
                venta.save(update_fields=['notas'])
            except Exception as ei:
                logger.error(f"Error generando inteligencia de ventas: {ei}")

        return venta

    @classmethod
    def _parse_seg_date(cls, date_str):
        if not date_str:
            return None
        from core.ticket_parser import _parse_date_robust
        return _parse_date_robust(str(date_str))