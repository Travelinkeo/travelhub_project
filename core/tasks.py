# core/tasks.py
import imaplib
import email
from email.header import decode_header
import logging
import os

from celery import shared_task
from django.conf import settings
from django.core.files.base import ContentFile

from .models import BoletoImportado

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
    Tarea de Celery para conectar a un buzón IMAP, leer correos no leídos
    y crear objetos BoletoImportado para su procesamiento.
    """
    logger.info("Iniciando la tarea de procesamiento de correos...")

    host = getattr(settings, 'TICKET_IMAP_HOST', None)
    port = getattr(settings, 'TICKET_IMAP_PORT', 993)
    user = getattr(settings, 'TICKET_IMAP_USER', None)
    password = getattr(settings, 'TICKET_IMAP_PASSWORD', None)
    mailbox = getattr(settings, 'TICKET_IMAP_MAILBOX', 'INBOX')
    use_ssl = getattr(settings, 'TICKET_IMAP_USE_SSL', True)

    if not all([host, user, password]):
        logger.warning("La configuración de IMAP para boletos no está completa. Saltando la tarea.")
        return "Configuración IMAP incompleta."

    mail = None
    try:
        logger.info(f"Conectando a {host} con el usuario {user}...")
        if use_ssl:
            mail = imaplib.IMAP4_SSL(host, port)
        else:
            mail = imaplib.IMAP4(host, port)
        
        mail.login(user, password)
        mail.select(mailbox)

        # Buscar correos no leídos
        status, messages = mail.search(None, 'UNSEEN')
        if status != 'OK':
            logger.error("Error al buscar correos en el buzón.")
            return "Error en búsqueda de correos."

        email_ids = messages[0].split()
        logger.info(f"Se encontraron {len(email_ids)} correos nuevos.")

        for email_id in email_ids:
            try:
                # Obtener el contenido completo del correo
                res, msg_data = mail.fetch(email_id, '(RFC822)')
                if res != 'OK':
                    logger.error(f"No se pudo obtener el correo con ID {email_id.decode()}.")
                    continue

                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)

                # Guardar el .eml original primero
                eml_filename = f"boleto_{email_id.decode()}.eml"
                BoletoImportado.objects.create(
                    archivo_boleto=ContentFile(raw_email, name=eml_filename)
                )
                logger.info(f"Creado BoletoImportado para {eml_filename} a partir del .eml original.")

                # Ahora, buscar adjuntos (PDF, TXT)
                if msg.is_multipart():
                    for part in msg.walk():
                        content_disposition = str(part.get("Content-Disposition"))
                        if "attachment" in content_disposition:
                            filename = get_filename_from_header(part.get_filename())
                            if filename:
                                # Validar extensión
                                allowed_exts = ['.pdf', '.txt']
                                if any(filename.lower().endswith(ext) for ext in allowed_exts):
                                    attachment_content = part.get_payload(decode=True)
                                    BoletoImportado.objects.create(
                                        archivo_boleto=ContentFile(attachment_content, name=filename)
                                    )
                                    logger.info(f"Creado BoletoImportado para el adjunto: {filename}")

                # Marcar el correo como leído
                mail.store(email_id, '+FLAGS', '\\Seen')

            except Exception as e:
                logger.exception(f"Error procesando el correo con ID {email_id.decode()}: {e}")
                # Opcional: marcar como no leído para reintentar o mover a una carpeta de error
                # mail.store(email_id, '-FLAGS', '\\Seen')

        return f"Tarea finalizada. Se procesaron {len(email_ids)} correos."

    except Exception as e:
        logger.exception(f"Fallo crítico en la tarea de procesamiento de correos: {e}")
        return f"Error crítico: {e}"

        finally:

            if mail:

                try:

                    mail.logout()

                    logger.info("Conexión IMAP cerrada correctamente.")

                except Exception as e:

                    logger.error(f"Error al cerrar la conexión IMAP: {e}")

    

    

    @shared_task(name="core.tasks.send_ticket_notification")

    def send_ticket_notification(boleto_id):

        """

        Envía una notificación por correo electrónico con el boleto PDF generado.

        """

        try:

            boleto = BoletoImportado.objects.get(id_boleto_importado=boleto_id)

            logger.info(f"Iniciando envío de notificación para Boleto ID: {boleto_id}")

    

            if not boleto.archivo_pdf_generado:

                logger.warning(f"No se encontró PDF generado para el Boleto ID: {boleto_id}. No se puede enviar notificación.")

                return f"No hay PDF para el boleto {boleto_id}."

    

            # --- Lógica de envío de correo ---

            from django.core.mail import EmailMessage

    

            # Determinar el destinatario. Podría ser el cliente, un admin, etc.

            # Por ahora, usaremos un email de placeholder que se puede configurar en .env

            recipient_email = getattr(settings, 'TICKET_NOTIFICATION_RECIPIENT', settings.EMAIL_HOST_USER)

            if not recipient_email:

                logger.error("No se ha configurado 'TICKET_NOTIFICATION_RECIPIENT' en los ajustes. No se puede enviar correo.")

                return "Destinatario de notificación no configurado."

    

            subject = f"Nuevo Boleto Procesado: {boleto.nombre_pasajero_procesado or 'N/A'} - PNR: {boleto.localizador_pnr or 'N/A'}"

            body = (

                "Se ha procesado un nuevo boleto de viaje.\n\n"

                f"Pasajero: {boleto.nombre_pasajero_completo}\n"

                f"Localizador: {boleto.localizador_pnr}\n"

                f"Ruta: {boleto.ruta_vuelo}\n\n"

                "El boleto unificado se encuentra adjunto a este correo.\n\n"

                "Saludos,\nEl equipo de TravelHub"

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

    