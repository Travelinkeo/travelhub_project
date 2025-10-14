
import logging
from decimal import Decimal

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.db import transaction

from core.models.boletos import BoletoImportado
from core.models.ventas import Venta, ItemVenta, PagoVenta
from core.models_catalogos import Moneda, ProductoServicio
from personas.models import Pasajero
from core.notification_service import (
    notificar_confirmacion_venta,
    notificar_cambio_estado,
    notificar_confirmacion_pago
)

logger = logging.getLogger(__name__)

@receiver(post_save, sender=BoletoImportado)
def crear_o_actualizar_venta_desde_boleto(sender, instance, created, **kwargs):
    """
    Señal que se dispara después de guardar un BoletoImportado para crear o actualizar
    una Venta basada en el localizador del boleto.
    Es compatible con datos normalizados (sub-diccionario 'normalized') y datos planos.
    """
    # Evitar recursión si solo estamos actualizando la venta_asociada
    update_fields = kwargs.get('update_fields') or set()
    if 'venta_asociada' in update_fields and len(update_fields) == 1:
        return

    # --- Guardias de seguridad ---
    if instance.venta_asociada:
        logger.info(f"BoletoImportado {instance.pk} ya tiene una venta asociada ({instance.venta_asociada_id}). No se hace nada.")
        return

    if not instance.datos_parseados:
        logger.info(f"BoletoImportado {instance.pk} no tiene datos parseados. No se puede crear venta.")
        return

    # --- Lógica de Aplanamiento de Datos ---
    # Si existe la clave 'normalized', la usamos. Si no, usamos el diccionario principal.
    if 'normalized' in instance.datos_parseados:
        data = instance.datos_parseados['normalized']
    else:
        data = instance.datos_parseados

    # --- Mapeo de Campos (con fallbacks para KIU y Sabre) ---
    localizador = data.get('reservation_code') or data.get('SOLO_CODIGO_RESERVA')
    
    if not localizador:
        logger.warning(f"BoletoImportado {instance.pk} no tiene un código de reserva válido.")
        return

    pasajero_nombre_completo = data.get('passenger_name') or data.get('NOMBRE_DEL_PASAJERO') or ''
    total_str = str(data.get('total_amount') or data.get('TOTAL_IMPORTE') or '0.00')
    moneda_iso = data.get('total_currency') or data.get('TOTAL_MONEDA') or 'USD'
    aerolinea = data.get('airline_name') or data.get('NOMBRE_AEROLINEA') or 'N/A'
    numero_documento = data.get('passenger_document') or data.get('CODIGO_IDENTIFICACION')

    with transaction.atomic():
        try:
            # --- 1. Buscar o crear el Pasajero ---
            nombres, apellidos = '', ''
            if pasajero_nombre_completo:
                parts = pasajero_nombre_completo.split('/')
                if len(parts) > 1:
                    apellidos, nombres = parts[0].strip(), parts[1].strip()
                else:
                    apellidos = pasajero_nombre_completo.strip()
            
            if not numero_documento:
                # Fallback para crear un ID único si no viene en el boleto
                doc_fallback = f"NN-{apellidos.replace(' ', '')}-{nombres.replace(' ', '')}".upper()
                numero_documento = doc_fallback

            pasajero, _ = Pasajero.objects.get_or_create(
                numero_documento=numero_documento,
                defaults={'nombres': nombres, 'apellidos': apellidos}
            )

            # --- 2. Buscar o crear la Venta ---
            moneda, _ = Moneda.objects.get_or_create(codigo_iso=moneda_iso, defaults={'nombre': f"Moneda {moneda_iso}"})

            venta, venta_creada = Venta.objects.get_or_create(
                localizador=localizador,
                defaults={
                    'cliente': None,
                    'moneda': moneda,
                    'canal_origen': Venta.CanalOrigen.IMPORTACION,
                    'descripcion_general': f"Venta importada desde boleto con localizador {localizador}"
                }
            )

            if not venta_creada and venta.moneda != moneda:
                logger.warning(f"Conflicto de moneda para Venta {venta.pk}. Se mantiene la moneda original {venta.moneda.codigo_iso}.")
            
            venta.pasajeros.add(pasajero)

            # --- 3. Buscar el Producto/Servicio "Boleto Aéreo" ---
            producto_boleto, _ = ProductoServicio.objects.get_or_create(
                nombre='Boleto Aéreo',
                defaults={'descripcion': 'Servicio de transporte aéreo.', 'tipo_producto': 'SER'}
            )

            # --- 4. Crear el ItemVenta ---
            total_boleto = Decimal(total_str)
            
            ItemVenta.objects.create(
                venta=venta,
                producto_servicio=producto_boleto,
                descripcion_personalizada=f"Boleto aéreo {numero_boleto} para {pasajero_nombre_completo} ({aerolinea})",
                cantidad=1,
                precio_unitario_venta=total_boleto,
            )

            # --- 5. Asociar el boleto a la venta ---
            instance.venta_asociada = venta
            instance.save(update_fields=['venta_asociada'])

            logger.info(f"Procesado BoletoImportado {instance.pk}. Venta {venta.pk} (localizador: {localizador}) creada/actualizada.")

        except Exception as e:
            logger.error(f"Error en la señal para BoletoImportado {instance.pk}: {e}", exc_info=True)


@receiver(pre_save, sender=Venta)
def capturar_estado_anterior_venta(sender, instance, **kwargs):
    """Captura el estado anterior antes de guardar para detectar cambios"""
    if instance.pk:
        try:
            instance._estado_anterior = Venta.objects.get(pk=instance.pk).estado
        except Venta.DoesNotExist:
            instance._estado_anterior = None
    else:
        instance._estado_anterior = None


@receiver(post_save, sender=Venta)
def enviar_notificaciones_venta(sender, instance, created, **kwargs):
    """Envía notificaciones automáticas según eventos de la venta"""
    # Evitar envío en operaciones masivas o migraciones
    if kwargs.get('raw', False):
        return
    
    if created:
        # Nueva venta creada
        notificar_confirmacion_venta(instance)
    else:
        # Venta actualizada - verificar cambio de estado
        estado_anterior = getattr(instance, '_estado_anterior', None)
        if estado_anterior and estado_anterior != instance.estado:
            notificar_cambio_estado(instance, estado_anterior)


@receiver(post_save, sender=PagoVenta)
def enviar_confirmacion_pago_recibido(sender, instance, created, **kwargs):
    """Envía notificación de confirmación cuando se registra un pago"""
    if kwargs.get('raw', False):
        return
    
    if created and instance.confirmado:
        notificar_confirmacion_pago(instance)

