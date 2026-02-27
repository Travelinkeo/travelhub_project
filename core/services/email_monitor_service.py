"""
Monitor unificado de correos para captura automática de boletos
Consolida: email_monitor.py, email_monitor_v2.py, email_monitor_whatsapp_drive.py
"""
import imaplib
import email
import tempfile
import os
from pathlib import Path
from django.conf import settings
from django.core.mail import EmailMessage
from core.ticket_parser import extract_data_from_text, generate_ticket
from core.whatsapp_notifications import enviar_whatsapp
import time
import logging

logger = logging.getLogger(__name__)

try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False
    logger.warning("PyPDF2 no instalado")

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    GOOGLE_DRIVE_AVAILABLE = True
except ImportError:
    GOOGLE_DRIVE_AVAILABLE = False


class EmailMonitorService:
    """Monitor unificado de correos con múltiples canales de notificación"""
    
    def __init__(self, agencia, notification_type='whatsapp', destination=None, interval=60, mark_as_read=False, process_all=False, force_reprocess=False):
        """
        Args:
            agencia: Instancia de Agencia (con credenciales)
            notification_type: 'whatsapp', 'email', 'whatsapp_drive'
            destination: Número de teléfono o email destino
            interval: Segundos entre verificaciones
            mark_as_read: Marcar correos como leídos
            process_all: Procesar todos los correos (incluso leídos)
            force_reprocess: Reprocesar boletos existentes
        """
        self.agencia = agencia
        self.notification_type = notification_type
        self.destination = destination or agencia.whatsapp or agencia.email_ventas
        self.interval = interval
        self.mark_as_read = mark_as_read
        self.process_all = process_all
        self.force_reprocess = force_reprocess
        self.drive_service = None
        
        if notification_type == 'whatsapp_drive' and GOOGLE_DRIVE_AVAILABLE:
            self.drive_service = self._init_drive()

    def _init_drive(self):
        """Inicializa servicio de Google Drive (TODO: Adaptar para SaaS)"""
        try:
            # SaaS: Por ahora solo el servidor principal tiene credenciales de Drive (Service Account)
            # En el futuro, podríamos leer de self.agencia.configuracion_api['google_drive_json']
            if hasattr(settings, 'GOOGLE_APPLICATION_CREDENTIALS') and settings.GOOGLE_APPLICATION_CREDENTIALS:
                if os.path.exists(settings.GOOGLE_APPLICATION_CREDENTIALS):
                    SCOPES = ['https://www.googleapis.com/auth/drive.file']
                    credentials = service_account.Credentials.from_service_account_file(
                        settings.GOOGLE_APPLICATION_CREDENTIALS, scopes=SCOPES)
                    return build('drive', 'v3', credentials=credentials)
            
            return None
        except Exception as e:
            logger.warning(f"Google Drive no disponible para esta instancia: {e}")
            return None

    def procesar_una_vez(self):
        """Procesa correos una sola vez y retorna cantidad procesada"""
        logger.info(f"🔍 Procesando correos una vez -> {self.notification_type}: {self.destination}")
        return self._procesar_correos()
    
    def start(self):
        """Inicia el monitoreo continuo"""
        logger.info(f"🚀 Monitor iniciado -> {self.notification_type}: {self.destination}")
        
        while True:
            try:
                self._procesar_correos()
            except Exception as e:
                logger.error(f"❌ Error en ciclo: {e}")
            
            time.sleep(self.interval)

    def _procesar_correos(self):
        """Procesa correos no leídos y retorna cantidad procesada"""
        if not self.agencia.email_monitor_user or not self.agencia.email_monitor_password:
             logger.warning(f"⚠️ Agencia {self.agencia.nombre} no tiene credenciales de correo configuradas.")
             return 0

        mail = imaplib.IMAP4_SSL(settings.GMAIL_IMAP_HOST)
        try:
            mail.login(self.agencia.email_monitor_user, self.agencia.email_monitor_password)
        except Exception as e:
            logger.error(f"❌ Error Login IMAP Agencia {self.agencia.nombre}: {e}")
            return 0
        mail.select('inbox')
        
        # Buscar correos según configuración
        if self.process_all:
            _, messages = mail.search(None, 'ALL')
            logger.info("📦 Procesando TODOS los correos")
        else:
            _, messages = mail.search(None, '(UNSEEN)')
            logger.info("🆕 Procesando solo correos NO LEÍDOS")
        
        message_ids = messages[0].split()
        
        if not message_ids:
            logger.info("📭 No hay correos nuevos")
            mail.close()
            mail.logout()
            return 0
        
        logger.info(f"📬 Encontrados {len(message_ids)} correos nuevos")
        procesados = 0
        
        for num in message_ids:
            try:
                _, msg_data = mail.fetch(num, '(RFC822)')
                message = email.message_from_bytes(msg_data[0][1])
                
                if self._procesar_mensaje(message, num, mail):
                    logger.info(f"✅ Correo {num} procesado")
                    procesados += 1
            except Exception as e:
                logger.error(f"❌ Error procesando {num}: {e}")
        
        mail.close()
        mail.logout()
        return procesados

    def _procesar_mensaje(self, message, msg_num, mail_connection):
        """Procesa un mensaje individual"""
        subject = message.get('Subject', '')
        from_addr = message.get('From', '')
        
        # Decodificar asunto si está codificado
        if subject and subject.startswith('=?'):
            try:
                import email.header
                decoded = email.header.decode_header(subject)
                subject = ''.join([str(t[0], t[1] or 'utf-8') if isinstance(t[0], bytes) else t[0] for t in decoded])
            except:
                pass
        
        logger.info(f"Procesando: {subject[:50]}...")
        logger.info(f"De: {from_addr}")
        
        # KIU: HTML/texto en el cuerpo (buscar variantes del asunto)
        subject_upper = subject.upper() if subject else ''
        from_lower = from_addr.lower() if from_addr else ''
        
        is_kiu_subject = ('E-TICKET ITINERARY RECEIPT' in subject_upper or 
                         'ETICKET ITINERARY RECEIPT' in subject_upper or
                         'PASSENGER ITINERARY RECEIPT' in subject_upper or
                         'TICKETS AVIOR' in subject_upper or
                         'AVIOR AIRLINES' in subject_upper or
                         'LASER AIRLINES' in subject_upper or
                         'RUTACA' in subject_upper or
                         'VENEZOLANA' in subject_upper)
                         
        # Solo KIU oficial fuerza HTML. Reenvíos desde la agencia se tratan dinámicamente.
        is_official_kiu = 'kiusys.com' in from_lower
        
        logger.info(f"Es KIU Oficial: {is_official_kiu} | Subject Ticket: {is_kiu_subject}")
        
        # 1. Si es correo oficial de KIU, procesar como HTML (Mejor data)
        if is_official_kiu:
            logger.info("Procesando KIU Oficial (HTML)")
            return self._procesar_boleto_email(message, msg_num, mail_connection)
        
        # 2. Si no es oficial (reenvío), priorizar PDF (Caso Sabre/Otros)
        tiene_pdf = self._tiene_pdf_adjunto(message)
        logger.info(f"PDF adjunto: {tiene_pdf}")
        
        if tiene_pdf:
            logger.info("Procesando PDF adjunto (Prioridad Reenvío)")
            if self._procesar_boleto_pdf(message, msg_num, mail_connection):
                return True
            logger.warning("⚠️ Falló el procesamiento del PDF, intentando fallback a HTML...")
            
        # 3. Si no tiene PDF o falló, intentar como HTML si el asunto coincide (Reenvío KIU)
        if is_kiu_subject:
            logger.info("Procesando como KIU/HTML por Asunto")
            return self._procesar_boleto_email(message, msg_num, mail_connection)
        
        logger.warning("No reconocido como boleto")
        return False

    def _procesar_boleto_email(self, message, msg_num, mail_connection):
        """Procesa boleto desde HTML/texto del correo usando TicketParserService"""
        try:
            logger.info("📩 Procesando Email (Body/HTML)...")
            from core.models import BoletoImportado
            from django.core.files.base import ContentFile
            from core.services.ticket_parser_service import TicketParserService
            
            # 1. Extraer contenido para guardar como archivo .eml o .html de referencia
            texto = self._extraer_texto(message)
            html = self._extraer_html(message)
            
            if not texto and not html:
                logger.warning("No hay contenido en el mensaje")
                return False
                
            content = html if html else texto
            ext = 'html' if html else 'txt'
            filename = f"email_ticket_{msg_num}.{ext}"
            
            # 2. Crear BoletoImportado 'PENDIENTE'
            # Necesitamos el archivo físico para el parser unificado
            boleto = BoletoImportado(
                agencia=self.agencia,
                estado_parseo=BoletoImportado.EstadoParseo.PENDIENTE,
                formato_detectado='EMAIL_AUTO'
            )
            boleto.archivo_boleto.save(filename, ContentFile(content.encode('utf-8')))
            boleto.save()
            logger.info(f"📁 BoletoImportado creado: ID {boleto.pk}")

            # 3. Procesar con Servicio Unificado
            servicio = TicketParserService()
            resultado = servicio.procesar_boleto(boleto.pk)
            
            # 4. Manejar Resultado
            return self._manejar_resultado_procesamiento(boleto, resultado)

        except Exception as e:
            logger.exception(f"❌ Error crítico procesando email {msg_num}: {e}")
            return False

    def _procesar_boleto_pdf(self, message, msg_num, mail_connection):
        """Procesa todos los boletos desde PDFs adjuntos usando TicketParserService"""
        try:
            logger.info("📎 Investigando adjuntos PDF...")
            from core.models import BoletoImportado
            from django.core.files.base import ContentFile
            from core.services.ticket_parser_service import TicketParserService

            pdfs = self._extraer_adjuntos_pdf(message)
            if not pdfs:
                logger.error("No se encontraron PDFs adjuntos.")
                return False
            
            procesados_exito = 0
            for i, (filename, pdf_content) in enumerate(pdfs):
                logger.info(f"📄 Guardando PDF {i+1}/{len(pdfs)}: {filename}")
                
                final_filename = f"ticket_{msg_num}_{i}_{filename}"

                # 1. Crear BoletoImportado (Signal auto-triggers background processing)
                boleto = BoletoImportado(
                    agencia=self.agencia,
                    estado_parseo=BoletoImportado.EstadoParseo.PENDIENTE,
                    formato_detectado='PDF_AUTO'
                )
                boleto.archivo_boleto.save(final_filename, ContentFile(pdf_content))
                boleto.save()
                logger.info(f"📁 BoletoImportado ID {boleto.pk} guardado. Procesamiento en segundo plano iniciado por señal.")
                procesados_exito += 1
            
            return procesados_exito > 0
            
        except Exception as e:
            logger.exception(f"❌ Error crítico procesando PDFs {msg_num}: {e}")
            return False

    def _manejar_resultado_procesamiento(self, boleto, resultado):
        """Maneja la respuesta del Parser Service (Éxito, Error o Revisión)"""
        
        # Caso 1: Revisión Requerida (Datos faltantes como FOID)
        if isinstance(resultado, dict) and resultado.get('status') == 'REVIEW_REQUIRED':
            logger.warning(f"⚠️ BOLETO {boleto.pk} REQUIERE REVISIÓN MANUAL (Datos faltantes)")
            
            # Notificar al Agente que debe ingresar datos
            msg = (
                f"⚠️ <b>ACCIÓN REQUERIDA</b>\n\n"
                f"Hemos recibido un boleto pero faltan datos (Cédula/ID).\n"
                f"🆔 Boleto ID: {boleto.pk}\n\n"
                f"👉 Por favor ingresa al Dashboard para completarlo."
            )
            
            # Siempre enviamos a Telegram si está configurado (ya no usamos WhatsApp)
            from core.utils.telegram_utils import send_telegram_alert_sync
            send_telegram_alert_sync(msg)
            
            return True # Contamos como procesado porque ya entró al sistema

        # Caso 2: Exito (Venta creada u objeto retornado)
        if resultado:
             # Refrescar para tener datos actualizados
             boleto.refresh_from_db()
             
             # Datos para notificación
             sistema = boleto.formato_detectado
             localizador = boleto.localizador_pnr
             numero = boleto.numero_boleto
             pasajero = boleto.nombre_pasajero_completo
             aerolinea = boleto.aerolinea_emisora
             
             pdf_path = None
             pdf_filename = None
             if boleto.archivo_pdf_generado:
                 pdf_path = boleto.archivo_pdf_generado.path
                 pdf_filename = os.path.basename(pdf_path)
             
             # Notificar éxito
             logger.info(f"✅ Notificación centralizada manejada por el Servicio de Parseo para Boleto {boleto.pk}")
             
             # Enviar respaldo
             self._enviar_respaldo_email(boleto, pdf_path)
             
             return True

        # Caso 3: Fallo silente o desconocido
        logger.error(f"❌ Procesamiento falló para Boleto {boleto.pk}")
        return False

    def _enviar_respaldo_email(self, boleto, pdf_path):
        """Envía copia oculta de respaldo a soporte de la agencia"""
        try:
            # SaaS Fix: Usar email de soporte de la agencia en lugar de hardcode
            destino = self.agencia.email_soporte
            if not destino:
                return # Si no hay email de soporte, no enviamos respaldo
                
            email_msg = EmailMessage(
                subject=f'Boleto Auto (Respaldo) - {boleto.localizador_pnr}',
                body=f'Respaldo automático ID {boleto.pk} para {self.agencia.nombre}',
                from_email=self.agencia.email_principal or settings.EMAIL_HOST_USER,
                to=[destino]
            )
            if pdf_path and os.path.exists(pdf_path):
                email_msg.attach_file(pdf_path)
            email_msg.send()
        except Exception as e:
            logger.warning(f"Error enviando respaldo email: {e}")

    def _enviar_notificacion(self, sistema, localizador, numero_boleto, pasajero, aerolinea, pdf_path, pdf_filename):
        """Envía notificación usando Telegram (Por defecto) o Email"""
        
        # Prioridad absoluta a Telegram para mensajería instantánea
        if self.notification_type == 'telegram' or self.notification_type == 'whatsapp': # Fallback whatsapp -> telegram
            return self._enviar_telegram(sistema, localizador, numero_boleto, pasajero, aerolinea, pdf_path)

        elif self.notification_type == 'email':
            return self._enviar_email(sistema, localizador, numero_boleto, pasajero, aerolinea, pdf_path)
        
        return False

    def _enviar_telegram(self, sistema, localizador, numero_boleto, pasajero, aerolinea, pdf_path):
        """Envía notificación por Telegram con el PDF adjunto"""
        from core.utils.telegram_utils import send_telegram_file_sync
        
        mensaje = (
            f"✈️ <b>Boleto {sistema} Procesado</b>\n\n"
            f"📍 PNR: <code>{localizador or 'N/A'}</code>\n"
            f"🎫 Boleto: {numero_boleto}\n"
            f"👤 Pasajero: {pasajero or 'N/A'}\n"
            f"✈️ Aerolínea: {aerolinea or 'N/A'}\n\n"
            f"<i>TravelHub - Oficina Digital</i>"
        )
        
        logger.info(f"📤 Enviando Telegram a Admin...")
        return send_telegram_file_sync(pdf_path, caption=mensaje)


    def _enviar_whatsapp(self, sistema, localizador, numero_boleto, pasajero, aerolinea, pdf_filename):
        """Envía notificación por WhatsApp"""
        mensaje = f"""✈️ *Boleto {sistema} Procesado*

📍 PNR: *{localizador or 'N/A'}*
🎫 Boleto: {numero_boleto}
👤 Pasajero: {pasajero or 'N/A'}
✈️ Aerolínea: {aerolinea or 'N/A'}
📄 PDF: {pdf_filename}

_TravelHub - Sistema Automático_"""
        
        return enviar_whatsapp(self.destination, mensaje)

    def _enviar_email(self, sistema, localizador, numero_boleto, pasajero, aerolinea, pdf_path):
        """Envía notificación por Email"""
        try:
            email_msg = EmailMessage(
                subject=f'Boleto {sistema} Procesado - {localizador}',
                body=f'''Boleto procesado automáticamente:

Sistema: {sistema}
PNR: {localizador}
Boleto: {numero_boleto}
Pasajero: {pasajero}
Aerolínea: {aerolinea}

PDF adjunto.

TravelHub - Sistema Automático''',
                to=[self.destination]
            )
            
            # SaaS Fix: Configurar From Email si la agencia tiene SMTP propio
            if self.agencia.email_principal:
                email_msg.from_email = self.agencia.email_principal
            
            email_msg.attach_file(pdf_path)
            email_msg.send()
            
            logger.info(f"✅ Email enviado: {numero_boleto}")
            return True
        except Exception as e:
            logger.error(f"❌ Error enviando email: {e}")
            return False

    def _enviar_whatsapp_drive(self, sistema, localizador, numero_boleto, pasajero, aerolinea, pdf_path):
        """Envía notificación por WhatsApp con link de Google Drive"""
        drive_link = self._upload_to_drive(pdf_path)
        
        if drive_link:
            mensaje = f"""✈️ *Boleto {sistema} Procesado*

📍 PNR: *{localizador or 'N/A'}*
🎫 Boleto: {numero_boleto}
👤 Pasajero: {pasajero or 'N/A'}
✈️ Aerolínea: {aerolinea or 'N/A'}

📥 Descarga tu PDF:
{drive_link}

_TravelHub - Sistema Automático_"""
        else:
            mensaje = f"""✈️ *Boleto {sistema} Procesado*

📍 PNR: *{localizador or 'N/A'}*
🎫 Boleto: {numero_boleto}
👤 Pasajero: {pasajero or 'N/A'}

📄 PDF guardado localmente

_TravelHub - Sistema Automático_"""
        
        return enviar_whatsapp(self.destination, mensaje)

    def _upload_to_drive(self, pdf_path):
        """Sube PDF a Google Drive y retorna link público"""
        if not self.drive_service:
            return None
        
        try:
            file_metadata = {
                'name': os.path.basename(pdf_path),
                'mimeType': 'application/pdf'
            }
            
            media = MediaFileUpload(pdf_path, mimetype='application/pdf')
            
            file = self.drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            file_id = file.get('id')
            
            # Hacer público
            self.drive_service.permissions().create(
                fileId=file_id,
                body={'type': 'anyone', 'role': 'reader'}
            ).execute()
            
            return f"https://drive.google.com/uc?export=download&id={file_id}"
        except Exception as e:
            logger.error(f"❌ Error subiendo a Drive: {e}")
            return None

    def _tiene_pdf_adjunto(self, message):
        """Verifica si el mensaje tiene PDF adjunto (por Content-Type o nombre)"""
        if message.is_multipart():
            for part in message.walk():
                ctype = part.get_content_type()
                filename = part.get_filename() or ""
                
                # Debug logging para entender qué está llegando
                logger.debug(f"Parte MIME: {ctype} - Filename: {filename}")
                
                if ctype == 'application/pdf':
                    return True
                if filename.lower().endswith('.pdf'):
                    return True
        return False

    def _extraer_adjuntos_pdf(self, message):
        """Extrae el contenido de todos los PDF adjuntos"""
        pdfs = []
        if message.is_multipart():
            for part in message.walk():
                ctype = part.get_content_type()
                filename = part.get_filename() or "adjunto.pdf"
                
                # Check for PDF by type OR extension
                is_pdf = (ctype == 'application/pdf') or (filename.lower().endswith('.pdf'))
                
                if is_pdf:
                    payload = part.get_payload(decode=True)
                    if payload:
                         pdfs.append((filename, payload))
        return pdfs

    def _extraer_pdf(self, message):
        """Extrae el contenido del primer PDF adjunto (Retrocompatibilidad)"""
        pdfs = self._extraer_adjuntos_pdf(message)
        return pdfs[0][1] if pdfs else None

    def _extraer_texto(self, message):
        """Extrae texto plano del email"""
        if message.is_multipart():
            for part in message.walk():
                if part.get_content_type() == "text/plain":
                    return part.get_payload(decode=True).decode('utf-8', errors='ignore')
        else:
            return message.get_payload(decode=True).decode('utf-8', errors='ignore')
        return None
    
    def _extraer_html(self, message):
        """Extrae HTML del email"""
        if message.is_multipart():
            for part in message.walk():
                if part.get_content_type() == "text/html":
                    return part.get_payload(decode=True).decode('utf-8', errors='ignore')
        else:
            content = message.get_payload(decode=True).decode('utf-8', errors='ignore')
            if '<HTML>' in content.upper():
                return content
        return None
