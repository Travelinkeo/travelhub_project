# core/services/doble_facturacion.py
"""
Servicio de Doble Facturación Automática
Genera factura por cuenta de terceros + factura por servicios propios
"""
import logging
from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from core.models import FacturaConsolidada, ItemFacturaConsolidada, Venta

logger = logging.getLogger(__name__)


class DobleFacturacionService:
    """Servicio para generar doble facturación automática"""
    
    @staticmethod
    @transaction.atomic
    def generar_facturas_venta(venta, datos_tercero=None, fee_servicio=None):
        """
        Genera dos facturas para una venta:
        1. Factura por cuenta de terceros (costo del servicio)
        2. Factura por servicios propios (fee de la agencia)
        
        Args:
            venta: Instancia de Venta
            datos_tercero: dict con {
                'razon_social': str,
                'rif': str,
                'monto_servicio': Decimal,
                'descripcion': str,
                'es_nacional': bool (True para nacional, False para internacional)
            }
            fee_servicio: Decimal - Fee de la agencia
        
        Returns:
            tuple: (factura_tercero, factura_propia)
        """
        if not datos_tercero or not fee_servicio:
            raise ValueError("Se requieren datos_tercero y fee_servicio")
        
        agencia = venta.agencia
        cliente = venta.cliente
        moneda = venta.moneda
        tasa_bcv = venta.tasa_cambio_bcv
        
        # 1. FACTURA POR CUENTA DE TERCEROS
        factura_tercero = FacturaConsolidada.objects.create(
            venta_asociada=venta,
            cliente=cliente,
            moneda=moneda,
            tipo_operacion=FacturaConsolidada.TipoOperacion.INTERMEDIACION,
            moneda_operacion=FacturaConsolidada.MonedaOperacion.DIVISA,
            tasa_cambio_bcv=tasa_bcv,
            
            # Emisor (agencia)
            emisor_rif=agencia.rif,
            emisor_razon_social=agencia.nombre,
            emisor_direccion_fiscal=agencia.direccion,
            es_sujeto_pasivo_especial=agencia.es_sujeto_pasivo_especial,
            esta_inscrita_rtn=agencia.esta_inscrita_rtn,
            
            # Cliente
            cliente_es_residente=True,
            cliente_identificacion=cliente.cedula_identidad or cliente.rif,
            cliente_direccion=cliente.direccion or '',
            
            # Tercero
            tercero_rif=datos_tercero['rif'],
            tercero_razon_social=datos_tercero['razon_social'],
            
            # Bases (el monto del servicio va como exento para la agencia)
            subtotal_exento=datos_tercero['monto_servicio'],
            
            estado=FacturaConsolidada.EstadoFactura.EMITIDA
        )
        
        # Item de la factura de tercero
        ItemFacturaConsolidada.objects.create(
            factura=factura_tercero,
            descripcion=datos_tercero['descripcion'],
            cantidad=1,
            precio_unitario=datos_tercero['monto_servicio'],
            tipo_servicio=ItemFacturaConsolidada.TipoServicio.TRANSPORTE_AEREO_NACIONAL,
            es_gravado=False
        )
        
        # 2. FACTURA POR SERVICIOS PROPIOS
        es_nacional = datos_tercero.get('es_nacional', True)
        
        if es_nacional:
            # Servicio nacional: 100% gravado
            base_gravada = fee_servicio
            base_no_sujeta = Decimal('0.00')
        else:
            # Servicio internacional: 20% gravado, 80% no sujeto
            base_gravada = fee_servicio * Decimal('0.20')
            base_no_sujeta = fee_servicio * Decimal('0.80')
        
        iva_16 = base_gravada * Decimal('0.16')
        
        factura_propia = FacturaConsolidada.objects.create(
            venta_asociada=venta,
            cliente=cliente,
            moneda=moneda,
            tipo_operacion=FacturaConsolidada.TipoOperacion.INTERMEDIACION,
            moneda_operacion=FacturaConsolidada.MonedaOperacion.DIVISA,
            tasa_cambio_bcv=tasa_bcv,
            
            # Emisor (agencia)
            emisor_rif=agencia.rif,
            emisor_razon_social=agencia.nombre,
            emisor_direccion_fiscal=agencia.direccion,
            es_sujeto_pasivo_especial=agencia.es_sujeto_pasivo_especial,
            esta_inscrita_rtn=agencia.esta_inscrita_rtn,
            
            # Cliente
            cliente_es_residente=True,
            cliente_identificacion=cliente.cedula_identidad or cliente.rif,
            cliente_direccion=cliente.direccion or '',
            
            # Bases
            subtotal_base_gravada=base_gravada,
            subtotal_exento=base_no_sujeta,
            monto_iva_16=iva_16,
            
            estado=FacturaConsolidada.EstadoFactura.EMITIDA
        )
        
        # Item de la factura propia
        tipo_servicio_desc = "nacional" if es_nacional else "internacional"
        ItemFacturaConsolidada.objects.create(
            factura=factura_propia,
            descripcion=f"Fee por servicio de intermediación {tipo_servicio_desc}",
            cantidad=1,
            precio_unitario=fee_servicio,
            tipo_servicio=ItemFacturaConsolidada.TipoServicio.COMISION_INTERMEDIACION,
            es_gravado=True,
            alicuota_iva=Decimal('16.00')
        )
        
        logger.info(f"Doble facturación generada para venta {venta.id_venta}: "
                   f"Tercero={factura_tercero.numero_factura}, Propia={factura_propia.numero_factura}")
        
        return factura_tercero, factura_propia
    
    @staticmethod
    def generar_desde_boleto(venta, boleto_importado, fee_servicio):
        """
        Genera doble facturación desde un boleto importado
        
        Args:
            venta: Instancia de Venta
            boleto_importado: Instancia de BoletoImportado
            fee_servicio: Decimal - Fee de la agencia
        """
        datos_parseados = boleto_importado.datos_parseados or {}
        normalized = datos_parseados.get('normalized', {})
        
        # Determinar si es nacional o internacional
        itinerario = normalized.get('itinerary', [])
        es_nacional = True
        if itinerario:
            # Si hay vuelos internacionales, es internacional
            for vuelo in itinerario:
                origen = vuelo.get('origin', '')
                destino = vuelo.get('destination', '')
                # Códigos IATA venezolanos comienzan con C (CCS, CZE, MAR, etc.)
                if not (origen.startswith('C') and destino.startswith('C')):
                    es_nacional = False
                    break
        
        datos_tercero = {
            'razon_social': normalized.get('airline_name', 'Aerolínea'),
            'rif': 'J-00000000-0',  # TODO: Obtener RIF real de aerolínea
            'monto_servicio': Decimal(normalized.get('total_amount', '0')),
            'descripcion': f"Boleto aéreo {normalized.get('ticket_number', '')} - Pasajero: {normalized.get('passenger_name', '')}",
            'es_nacional': es_nacional
        }
        
        return DobleFacturacionService.generar_facturas_venta(venta, datos_tercero, fee_servicio)
