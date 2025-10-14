# contabilidad/signals.py
"""
Señales para integración automática Facturación -> Contabilidad.
Se disparan al guardar facturas y pagos para generar asientos contables.
"""

import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

from core.models.facturacion_venezuela import FacturaVenezuela
from core.models.ventas import PagoVenta
from .services import ContabilidadService

logger = logging.getLogger(__name__)


@receiver(post_save, sender=FacturaVenezuela)
def generar_asiento_desde_factura_signal(sender, instance, created, **kwargs):
    """
    Genera asiento contable automáticamente al crear/actualizar una factura.
    Solo se ejecuta si la factura tiene items y está en estado válido.
    """
    if not created:
        return
    
    try:
        # Verificar que la factura tenga items
        if not instance.items_factura.exists():
            logger.debug(f"Factura {instance.numero_factura} sin items, omitiendo asiento")
            return
        
        # Generar asiento contable
        asiento = ContabilidadService.generar_asiento_desde_factura(instance)
        logger.info(f"Asiento {asiento.numero_asiento} generado automáticamente para factura {instance.numero_factura}")
        
    except Exception as e:
        logger.error(f"Error en signal generando asiento para factura {instance.numero_factura}: {e}")


@receiver(post_save, sender=PagoVenta)
def registrar_pago_y_diferencial_signal(sender, instance, created, **kwargs):
    """
    Registra el pago y calcula diferencial cambiario automáticamente.
    Solo se ejecuta para pagos confirmados.
    """
    if not instance.confirmado:
        return
    
    try:
        # Registrar pago con diferencial cambiario
        asiento = ContabilidadService.registrar_pago_y_diferencial(instance)
        
        if asiento:
            logger.info(f"Asiento de pago {asiento.numero_asiento} generado para pago {instance.id_pago_venta}")
        
    except Exception as e:
        logger.error(f"Error en signal registrando pago {instance.id_pago_venta}: {e}")
