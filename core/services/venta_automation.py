# core/services/venta_automation.py
from decimal import Decimal
from django.db import transaction
from django.utils import timezone

# Modelos del Core
from core.models import (
    Venta, 
    BoletoImportado, 
    ItemVenta
)
from core.models_catalogos import Moneda, ProductoServicio, Proveedor
from core.models.tarifario_hoteles import TarifarioProveedor
from apps.crm.models import Cliente

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
            
            cliente, _ = Cliente.objects.get_or_create(
                nombres__icontains=nombre_search, 
                defaults={
                    'nombres': nombre_pax,
                    'apellidos': '.', 
                    'tipo_cliente': Cliente.TipoCliente.PARTICULAR
                }
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

            # B. Venta (Cabecera)
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
                
                # Totales para el CLIENTE (Paga full)
                subtotal=monto_base,
                impuestos=monto_iva_yn + monto_otros_tax,
                total_venta=monto_total,
                saldo_pendiente=monto_total,
                
                descripcion_general=f"Emisión {aerolinea} - Pax: {nombre_pax}"
            )

            # C. Boleto Importado (El PDF procesado)
            boleto_obj, _ = BoletoImportado.objects.get_or_create(
                numero_boleto=ticket_num,
                defaults={'agencia': agencia}
            )
            
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
                defaults={'tipo': 'SERV'}
            )

            ItemVenta.objects.create(
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

            return venta