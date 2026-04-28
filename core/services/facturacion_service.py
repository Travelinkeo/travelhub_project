
import logging
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
# from core.models.facturacion import Factura, ItemFactura (MOVED)
from apps.finance.models import Factura, ItemFactura
from apps.bookings.models import Venta
from apps.bookings.models import BoletoImportado

logger = logging.getLogger(__name__)

class FacturacionService:
    """
    Servicio para la generación y gestión de facturas fiscales.
    Centraliza la lógica de cálculo de impuestos venezolanos (IVA, INATUR, IGTF).
    """

    @staticmethod
    @transaction.atomic
    def generar_factura_desde_venta(venta: Venta, cliente=None) -> Factura:
        """
        Genera una Factura Fiscal a partir de una Venta.
        Utiliza la inteligencia fiscal de BoletoImportado si existe.
        
        Args:
            venta: Instancia de Venta.
            cliente: (Opcional) Cliente a asignar. Si es None, usa venta.cliente.
            
        Returns:
            Factura creada.
        """
        cliente_final = cliente or venta.cliente
        if not cliente_final:
            raise ValueError("La venta debe tener un cliente asignado para facturar.")

        # 1. Buscar Datos Fiscales del Boleto (Si aplica)
        boleto = BoletoImportado.objects.filter(venta_asociada=venta).first()
        
        datos_fiscales = {
            'iva_monto': Decimal('0.00'),
            'inatur_monto': Decimal('0.00'),
            'base_imponible': Decimal('0.00'),
            'base_exenta': Decimal('0.00'),
            'monto_impuestos': Decimal('0.00'),
            'subtotal': Decimal('0.00'),
            'monto_total': Decimal('0.00')
        }
        
        items_a_crear = []
        
        if boleto and boleto.datos_parseados:
            # --- MODELO INTELIGENTE (BOLETO PARSEADO) ---
            logger.info(f"Generando factura inteligente para Venta {venta.id_venta} desde Boleto {boleto.numero_boleto}")
            
            # Extraer montos del boleto
            tarifa_base = boleto.tarifa_base or Decimal('0.00')
            fee_servicio = boleto.fee_servicio or Decimal('0.00') # Si existe fee separado
            otros_impuestos = boleto.otros_impuestos_monto or Decimal('0.00')
            iva_monto = boleto.iva_monto or Decimal('0.00')
            inatur_monto = boleto.inatur_monto or Decimal('0.00')
            
            # Lógica de asignación
            # Base Gravada = Tarifa Base (+ Fee si aplica y es gravado)
            base_gravada = tarifa_base 
            
            # Base Exenta = Otros Impuestos (Tasas)
            base_exenta = otros_impuestos
            
            # Item 1: Boleto Aéreo (Gravado)
            items_a_crear.append({
                'descripcion': f"Emisión Boleto Aéreo {boleto.aerolinea_emisora or ''} Ruta: {boleto.ruta_vuelo or ''}",
                'cantidad': 1,
                'precio_unitario': base_gravada,
                'tipo_impuesto': ItemFactura.TipoImpuesto.IVA_16 if iva_monto > 0 else ItemFactura.TipoImpuesto.EXENTO,
                'subtotal': base_gravada
            })
            
            # Item 2: Tasas e Impuestos Aeroportuarios (Exento)
            if base_exenta > 0:
                items_a_crear.append({
                    'descripcion': f"Tasas e Impuestos Aeroportuarios Boleto {boleto.numero_boleto}",
                    'cantidad': 1,
                    'precio_unitario': base_exenta,
                    'tipo_impuesto': ItemFactura.TipoImpuesto.EXENTO,
                    'subtotal': base_exenta
                })
                
            # Totales Fiscales (Forzamos los del boleto para exactitud)
            datos_fiscales['base_imponible'] = base_gravada
            datos_fiscales['base_exenta'] = base_exenta
            datos_fiscales['iva_monto'] = iva_monto
            datos_fiscales['inatur_monto'] = inatur_monto
            datos_fiscales['monto_impuestos'] = iva_monto + inatur_monto
            datos_fiscales['subtotal'] = base_gravada + base_exenta
            datos_fiscales['monto_total'] = datos_fiscales['subtotal'] + datos_fiscales['monto_impuestos']

        else:
            # --- MODELO GENÉRICO (VENTA MANUAL) ---
            logger.info(f"Generando factura genérica para Venta {venta.id_venta}")
            
            # Asumimos todo gravado por defecto si no hay info contraria
            subtotal_venta = venta.subtotal
            impuestos_venta = venta.impuestos
            
            base_gravada = subtotal_venta
            iva_calculado = base_gravada * Decimal('0.16')
            
            # Ajuste simple: Si la diferencia de impuestos es pequeña, asumimos que es correcto
            # Si impuestos_venta es muy diferente al 16% de subtotal, algo pasa (quizas hay exentos).
            
            items_a_crear.append({
                'descripcion': "Servicios Turísticos",
                'cantidad': 1,
                'precio_unitario': subtotal_venta,
                'tipo_impuesto': ItemFactura.TipoImpuesto.IVA_16,
                'subtotal': subtotal_venta
            })
            
            datos_fiscales['base_imponible'] = subtotal_venta
            datos_fiscales['iva_monto'] = impuestos_venta # Usamos el total de impuestos de la venta como IVA
            datos_fiscales['monto_impuestos'] = impuestos_venta
            datos_fiscales['subtotal'] = subtotal_venta
            datos_fiscales['monto_total'] = venta.total_venta

        # 2. Crear Cabecera de Factura
        factura = Factura.objects.create(
            cliente=cliente_final,
            venta_asociada=venta,
            moneda=venta.moneda,
            fecha_emision=timezone.now().date(),
            
            # Datos Cliente Snapshot
            cliente_nombre=f"{cliente_final.nombres} {cliente_final.apellidos}",
            cliente_rif=cliente_final.numero_documento or '',
            cliente_direccion=cliente_final.direccion or '',
            cliente_telefono=cliente_final.telefono or '',
            
            # Valores Fiscales Iniciales
            base_imponible=datos_fiscales['base_imponible'],
            base_exenta=datos_fiscales['base_exenta'],
            iva_monto=datos_fiscales['iva_monto'],
            inatur_monto=datos_fiscales['inatur_monto'],
            monto_impuestos=datos_fiscales['monto_impuestos'],
            subtotal=datos_fiscales['subtotal'],
            monto_total=datos_fiscales['monto_total'],
            saldo_pendiente=datos_fiscales['monto_total'],
            
            estado=Factura.EstadoFactura.BORRADOR # Siempre nace como borrador para revisión
        )
        
        # 3. Crear Items
        for item_data in items_a_crear:
            ItemFactura.objects.create(
                factura=factura,
                descripcion=item_data['descripcion'],
                cantidad=item_data['cantidad'],
                precio_unitario=item_data['precio_unitario'],
                tipo_impuesto=item_data['tipo_impuesto'],
                subtotal_item=item_data['subtotal']
            )
            
        # 4. Enlazar Venta
        venta.factura = factura
        venta.save(update_fields=['factura'])
        
        logger.info(f"Factura {factura.numero_factura} creada exitosamente (ID: {factura.pk})")
        return factura
