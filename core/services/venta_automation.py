import logging
import json
logger = logging.getLogger(__name__)
from decimal import Decimal
from django.db import transaction
from django.utils import timezone

# Modelos del Core

from core.models_catalogos import Ciudad, Moneda, ProductoServicio, Proveedor
from core.models.tarifario_hoteles import TarifarioProveedor
from apps.crm.models import Cliente, Pasajero
from apps.bookings.models import Venta, BoletoImportado, ItemVenta, SegmentoVuelo

class VentaAutomationService:
    
    @classmethod
    def crear_venta_desde_parser(cls, parsed_data, agencia, usuario=None, proveedor_id=None):
        """
        Crea una venta calculando automáticamente la deuda con la Consolidadora (Nivel 4).
        
        Args:
            parsed_data: Diccionario con datos del parser (Unified Parser).
            agencia: Tu agencia.
            proveedor_id: ID del consolidador (seleccionado en el frontend o detectado).
        """
        # 0. Normalización de entrada
        data = parsed_data
        if hasattr(parsed_data, 'to_dict'):
            data = parsed_data.to_dict()
        elif not isinstance(data, dict):
            # Si es un objeto genérico, intentamos convertirlo
             try: data = vars(parsed_data)
             except: data = {}

        # 1. Extracción Financiera (Soporte Multi-Formato)
        financials = data.get('tarifas') or data.get('fares') or {}
        
        # Fallback para formato Legacy KIU que no tiene 'tarifas' anidado
        if not financials and 'TOTAL_IMPORTE' in data:
            financials = {
                'fare_amount': data.get('TARIFA_IMPORTE', '0.00'),
                'total_amount': data.get('TOTAL_IMPORTE', '0.00'),
                'currency': data.get('TOTAL_MONEDA', 'USD'),
                'tax_details': {}
            }

        tax_details = financials.get('tax_details', {})
        
        monto_base = Decimal(str(financials.get('fare_amount') or 0))
        monto_total = Decimal(str(financials.get('total_amount') or 0))
        monto_iva_yn = Decimal(str(tax_details.get('iva_yn') or 0))
        monto_otros_tax = Decimal(str(tax_details.get('other_taxes') or 0))
        
        # Moneda
        codigo_moneda = financials.get('currency', 'USD')
        # Corrección rápida para monedas extrañas o vacías
        if not codigo_moneda or len(codigo_moneda) != 3: codigo_moneda = 'USD'

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
                    # Cálculo: Ganancia = Total * % Comisión
                    comision_monto = monto_total * (porcentaje_comision / 100)
                    # Cálculo: Deuda = Total - Ganancia
                    costo_neto_pagar = monto_total - comision_monto
                    
            except Proveedor.DoesNotExist:
                pass

        # 3. Guardado en Base de Datos
        with transaction.atomic():
            
            # A. Cliente (Búsqueda inteligente o creación)
            # Extracción robusta del nombre
            nombre_pax = "PASAJERO DESCONOCIDO"
            if 'passenger_name' in data:
                nombre_pax = data['passenger_name']
            elif 'pasajero' in data:
                pasajero_field = data['pasajero']
                if isinstance(pasajero_field, dict):
                    nombre_pax = pasajero_field.get('nombre_completo', '')
                else:
                    nombre_pax = str(pasajero_field)
            elif 'NOMBRE_DEL_PASAJERO' in data:
                nombre_pax = data['NOMBRE_DEL_PASAJERO']

            # Limpiar nombre para búsqueda
            nombre_search = nombre_pax.split('/')[0] if '/' in nombre_pax else nombre_pax
            
            # Blindaje Multi-tenant: Filtrar búsqueda por agencia
            cliente = Cliente.objects.filter(agencia=agencia, nombres__icontains=nombre_search).first()
            if not cliente:
                 cliente = Cliente.objects.create(
                    agencia=agencia,
                    nombres=nombre_pax,
                    apellidos='.',
                    tipo_cliente='IND'
                )

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
            # (Aquí se podría agregar lógica de parsing de fecha si se necesitara precisión exacta)

            # B. Venta (Cabecera) - Lógica de Idempotencia y Auto-Healing
            pnr = data.get('pnr') or data.get('CODIGO_RESERVA') or data.get('localizador') or "SIN-PNR"
            
            try:
                with transaction.atomic():
                    venta, created = Venta.objects.get_or_create(
                        agencia=agencia,
                        localizador=pnr,
                        defaults={
                            'cliente': cliente,
                            'creado_por': usuario,
                            'moneda': moneda_obj,
                            'fecha_venta': timezone.now(),
                            'estado': Venta.EstadoVenta.PENDIENTE_PAGO,
                            'tipo_venta': Venta.TipoVenta.B2C,
                            'canal_origen': Venta.CanalOrigen.IMPORTACION,
                            'subtotal': monto_base,
                            'impuestos': monto_iva_yn + monto_otros_tax,
                            'total_venta': monto_total,
                            'saldo_pendiente': monto_total,
                            'descripcion_general': f"Emisión {aerolinea} - Pax: {nombre_pax}"
                        }
                    )
            except Exception: # Colisión de PNR o Soft Delete
                # Buscar en la papelera (Soft Delete)
                manager = getattr(Venta, 'all_objects', Venta.objects)
                venta = manager.filter(agencia=agencia, localizador=pnr).first()
                created = False
                
                if venta:
                    # Restaurar si estaba borrado
                    if hasattr(venta, 'deleted_at') and venta.deleted_at:
                        venta.deleted_at = None
                        venta.save(update_fields=['deleted_at'])
                        logger.info(f"🧟♂️ Venta {pnr} recuperada de la papelera.")
                else:
                    # Si realmente no existe, algo falló gravemente en la integridad
                    raise

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

            # D. Item Venta
            producto_servicio, _ = ProductoServicio.objects.get_or_create(
                nombre="Boleto Aéreo Internacional",
                defaults={'tipo_producto': 'AIR'}
            )

            ItemVenta.objects.create(
                agencia=agencia,
                venta=venta,
                producto_servicio=producto_servicio,
                descripcion_personalizada=f"Boleto {ticket_num} ({aerolinea})",
                cantidad=1,
                
                # Precio al Cliente
                precio_unitario_venta=monto_total,
                impuestos_item_venta=0, 
                subtotal_item_venta=monto_total,
                total_item_venta=monto_total,
                
                # --- DATOS DE RENTABILIDAD (NIVEL 4) ---
                proveedor_servicio=proveedor_obj,
                costo_neto_proveedor=costo_neto_pagar, 
                comision_agencia_monto=comision_monto,
                
                estado_item=ItemVenta.EstadoItemVenta.CONFIRMADO
            )

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
                    # Extraer ciudades (Búsqueda por código IATA si el parser lo da)
                    # El parser suele dar "BOGOTA, COLOMBIA" o "MADRID, SPAIN"
                    # Por ahora creamos el segmento con el texto raw o buscamos ciudad si es posible
                    dep_loc = seg.get('departure', {}).get('location', 'N/A')
                    arr_loc = seg.get('arrival', {}).get('location', 'N/A')
                    
                    # Intentar buscar ciudades por nombre simple
                    ciudad_dep = Ciudad.objects.filter(nombre__icontains=dep_loc.split(',')[0]).first()
                    ciudad_arr = Ciudad.objects.filter(nombre__icontains=arr_loc.split(',')[0]).first()

                    # 🛡️ FALLBACK: Si no existe, buscamos la primera ciudad.
                    # El DB constraint exige NOT NULL aunque el modelo diga Null=True.
                    if not ciudad_dep:
                        ciudad_dep = Ciudad.objects.first()
                        if not ciudad_dep:
                            # 🚨 EMERGENCIA: Creamos una ciudad base si el catálogo está vacío
                            ciudad_dep, _ = Ciudad.objects.get_or_create(nombre="CIUDAD DESCONOCIDA")
                    
                    if not ciudad_arr:
                        ciudad_arr = Ciudad.objects.first()
                        if not ciudad_arr:
                            ciudad_arr, _ = Ciudad.objects.get_or_create(nombre="CIUDAD DESCONOCIDA")
                    
                    SegmentoVuelo.objects.create(
                        agencia=agencia,
                        venta=venta,
                        origen=ciudad_dep,
                        destino=ciudad_arr,
                        aerolinea=seg.get('airline') or seg.get('aerolinea') or aerolinea,
                        numero_vuelo=str(seg.get('vuelo') or seg.get('flightNumber') or seg.get('flight_number') or "N/A"),
                        clase_reserva=str(seg.get('details', {}).get('cabin') or seg.get('clase') or 'Y')[:5],
                        fecha_salida=self._parse_seg_date(seg.get('fecha_salida') or seg.get('date')),
                        fecha_llegada=self._parse_seg_date(seg.get('fecha_llegada')),
                    )
                except Exception as seg_err:
                    print(f"Error procesando segmento de vuelo: {seg_err}")

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