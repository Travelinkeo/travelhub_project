import logging

from django.db import transaction
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

# 🔒 PADLOCK: CRITICAL INFRASTRUCTURE
# This file handles the automatic triggering of Ticket Parsing via Celery.
# LOGIC IS LOCKED. DO NOT MODIFY WITHOUT EXPLICIT AUTHORIZATION.
# Maintained by: Antigravity/Gemini
# -----------------------------------------------------
# Models are imported inside receivers to avoid circular dependencies during django.setup()
# from apps.bookings.models import BoletoImportado, Venta, ItemVenta, PagoVenta
# from apps.finance.models import Moneda
# from apps.bookings.models import ProductoServicio
# from apps.crm.models import Pasajero, Cliente 
from apps.communications.services.notification_service import (
    notificar_confirmacion_pago,
)

logger = logging.getLogger(__name__)

@receiver(post_save, sender='bookings.BoletoImportado')
def crear_o_actualizar_venta_desde_boleto(sender, instance, created, **kwargs):
    from apps.bookings.models import BoletoImportado, ItemVenta, ProductoServicio, Venta
    from apps.crm.models import Pasajero
    from apps.finance.models.currencies import Moneda
    """
    Señal que se dispara después de guardar un BoletoImportado para crear o actualizar
    una Venta basada en el localizador del boleto.
    Es compatible con datos normalizados (sub-diccionario 'normalized') y datos planos.
    """
    # Evitar recursión si solo estamos actualizando la venta_asociada
    # Evitar recursión si solo estamos actualizando la venta_asociada
    update_fields = kwargs.get('update_fields') or set()
    if 'venta_asociada' in update_fields and len(update_fields) == 1:
        return

    # --- AUTO-TRIGGER PARSING (Fix Admin Uploads) ---
    # Si se crea un boleto con archivo pero sin datos parseados
    if instance.archivo_boleto and not instance.datos_parseados:
        try:
            # ATOMIC LOCK: Try to update status from PENDIENTE to EN_PROCESO.
            # update() returns the number of rows matched.
            # Only if it was PENDIENTE in the DB effectively, we proceed.
            updated_count = BoletoImportado.objects.filter(
                pk=instance.pk, 
                estado_parseo=BoletoImportado.EstadoParseo.PENDIENTE
            ).update(estado_parseo=BoletoImportado.EstadoParseo.EN_PROCESO)

            if updated_count > 0:
                from core.tasks import parsear_boleto_individual
                logger.info(f"🧩 SIGNAL: Lock adquirido para Boleto {instance.pk}. Disparando Celery...")
                print(f"DEBUG: Triggering process for Boleto {instance.pk} (Lock Acquired)")
                # Direct delay call
                parsear_boleto_individual.delay(instance.pk)
                return 
            else:
                logger.info(f"🧩 SIGNAL: Boleto {instance.pk} ignorado (Ya no está PENDIENTE o Lock falló).")
                
        except Exception as e:
            logger.error(f"Error triggering auto-parse: {e}")
            print(f"DEBUG Error: {e}")

@receiver(post_save, sender='bookings.BoletoImportado')
def post_save_boleto_importado(sender, instance, created, **kwargs):
    """
    Señal para automatizar procesos tras la importación de un boleto.
    Delega la lógica pesada a VentaAutomationService.
    """
    if not instance.datos_parseados or instance.venta_asociada:
        return

    with transaction.atomic():
        try:
            from apps.bookings.services.automation import VentaAutomationService
            venta = VentaAutomationService.process_ticket_import(instance)
            
            if not venta:
                return

            # --- Automatización de Facturación (Opcional) ---
            if instance.formato_detectado and instance.formato_detectado.startswith('EML'):
                try:
                    from apps.finance.services.invoice_service import InvoiceService
                    InvoiceService.create_invoice_from_sale(venta.id_venta)
                except Exception as e_fact:
                    logger.error(f"⚠️ Error en factura automática: {e_fact}")

            # --- Notificaciones ---
            if instance.archivo_pdf_generado and not instance.telegram_file_id:
                try:
                    from apps.communications.services.notificaciones_boletos import notificar_boleto_procesado
                    notificar_boleto_procesado(instance)
                except Exception as e_notif:
                    logger.error(f"⚠️ Error en notificación: {e_notif}")

        except Exception as e:
            logger.error(f"❌ Error crítico en señal de BoletoImportado {instance.pk}: {e}")



# Notificaciones de Venta consolidadas en apps/bookings/signals.py (venta_post_save_dispatcher)


@receiver(post_save, sender='bookings.PagoVenta')
def enviar_confirmacion_pago_recibido(sender, instance, created, **kwargs):
    """Envía notificación de confirmación cuando se registra un pago"""
    if kwargs.get('raw', False):
        return
    
    if created and instance.confirmado:
        notificar_confirmacion_pago(instance)


@receiver(post_save, sender='core.MigrationCheck')
def enviar_alerta_migratoria(sender, instance, created, **kwargs):
    """
    Dispara la notificación de alerta migratoria si el resultado es crítico.
    """
    if kwargs.get('raw', False):
        return

    # Solo notificar si es creado o si cambió el nivel de alerta (si pudiéramos rastrearlo)
    # Por ahora notificamos si es creado y es alerta
    if created and instance.alert_level in ['RED', 'YELLOW']:
         from apps.communications.services.notification_service import notificar_alerta_migratoria
         try:
             notificar_alerta_migratoria(instance)
         except Exception as e:
             logger.error(f"Error disparando señal de alerta migratoria: {e}")


# --- Facturación Notificaciones ---

@receiver(pre_save, sender='finance.Factura')
def capturar_pdf_factura_anterior(sender, instance, **kwargs):
    from apps.finance.models import Factura
    """Detectar si el archivo PDF cambia."""
    if instance.pk:
        try:
            old_inst = Factura.objects.get(pk=instance.pk)
            instance._old_pdf = old_inst.archivo_pdf
        except Factura.DoesNotExist:
            instance._old_pdf = None
    else:
        instance._old_pdf = None

@receiver(post_save, sender='finance.Factura')
def enviar_factura_telegram(sender, instance, created, **kwargs):
    """
    Envía la Factura por Telegram cuando se genera/asigna su PDF.
    """
    if kwargs.get('raw', False): return

    # Verificar si hay un NUEVO archivo PDF
    nuevo_pdf = bool(instance.archivo_pdf)
    viejo_pdf = bool(getattr(instance, '_old_pdf', None))
    cambio_pdf = nuevo_pdf and (not viejo_pdf or instance.archivo_pdf != instance._old_pdf)

    if cambio_pdf:
        try:
            from apps.communications.services.telegram_notification_service import (
                TelegramNotificationService,
            )
            
            # Construir caption
            simbolo = instance.moneda.simbolo if instance.moneda else "$"
            caption = (
                f"🧾 <b>Nueva Factura Generada</b>\n"
                f"🔢 Nro: {instance.numero_factura}\n"
                f"👤 Cliente: {instance.cliente_nombre or 'N/A'}\n"
                f"💰 Total: {instance.monto_total:,.2f} {simbolo}\n"
                f"📅 Fecha: {instance.fecha_emision}"
            )

            pdf_path_or_url = None
            try:
                # Intento 1: Path local
                if hasattr(instance.archivo_pdf, 'path'):
                     pdf_path_or_url = instance.archivo_pdf.path
            except NotImplementedError:
                # Intento 2: URL remota
                if hasattr(instance.archivo_pdf, 'url'):
                     pdf_path_or_url = instance.archivo_pdf.url
            
            if pdf_path_or_url:
                TelegramNotificationService.send_document(
                    file_path=pdf_path_or_url, 
                    caption=caption
                )
                logger.info(f"📲 Factura {instance.numero_factura} enviada a Telegram.")
            else:
                logger.error(f"❌ No se pudo obtener Path ni URL de Factura {instance.numero_factura}")

        except Exception as e:
            logger.error(f"Error enviando Factura {instance.pk} a Telegram: {e}")

