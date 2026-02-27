# core/tasks.py
import imaplib
import email
from email.header import decode_header
import logging
import os

from celery import shared_task
from django.conf import settings
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)

def get_filename_from_header(header):
    """Decodifica el nombre de un archivo desde el header de un email."""
    if not header:
        return None
    decoded_header = decode_header(header)
    parts = []
    for part, charset in decoded_header:
        if isinstance(part, bytes):
            try:
                parts.append(part.decode(charset or 'utf-8', errors='ignore'))
            except (UnicodeDecodeError, LookupError):
                parts.append(part.decode('latin-1', errors='ignore'))
        else:
            parts.append(part)
    return ''.join(parts)


@shared_task(name="core.tasks.process_incoming_emails")
def process_incoming_emails():
    """
    Tarea de Celery para procesar correos de TODAS las agencias activas.
    Usa el servicio centralizado EmailMonitorService.
    """
    from core.models import Agencia
    from core.services.email_monitor_service import EmailMonitorService

    logger.info("🚀 Iniciando tarea programada: Procesamiento de Correos (Multi-Tenant)")
    
    agencias = Agencia.objects.filter(activa=True)
    total_procesados = 0
    total_agencias = 0

    if not agencias.exists():
        logger.warning("No hay agencias activas para monitorear.")
        return "Sin agencias activas."

    for agencia in agencias:
        try:
            # Validar si tiene credenciales
            if not agencia.email_monitor_user or not agencia.email_monitor_password:
                continue

            logger.info(f"🔄 Procesando agencia: {agencia.nombre} ({agencia.email_monitor_user})")
            
            monitor = EmailMonitorService(
                agencia=agencia, 
                notification_type='telegram', # Changed to telegram to ensure Admin gets notified + backup email
                process_all=False, 
                mark_as_read=True
            )
            
            # Procesar una vez (sin loop infinito)
            cantidad = monitor.procesar_una_vez()
            total_procesados += cantidad
            total_agencias += 1
            
        except Exception as e:
            logger.error(f"❌ Error procesando agencia {agencia.nombre}: {e}")
            continue

    resultado = f"Tarea finalizada. {total_procesados} correos procesados en {total_agencias} agencias."
    logger.info(resultado)
    return resultado


@shared_task(name="core.tasks.procesar_boleto_task")
def procesar_boleto_task(boleto_id):
    """
    Tarea asíncrona para procesar un boleto individual.
    Útil para uploads desde Admin o reintentos manuales.
    """
    try:
        from core.services.ticket_parser_service import TicketParserService
        logger.info(f"🧩 Iniciando tarea de parseo para Boleto {boleto_id}")
        service = TicketParserService()
        resultado = service.procesar_boleto(boleto_id)
        if resultado:
             logger.info(f"✅ Tarea de parseo completada para Boleto {boleto_id}")
             return f"Boleto {boleto_id} procesado exitosamente."
        else:
             logger.warning(f"⚠️ Tarea de parseo finalizó sin resultados para Boleto {boleto_id}")
             return f"Fallo al procesar Boleto {boleto_id}"
    except Exception as e:
        logger.error(f"❌ Error en procesar_boleto_task: {e}")
        return f"Error: {e}"


    

    

    @shared_task(name="core.tasks.send_ticket_notification")

    def send_ticket_notification(boleto_id):

        """

        Envía una notificación por correo electrónico con el boleto PDF generado.

        """

        try:
            from core.models import BoletoImportado
            boleto = BoletoImportado.objects.get(id_boleto_importado=boleto_id)

            logger.info(f"Iniciando envío de notificación para Boleto ID: {boleto_id}")

    

            if not boleto.archivo_pdf_generado:

                logger.warning(f"No se encontró PDF generado para el Boleto ID: {boleto_id}. No se puede enviar notificación.")

                return f"No hay PDF para el boleto {boleto_id}."

    

            # --- Lógica de envío de correo ---

            from django.core.mail import EmailMessage

    

            # SaaS Fix: Usar email de soporte/ventas de la agencia
            if not recipient_email:
                logger.error(f"Agencia {boleto.agencia.nombre} no tiene email configurado. No se puede enviar correo.")
                return "Destinatario de notificación no configurado."

            # 🛡️ Guard: Skip placeholder emails to avoid bounce-backs
            if "@sin-email.com" in recipient_email.lower():
                logger.info(f"🔕 Notificación omitida para email de marcador de posición: {recipient_email}")
                return "Omitido por ser email de marcador de posición"

    

            # SaaS Fix: Firma dinámica
            sender_name = boleto.agencia.nombre_comercial or boleto.agencia.nombre
            from_email = boleto.agencia.email_principal or settings.DEFAULT_FROM_EMAIL
            
            subject = f"Nuevo Boleto Procesado: {boleto.nombre_pasajero_procesado or 'N/A'} - PNR: {boleto.localizador_pnr or 'N/A'}"

            body = (
                "Se ha procesado un nuevo boleto de viaje.\n\n"
                f"Pasajero: {boleto.nombre_pasajero_completo}\n"
                f"Localizador: {boleto.localizador_pnr}\n"
                f"Ruta: {boleto.ruta_vuelo}\n\n"
                "El boleto unificado se encuentra adjunto a este correo.\n\n"
                f"Saludos,\nEl equipo de {sender_name}"
            )

            

            email = EmailMessage(

                subject,

                body,

                settings.DEFAULT_FROM_EMAIL,

                [recipient_email],

            )

    

            # Adjuntar el PDF

            boleto.archivo_pdf_generado.open(mode='rb')

            email.attach(

                boleto.archivo_pdf_generado.name,

                boleto.archivo_pdf_generado.read(),

                'application/pdf'

            )

            boleto.archivo_pdf_generado.close()

    

            email.send()

            logger.info(f"Notificación para Boleto ID: {boleto_id} enviada a {recipient_email}.")

            return f"Notificación para boleto {boleto_id} enviada."

    

        except BoletoImportado.DoesNotExist:

            logger.error(f"Se intentó enviar una notificación para un Boleto ID ({boleto_id}) que no existe.")

            return f"Boleto con ID {boleto_id} no encontrado."

        except Exception as e:

            logger.exception(f"Fallo crítico al enviar notificación para Boleto ID {boleto_id}: {e}")

            # Reintentar la tarea podría ser una opción aquí si es un error de red

            raise e


@shared_task(name="core.tasks.check_passport_expiry")
def check_passport_expiry():
    """
    Tarea diaria para verificar pasaportes próximos a vencer (6 meses).
    Envía una alerta al agente (o cliente en el futuro).
    """
    from django.utils import timezone
    from datetime import timedelta
    from apps.crm.models import Pasajero, Cliente
    from django.core.mail import send_mail
    
    logger.info("Iniciando chequeo de vencimiento de documentos (Multi-Tenant)...")
    
    today = timezone.now().date()
    threshold_date = today + timedelta(days=180) # 6 meses
    
    # Buscar pasaportes que vencen en el rango de la semana objetivo
    start_range = threshold_date
    end_range = threshold_date + timedelta(days=7)
    
    from core.models import Agencia
    total_alerts = 0

    # Iterar por agencia para enviar reportes separados
    for agencia in Agencia.objects.filter(activa=True):
        pasajeros_vencimiento = Pasajero.objects.filter(
            agencia=agencia,
            tipo_documento=Pasajero.TipoDocumento.PASAPORTE,
            fecha_expiracion_documento__range=[start_range, end_range]
        )
        
        clientes_vencimiento = Cliente.objects.filter(
            agencia=agencia,
            numero_pasaporte__isnull=False,
            fecha_expiracion_pasaporte__range=[start_range, end_range]
        )
        
        count = pasajeros_vencimiento.count() + clientes_vencimiento.count()
        
        if count > 0:
            logger.info(f"Agencia {agencia.nombre}: {count} documentos por vencer.")
            
            report_lines = [f"Reporte para {agencia.nombre_comercial or agencia.nombre}:\nLos siguientes documentos vencerán en 6 meses:\n"]
            
            for p in pasajeros_vencimiento:
                report_lines.append(f"- Pasajero: {p.nombres} {p.apellidos} (Vence: {p.fecha_expiracion_documento})")
                
            for c in clientes_vencimiento:
                report_lines.append(f"- Cliente: {c.nombres} {c.apellidos} (Vence: {c.fecha_expiracion_pasaporte})")
                
            body = "\n".join(report_lines)
            
            recipient_email = agencia.email_ventas or agencia.email_soporte or getattr(settings, 'TICKET_NOTIFICATION_RECIPIENT', settings.EMAIL_HOST_USER)
            
            if recipient_email:
                send_mail(
                    "⚠️ Alerta de Vencimiento de Pasaportes",
                    body,
                    agencia.email_principal or settings.DEFAULT_FROM_EMAIL,
                    [recipient_email],
                    fail_silently=False,
                )
                logger.info(f"Reporte enviado a {recipient_email}")
                total_alerts += count
        
    return f"Chequeo completado. {total_alerts} alertas procesadas."


@shared_task(name="core.tasks.check_upcoming_flights")
def check_upcoming_flights():
    """
    Tarea para buscar vuelos en las próximas 24 horas y enviar recordatorio de Check-in.
    Envia alerta al Admin vía Telegram.
    """
    from django.utils import timezone
    from datetime import timedelta
    from core.models import BoletoImportado
    from core.utils.telegram_utils import send_telegram_alert_sync
    import json
    
    logger.info("🔍 Buscando vuelos próximos para Check-in...")
    
    now = timezone.now()
    tomorrow_start = now + timedelta(hours=23)
    tomorrow_end = now + timedelta(hours=25)
    
    # Buscamos boletos con fecha de salida en el rango de ~24hs
    # Nota: Esto depende de que hayamos parseado la fecha de salida.
    # Como el modelo BoletoImportado actual guarda mucha data en JSON, 
    # iteraremos los recientes para verificar la fecha dentro del JSON 'datos_parseados'.
    
    # Optimización: Filtrar por fecha de creación reciente (últimos 365 días)
    # y que no estén cancelados.
    from core.models import Agencia
    from core.services.telegram_notification_service import TelegramNotificationService
    
    total_alerts = 0
    
    # Iterar por Agencias
    for agencia in Agencia.objects.filter(activa=True):
        boletos = BoletoImportado.objects.filter(
            agencia=agencia,
            fecha_subida__gte=now - timedelta(days=365),
            estado_parseo='COM'
        )
        
        # Obtener Chat ID de la agencia (SaaS)
        chat_id = agencia.configuracion_api.get('TELEGRAM_GROUP_ID') or getattr(settings, 'TELEGRAM_GROUP_ID', None)
        if not chat_id: continue

        for boleto in boletos:
            try:
                data = boleto.datos_parseados
                if isinstance(data, str):
                    data = json.loads(data)
                    
                # Buscar segmentos de vuelo
                if 'vuelos' in data and isinstance(data['vuelos'], list):
                    for vuelo in data['vuelos']:
                        fecha_str = vuelo.get('fecha_salida') or vuelo.get('date')
                        
                        target_date_str = tomorrow_start.strftime("%d %b") 
                        
                        if fecha_str and target_date_str.upper() in str(fecha_str).upper():
                            # ENCONTRADO CANDIDATO
                            msg = (
                                f"⏰ <b>RECORDATORIO DE CHECK-IN</b>\n\n"
                                f"El vuelo de <b>{boleto.nombre_pasajero_completo}</b> sale mañana.\n"
                                f"✈️ Aerolínea: {boleto.aerolinea_emisora}\n"
                                f"📍 PNR: <code>{boleto.localizador_pnr}</code>\n"
                                f"📅 Fecha: {fecha_str}\n\n"
                                f"<i>Verifica si el Check-in está abierto.</i>"
                            )
                            # Enviar usando servicio SaaS con contexto de Agencia
                            TelegramNotificationService.send_message(msg, chat_id=chat_id, agencia=agencia)
                            total_alerts += 1
                            logger.info(f"Alerta check-in enviada para {boleto.localizador_pnr} (Agencia: {agencia.nombre})")
                            break 
                            
            except Exception as e:
                logger.error(f"Error procesando boleto {boleto.pk} para checkin: {e}")

    result = f"Check-in scan completado. Alertas enviadas: {total_alerts}"
    logger.info(result)
    return result


@shared_task(name="core.tasks.check_client_birthdays")
def check_client_birthdays():
    """
    Tarea diaria para felicitar a clientes y pasajeros por su cumpleaños.
    Soporta configuración Multi-Tenant (SMTP por Agencia).
    """
    from django.utils import timezone
    from apps.crm.models import Cliente, Pasajero
    from core.models import Agencia
    from django.core.mail import get_connection, EmailMessage
    
    logger.info("Iniciando chequeo de cumpleaños (Multi-Tenant)...")
    today = timezone.now().date()
    count = 0
    
    # Iterar por cada agencia activa
    for agencia in Agencia.objects.filter(activa=True):
        # Obtener configuración de correo de la agencia
        email_config = agencia.configuracion_correo
        
        # Si no tiene configuración, usar la del sistema (fallback) o saltar
        # Por ahora, usaremos un connection con los datos si existen
        connection = None
        from_email = settings.DEFAULT_FROM_EMAIL
        
        if email_config and 'EMAIL_HOST' in email_config:
            try:
                connection = get_connection(
                    host=email_config.get('EMAIL_HOST'),
                    port=email_config.get('EMAIL_PORT', 587),
                    username=email_config.get('EMAIL_HOST_USER'),
                    password=email_config.get('EMAIL_HOST_PASSWORD'),
                    use_tls=email_config.get('EMAIL_USE_TLS', True)
                )
                from_email = email_config.get('DEFAULT_FROM_EMAIL', from_email)
            except Exception as e:
                logger.error(f"Error configurando SMTP para agencia {agencia.nombre}: {e}")
                continue # Saltar esta agencia si falla la config
        else:
            # Usar conexión por defecto de Django
            connection = get_connection()

        # Buscar clientes de ESTA agencia que cumplen años
        clientes_cumple = Cliente.objects.filter(
            agencia=agencia,
            fecha_nacimiento__month=today.month,
            fecha_nacimiento__day=today.day,
            email__isnull=False
        )
        
        # Enviar a Clientes
        for c in clientes_cumple:
            try:
                email = EmailMessage(
                    f"¡Feliz Cumpleaños, {c.nombres}!",
                    f"Hola {c.nombres},\n\nDesde {agencia.nombre_comercial or agencia.nombre} te deseamos un muy feliz cumpleaños. ¡Que tengas un día lleno de viajes y aventuras!\n\nSaludos,\nEl equipo de {agencia.nombre}",
                    from_email,
                    [c.email],
                    connection=connection
                )
                email.send()
                count += 1
            except Exception as e:
                logger.error(f"Error enviando felicitación a cliente {c.id_cliente} de agencia {agencia.nombre}: {e}")

    logger.info(f"Felicitaciones enviadas (Total): {count}")
    return f"Cumpleaños procesados: {count}"


@shared_task(name="core.tasks.check_pending_payments")
def check_pending_payments():
    """
    Tarea diaria para recordar pagos pendientes.
    Regla: Recordar a los 3, 7 y 15 días de la venta si hay saldo pendiente.
    """
    from django.utils import timezone
    from datetime import timedelta
    from core.models import Venta
    from django.core.mail import send_mail
    
    logger.info("Iniciando chequeo de pagos pendientes...")
    today = timezone.now().date()
    
    # Definir los días de antigüedad para enviar recordatorio
    days_to_remind = [3, 7, 15]
    
    count = 0
    
    from core.models import Agencia
    from django.core.mail import get_connection

    for agencia in Agencia.objects.filter(activa=True):
        # Configurar SMTP de agencia
        email_config = agencia.configuracion_correo
        connection = None
        from_email = settings.DEFAULT_FROM_EMAIL
        
        if email_config and 'EMAIL_HOST' in email_config:
            try:
                connection = get_connection(
                    host=email_config.get('EMAIL_HOST'),
                    port=email_config.get('EMAIL_PORT', 587),
                    username=email_config.get('EMAIL_HOST_USER'),
                    password=email_config.get('EMAIL_HOST_PASSWORD'),
                    use_tls=email_config.get('EMAIL_USE_TLS', True)
                )
                from_email = email_config.get('DEFAULT_FROM_EMAIL', from_email)
            except Exception:
                pass
        
        for days in days_to_remind:
            target_date = today - timedelta(days=days)
            
            # Buscar ventas de ESTA agencia
            ventas_pendientes = Venta.objects.filter(
                agencia=agencia,
                fecha_venta__date=target_date,
                saldo_pendiente__gt=0,
                estado__in=[Venta.EstadoVenta.PENDIENTE_PAGO, Venta.EstadoVenta.PAGADA_PARCIAL],
                cliente__email__isnull=False
            )
            
            for venta in ventas_pendientes:
                try:
                    cliente = venta.cliente
                    sender_name = agencia.nombre_comercial or agencia.nombre
                    subject = f"Recordatorio de Pago Pendiente - Localizador: {venta.localizador}"
                    body = (
                        f"Estimado/a {cliente.nombres},\n\n"
                        f"Desde {sender_name} le recordamos que su reserva con localizador {venta.localizador} tiene un saldo pendiente de {venta.saldo_pendiente} {venta.moneda.codigo}.\n\n"
                        "Por favor, realice el pago para evitar la cancelación de sus servicios.\n\n"
                        "Saludos,\nEl equipo de Administración"
                    )
                    
                    email = EmailMessage(
                        subject, body, from_email, [cliente.email], connection=connection
                    )
                    email.send()
                    
                    count += 1
                    logger.info(f"Recordatorio enviado para Venta {venta.id_venta} (Agencia: {agencia.nombre})")
                    
                except Exception as e:
                    logger.error(f"Error enviando recordatorio para Venta {venta.id_venta}: {e}")
                
    return f"Recordatorios de pago enviados: {count}"


@shared_task(name="core.tasks.sync_bcv_rates")
def sync_bcv_rates():
    """
    Tarea diaria para sincronizar la tasa del BCV.
    """
    from contabilidad.tasas_venezuela_client import TasasVenezuelaClient
    
    logger.info("Iniciando sincronización de tasas BCV...")
    
    try:
        resultados = TasasVenezuelaClient.actualizar_tasas_db()
        
        if resultados.get('oficial'):
            tasa = resultados['oficial']
            # Verificar si es objeto valido (tiene atributo tasa) o es un bool/dict
            if hasattr(tasa, 'tasa'):
                logger.info(f"Tasa BCV actualizada: {tasa.tasa} (Fecha: {tasa.fecha_validez})")
                return f"Sincronización exitosa. Tasa: {tasa.tasa}"
            else:
                 logger.info(f"Tasa BCV actualizada (Valor Crudo): {tasa}")
                 return f"Sincronización exitosa. Valor: {tasa}"
        else:
            logger.error("No se pudo obtener/guardar la tasa BCV.")
            return "Fallo en sincronización BCV."
            
    except Exception as e:
        logger.exception(f"Error crítico sincronizando tasas: {e}")
        return f"Error crítico: {e}"

    