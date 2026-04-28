import logging
import datetime
from decimal import Decimal

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.db import transaction

# 🔒 PADLOCK: CRITICAL INFRASTRUCTURE
# This file handles the automatic triggering of Ticket Parsing via Celery.
# LOGIC IS LOCKED. DO NOT MODIFY WITHOUT EXPLICIT AUTHORIZATION.
# Maintained by: Antigravity/Gemini
# -----------------------------------------------------

# Models are imported inside receivers to avoid circular dependencies during django.setup()
# from apps.bookings.models import BoletoImportado, Venta, ItemVenta, PagoVenta
# from core.models_catalogos import Moneda, ProductoServicio
# from apps.crm.models import Pasajero, Cliente 

from core.notification_service import (
    notificar_confirmacion_venta,
    notificar_cambio_estado,
    notificar_confirmacion_pago
)

logger = logging.getLogger(__name__)

@receiver(post_save, sender='bookings.BoletoImportado')
def crear_o_actualizar_venta_desde_boleto(sender, instance, created, **kwargs):
    from apps.bookings.models import BoletoImportado, Venta, ItemVenta
    from core.models_catalogos import Moneda, ProductoServicio
    from apps.crm.models import Pasajero
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
    localizador = data.get('reservation_code') or data.get('SOLO_CODIGO_RESERVA') or data.get('pnr') or data.get('localizador')
    if localizador:
        localizador = str(localizador).strip()[:20]
    
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
            
            # Truncamiento de seguridad para el modelo Pasajero (max_length=100)
            nombres = nombres[:100]
            apellidos = apellidos[:100]
            
            if not numero_documento:
                # Fallback para crear un ID único si no viene en el boleto
                doc_fallback = f"NN-{apellidos.replace(' ', '')}-{nombres.replace(' ', '')}".upper()
                numero_documento = doc_fallback

            # Determinar Agencia (FIX VENTA HUÉRFANA y Pasajero Isolation)
            agencia_owner = instance.agencia
            if not agencia_owner:
                from core.models import Agencia
                # Fallback: Usar la primera agencia disponible (preventivo)
                agencia_owner = Agencia.objects.filter(activa=True).first()
                if agencia_owner:
                     logger.warning(f"BoletoImportado {instance.pk} sin agencia. Asignando agencia por defecto: {agencia_owner}")
                else:
                     logger.error(f"CRÍTICO: No hay agencias disponibles para asignar a la venta del Boleto {instance.pk}")

            # --- 1. Buscar o crear el Pasajero (SaaS Isolation) ---
            # Intentamos buscar por documento globalmente o restringido a la agencia?
            # Estrategia Híbrida: Buscamos coincidencia exacta. Si existe y no tiene agencia, es global/legacy.
            # Si no existe, lo creamos asignado a la agencia.
            
            pasajero, created_pax = Pasajero.objects.get_or_create(
                numero_documento=numero_documento,
                defaults={
                    'nombres': nombres, 
                    'apellidos': apellidos,
                    'agencia': agencia_owner # Asignamos la agencia al crear
                }
            )
            
            # Si el pasajero existía pero no tenia agencia (Legacy), y ahora lo estamos usando en una agencia...
            # Opcional: Podríamos asignarselo si es huérfano.
            if not created_pax and not pasajero.agencia and agencia_owner:
                 # Lo adoptamos? O lo dejamos global?
                 # Por simplicidad en esta fase, lo dejamos global (compartido) o lo adoptamos si no tiene dueño.
                 pass

            # --- 2. Buscar o crear la Venta ---
            moneda_codigo = moneda_iso.upper() if moneda_iso else 'USD'
            moneda = Moneda.objects.filter(codigo_iso=moneda_codigo).first()
            
            if not moneda and moneda_codigo in ['VES', 'BS']:
                moneda = Moneda.objects.filter(codigo_iso__in=['VES', 'BS', 'VEF']).first()
            
            if not moneda:
                # Fallback final a USD
                moneda, _ = Moneda.objects.get_or_create(
                    codigo_iso='USD', 
                    defaults={'nombre': 'Dólar Estadounidense'}
                )

            # Agencia ya determinada arriba

            try:
                logger.info(f"⚡ INTENTANDO Venta.get_or_create: localizador={localizador}, moneda={moneda}, agencia={agencia_owner}")
                venta, venta_creada = Venta.objects.get_or_create(
                    localizador=localizador,
                    defaults={
                        'cliente': None,
                        'moneda': moneda,
                        'agencia': agencia_owner,
                        'canal_origen': Venta.CanalOrigen.IMPORTACION,
                        'descripcion_general': f"Venta importada desde boleto con localizador {localizador}"
                    }
                )
            except Exception as e_venta:
                logger.error(f"❌ FALLÓ Venta.get_or_create: {str(e_venta)}")
                logger.error(f"VALORES: localizador={localizador}, moneda_id={moneda.id_moneda if moneda else 'NONE'}, agencia_id={agencia_owner.pk if agencia_owner else 'NONE'}")
                raise e_venta

            if not venta_creada:
                 # Si la venta ya existía, verificamos si está huérfana y la adoptamos
                 if not venta.agencia and agencia_owner:
                      venta.agencia = agencia_owner
                      venta.save(update_fields=['agencia'])
                      logger.info(f"Venta existente {venta.pk} estaba huérfana. Asignada agencia {agencia_owner}.")

                 if venta.moneda != moneda:
                    logger.warning(f"Conflicto de moneda para Venta {venta.pk}. Se mantiene la moneda original {venta.moneda.codigo_iso}.")
            
            venta.pasajeros.add(pasajero)

            # --- 3. Buscar el Producto/Servicio "Boleto Aéreo" ---
            producto_boleto, _ = ProductoServicio.objects.get_or_create(
                nombre='Boleto Aéreo',
                defaults={'descripcion': 'Servicio de transporte aéreo.', 'tipo_producto': 'SER'}
            )

            # --- 4. Crear el ItemVenta ---
            total_boleto = Decimal(total_str)
            numero_boleto = data.get('ticket_number') or data.get('NUMERO_DE_BOLETO') or localizador
            
            ItemVenta.objects.create(
                venta=venta,
                producto_servicio=producto_boleto,
                descripcion_personalizada=f"Boleto aéreo {numero_boleto} para {pasajero_nombre_completo} ({aerolinea})",
                cantidad=1,
                precio_unitario_venta=total_boleto,
            )

            # --- 5. Asociar el boleto a la venta ---
            # Se permite que múltiples boletos (pasajeros) se asocien a la misma venta (localizador)
            instance.venta_asociada = venta
            instance.save(update_fields=['venta_asociada'])

            logger.info(f"Procesado BoletoImportado {instance.pk}. Venta {venta.pk} (localizador: {localizador}) creada/actualizada.")

            # --- 5.5. Validación Automática de Migración ---
            # Solo si la venta es nueva o se actualizó para incluir pasajeros/segmentos
            try:
                from core.services.migration_checker_service import MigrationCheckerService
                
                mig_service = MigrationCheckerService()
                
                # Obtener segmentos de vuelo (si existen)
                # Nota: Los segmentos se crean DESPUÉS de esta señal si se procesan por separado.
                # Pero si vienen en 'datos_parseados', podemos inferirlos o esperar.
                # En el flujo actual, SegmentoVuelo suele crearse después o en paralelo.
                # Sin embargo, 'datos_parseados' tiene la info cruda.
                
                flights_data = []
                if 'flights' in data:
                    # Usar datos normalizados si están disponibles
                    for f in data['flights']:
                         flights_data.append({
                             'origen': f.get('departure', {}).get('location', '')[:3], # Asumiendo código IATA en location
                             'destino': f.get('arrival', {}).get('location', '')[:3],
                             'fecha': datetime.datetime.strptime(f.get('date'), '%Y-%m-%d').date() if f.get('date') else timezone.now().date()
                         })
                
                # Si no hay datos normalizados de vuelos, intentamos reconstruir desde el texto crudo o saltamos
                # Para MVP, solo validamos si tenemos datos claros
                
                if flights_data and pasajero:
                    logger.info(f"🚦 Ejecutando chequeo migratorio automático para {pasajero.get_nombre_completo()}")
                    check = mig_service.check_migration_requirements(
                        pasajero_id=pasajero.id_pasajero,
                        vuelos=flights_data,
                        venta_id=venta.id_venta
                    )
                    if check.alert_level in ['RED', 'YELLOW']:
                        logger.warning(f"⚠️ Alerta Migratoria ({check.alert_level}) para Venta {venta.localizador}: {check.summary}")
            except Exception as e_mig:
                logger.error(f"Error en validación migratoria automática: {e_mig}")

            
            # --- 6. Automatización de Facturación (SaaS) ---
            # Si el boleto viene del Monitor automático, generamos la Factura en Borrador
            if instance.formato_detectado and instance.formato_detectado.startswith('EML'):
                try:
                    from apps.finance.services.invoice_service import InvoiceService
                    logger.info(f"⚡ Generando Factura Automática (Finanzas) para Venta {venta.pk}")
                    InvoiceService.create_invoice_from_sale(venta.id_venta)
                except Exception as e_fact:
                    logger.error(f"⚠️ Error generando factura automática: {e_fact}")
            
            # Enviar notificación de boleto procesado (SOLO SI TIENE PDF Y NO FUE ENVIADO POR EL BOT)
            if instance.archivo_pdf_generado:
                try:
                    # 🚀 DE-DUPLICATION: If the bot already sent it via TicketParserService, 
                    # it will have instance.telegram_file_id. We skip signal notification to avoid triplicates.
                    if not instance.telegram_file_id:
                        from core.services.notificaciones_boletos import notificar_boleto_procesado
                        notificar_boleto_procesado(instance)
                        logger.info(f"📲 Señal: Notificación enviada para Boleto {instance.pk}")
                    else:
                        logger.info(f"🔕 Señal: Notificación omitida para Boleto {instance.pk} (Ya enviado por Bot/Service)")
                except Exception as notif_error:
                    logger.warning(f"Error enviando notificación de boleto: {notif_error}")
            elif not instance.archivo_pdf_generado:
                logger.info(f"Omitiendo notificación para Boleto {instance.pk} por falta de PDF (se enviará al adjuntar).")

        except Exception as e:
            logger.error(f"Error en la señal para BoletoImportado {instance.pk}: {e}", exc_info=True)


@receiver(pre_save, sender='bookings.Venta')
def capturar_estado_anterior_venta(sender, instance, **kwargs):
    from apps.bookings.models import Venta
    """Captura el estado anterior antes de guardar para detectar cambios"""
    if instance.pk:
        try:
            instance._estado_anterior = Venta.objects.get(pk=instance.pk).estado
        except Venta.DoesNotExist:
            instance._estado_anterior = None
    else:
        instance._estado_anterior = None


@receiver(post_save, sender='bookings.Venta')
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


@receiver(post_save, sender='bookings.PagoVenta')
def enviar_confirmacion_pago_recibido(sender, instance, created, **kwargs):
    from apps.bookings.models import PagoVenta
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
         from core.notification_service import notificar_alerta_migratoria
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
    from apps.finance.models import Factura
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
            from core.services.telegram_notification_service import TelegramNotificationService
            
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

