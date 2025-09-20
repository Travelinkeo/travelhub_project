# Archivo: core/management/commands/fetch_tickets.py

import email
import imaplib
from email.header import decode_header

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from core.models.boletos import BoletoImportado


class Command(BaseCommand):
    help = 'Revisa el correo electrónico configurado, descarga nuevos boletos de Kiu y los guarda en la base de datos para ser procesados.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Iniciando el proceso de revisión de boletos por correo..."))

        try:
            # --- Obtener configuración desde settings.py ---
            GMAIL_IMAP_HOST = getattr(settings, 'GMAIL_IMAP_HOST', 'imap.gmail.com')
            GMAIL_USER = getattr(settings, 'GMAIL_USER', None)
            GMAIL_APP_PASSWORD = getattr(settings, 'GMAIL_APP_PASSWORD', None)
            GMAIL_FROM_KIU = getattr(settings, 'GMAIL_FROM_KIU', 'noreply@kiusys.com')

            if not all([GMAIL_USER, GMAIL_APP_PASSWORD]):
                self.stdout.write(self.style.ERROR("Error Crítico: Las variables de entorno GMAIL_USER y GMAIL_APP_PASSWORD no están configuradas en settings.py."))
                return

            # --- Conexión al servidor IMAP ---
            self.stdout.write(f"Conectando a {GMAIL_IMAP_HOST} como {GMAIL_USER}...")
            mail = imaplib.IMAP4_SSL(GMAIL_IMAP_HOST)
            mail.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            mail.select("inbox")
            self.stdout.write(self.style.SUCCESS("Conexión a Gmail exitosa."))

            # --- Búsqueda de correos no leídos ---
            search_criteria = f'(FROM "{GMAIL_FROM_KIU}" SUBJECT "E-TICKET ITINERARY RECEIPT" UNSEEN)'
            status, messages = mail.search(None, search_criteria)

            if status != "OK" or not messages[0]:
                self.stdout.write(self.style.SUCCESS("No se encontraron nuevos correos para procesar."))
                mail.logout()
                return

            email_ids = messages[0].split()
            self.stdout.write(self.style.WARNING(f"Se encontraron {len(email_ids)} correo(s) nuevo(s)."))
            
            processed_count = 0
            for email_id in email_ids:
                try:
                    self.stdout.write(f"--- Procesando email ID: {email_id.decode()} ---")
                    status, msg_data = mail.fetch(email_id, "(RFC822)")
                    if status != 'OK':
                        self.stdout.write(self.style.ERROR(f"No se pudo obtener el contenido del email ID {email_id.decode()}."))
                        continue

                    # Obtener el contenido en bytes del correo completo
                    raw_email_bytes = msg_data[0][1]

                    # Decodificar el asunto para el nombre del archivo
                    msg = email.message_from_bytes(raw_email_bytes)
                    subject, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding if encoding else 'utf-8')
                    
                    # Crear un nombre de archivo único y seguro
                    sanitized_subject = "".join(c for c in subject if c.isalnum() or c in (' ', '-')).rstrip()
                    filename = f"{sanitized_subject}_{email_id.decode()}.eml"

                    # Crear una instancia de BoletoImportado
                    boleto = BoletoImportado()
                    
                    # Usar ContentFile para guardar los bytes en memoria y asignarlos al FileField
                    boleto.archivo_boleto.save(filename, ContentFile(raw_email_bytes), save=True)
                    
                    self.stdout.write(self.style.SUCCESS(f"Boleto guardado con el ID {boleto.id_boleto_importado} y el archivo {filename}."))
                    self.stdout.write("El procesamiento automático (parseo) se ha iniciado en segundo plano.")

                    # Marcar el correo como leído
                    mail.store(email_id, '+FLAGS', '\\Seen')
                    self.stdout.write(f"Correo ID {email_id.decode()} marcado como leído.")
                    processed_count += 1

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error procesando el email ID {email_id.decode()}: {e}"))
                    import traceback
                    traceback.print_exc()
                    continue

            mail.logout()
            self.stdout.write(self.style.SUCCESS(f"Proceso completado. Se procesaron {processed_count} de {len(email_ids)} correos."))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Ocurrió un error crítico general: {e}"))
            import traceback
            traceback.print_exc()

