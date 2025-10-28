"""
Servicio de integración contable para facturas consolidadas.
Genera asientos contables automáticos según normativa VEN-NIF.
"""

from decimal import Decimal
from django.db import transaction
from contabilidad.models import AsientoContable, DetalleAsiento, CuentaContable
import logging

logger = logging.getLogger(__name__)


def generar_asiento_factura(factura):
    """
    Genera asiento contable automático para una factura consolidada.
    
    Asiento tipo:
    DEBE:
        - Cuentas por Cobrar Clientes (monto_total)
    HABER:
        - Ingresos por Ventas (subtotal_base_gravada + subtotal_exento)
        - IVA por Pagar (monto_iva_16 + monto_iva_adicional)
        - IGTF por Pagar (monto_igtf)
    
    Args:
        factura: Instancia de FacturaConsolidada
        
    Returns:
        AsientoContable: Asiento generado
    """
    try:
        with transaction.atomic():
            # Crear asiento contable
            asiento = AsientoContable.objects.create(
                tipo_asiento='VENTA',
                fecha=factura.fecha_emision,
                descripcion=f"Factura {factura.numero_factura} - {factura.cliente.nombres} {factura.cliente.apellidos}",
                moneda=factura.moneda,
                tasa_cambio=factura.tasa_cambio_bcv or Decimal('1.00'),
                referencia=factura.numero_factura,
                estado='BORRADOR'
            )
            
            # DEBE: Cuentas por Cobrar
            cuenta_cxc = CuentaContable.objects.filter(
                codigo__startswith='1.1.2',  # Cuentas por Cobrar
                activa=True
            ).first()
            
            if cuenta_cxc:
                DetalleAsiento.objects.create(
                    asiento=asiento,
                    cuenta=cuenta_cxc,
                    tipo_movimiento='DEBE',
                    monto=factura.monto_total,
                    descripcion=f"CxC Cliente {factura.cliente.nombres}"
                )
            
            # HABER: Ingresos por Ventas
            cuenta_ingresos = CuentaContable.objects.filter(
                codigo__startswith='4.1',  # Ingresos
                activa=True
            ).first()
            
            if cuenta_ingresos:
                monto_ingresos = factura.subtotal_base_gravada + factura.subtotal_exento + factura.subtotal_exportacion
                if monto_ingresos > 0:
                    DetalleAsiento.objects.create(
                        asiento=asiento,
                        cuenta=cuenta_ingresos,
                        tipo_movimiento='HABER',
                        monto=monto_ingresos,
                        descripcion=f"Ingresos Factura {factura.numero_factura}"
                    )
            
            # HABER: IVA por Pagar
            if factura.monto_iva_16 > 0 or factura.monto_iva_adicional > 0:
                cuenta_iva = CuentaContable.objects.filter(
                    codigo__startswith='2.1.4',  # IVA por Pagar
                    activa=True
                ).first()
                
                if cuenta_iva:
                    monto_iva_total = factura.monto_iva_16 + factura.monto_iva_adicional
                    DetalleAsiento.objects.create(
                        asiento=asiento,
                        cuenta=cuenta_iva,
                        tipo_movimiento='HABER',
                        monto=monto_iva_total,
                        descripcion=f"IVA 16% Factura {factura.numero_factura}"
                    )
            
            # HABER: IGTF por Pagar
            if factura.monto_igtf > 0:
                cuenta_igtf = CuentaContable.objects.filter(
                    codigo__startswith='2.1.5',  # IGTF por Pagar
                    activa=True
                ).first()
                
                if cuenta_igtf:
                    DetalleAsiento.objects.create(
                        asiento=asiento,
                        cuenta=cuenta_igtf,
                        tipo_movimiento='HABER',
                        monto=factura.monto_igtf,
                        descripcion=f"IGTF 3% Factura {factura.numero_factura}"
                    )
            
            # Actualizar factura con asiento
            factura.asiento_contable_factura = asiento
            factura.save(update_fields=['asiento_contable_factura'])
            
            logger.info(f"Asiento contable generado: {asiento.id} para factura {factura.numero_factura}")
            return asiento
            
    except Exception as e:
        logger.error(f"Error generando asiento para factura {factura.numero_factura}: {str(e)}")
        raise


def contabilizar_factura(factura):
    """
    Genera y contabiliza (aprueba) el asiento de la factura.
    
    Args:
        factura: Instancia de FacturaConsolidada
        
    Returns:
        bool: True si se contabilizó exitosamente
    """
    try:
        # Generar asiento si no existe
        if not factura.asiento_contable_factura:
            asiento = generar_asiento_factura(factura)
        else:
            asiento = factura.asiento_contable_factura
        
        # Aprobar asiento
        if asiento.estado == 'BORRADOR':
            asiento.estado = 'APROBADO'
            asiento.save()
            logger.info(f"Asiento {asiento.id} aprobado para factura {factura.numero_factura}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error contabilizando factura {factura.numero_factura}: {str(e)}")
        return False
