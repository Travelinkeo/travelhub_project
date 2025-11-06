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
    
    def __init__(self, notification_type='whatsapp', destination=None, interval=60, mark_as_read=False, process_all=False, force_reprocess=False):
        """
        Args:
            notification_type: 'whatsapp', 'email', 'whatsapp_drive'
            destination: Número de teléfono o email destino
            interval: Segundos entre verificaciones
            mark_as_read: Marcar correos como leídos
            process_all: Procesar todos los correos (incluso leídos)
            force_reprocess: Reprocesar boletos existentes
        """
        self.notification_type = notification_type
        self.destination = destination
        self.interval = interval
        self.mark_as_read = mark_as_read
        self.process_all = process_all
        self.force_reprocess = force_reprocess
        self.drive_service = None
        
        if notification_type == 'whatsapp_drive' and GOOGLE_DRIVE_AVAILABLE:
            self.drive_service = self._init_drive()

    def _init_drive(self):
        """Inicializa servicio de Google Drive"""
        try:
            SCOPES = ['https://www.googleapis.com/auth/drive.file']
            credentials = service_account.Credentials.from_service_account_file(
                settings.GOOGLE_APPLICATION_CREDENTIALS, scopes=SCOPES)
            return build('drive', 'v3', credentials=credentials)
        except Exception as e:
            logger.error(f"Error inicializando Drive: {e}")
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
        mail = imaplib.IMAP4_SSL(settings.GMAIL_IMAP_HOST)
        mail.login(settings.GMAIL_USER, settings.GMAIL_APP_PASSWORD)
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
        
        print(f"\n📧 Asunto: {subject}")
        print(f"   De: {from_addr}")
        
        # KIU: HTML/texto en el cuerpo (buscar variantes del asunto)
        subject_upper = subject.upper() if subject else ''
        from_lower = from_addr.lower() if from_addr else ''
        
        is_kiu_subject = ('E-TICKET ITINERARY RECEIPT' in subject_upper or 
                         'ETICKET ITINERARY RECEIPT' in subject_upper or
                         'PASSENGER ITINERARY RECEIPT' in subject_upper)
        is_kiu_sender = 'kiusys.com' in from_lower
        
        print(f"   KIU Subject: {is_kiu_subject}, KIU Sender: {is_kiu_sender}")
        
        if is_kiu_subject or is_kiu_sender:
            print("🎫 Procesando como KIU")
            return self._procesar_boleto_email(message, msg_num, mail_connection)
        
        # Otros: PDF adjunto
        tiene_pdf = self._tiene_pdf_adjunto(message)
        print(f"   PDF adjunto: {tiene_pdf}")
        
        if tiene_pdf:
            print("📎 Procesando PDF adjunto")
            return self._procesar_boleto_pdf(message, msg_num, mail_connection)
        
        print("⚠️ No reconocido como boleto")
        return False

    def _procesar_boleto_email(self, message, msg_num, mail_connection):
        """Procesa boleto desde HTML/texto del correo"""
        print("   🔍 Extrayendo texto/HTML...")
        texto = self._extraer_texto(message)
        html = self._extraer_html(message)
        
        # Si no hay texto pero hay HTML, extraer texto del HTML
        if not texto and html:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            texto = soup.get_text(separator='\n')
        
        print(f"   Texto: {len(texto) if texto else 0} chars, HTML: {len(html) if html else 0} chars")
        
        if not texto and not html:
            print("   ❌ No hay texto ni HTML")
            return False
        
        print("   🔧 Parseando datos...")
        datos = extract_data_from_text(texto, html)
        
        if datos.get('error'):
            print(f"   ❌ Error parseando: {datos['error']}")
            return False
        
        print(f"   ✅ Datos parseados: {datos.get('SOURCE_SYSTEM', 'UNKNOWN')}")
        return self._guardar_y_notificar(datos, msg_num, mail_connection)

    def _procesar_boleto_pdf(self, message, msg_num, mail_connection):
        """Procesa boleto desde PDF adjunto"""
        if not PYPDF2_AVAILABLE:
            logger.error("PyPDF2 no disponible")
            return False
        
        pdf_content = self._extraer_pdf(message)
        if not pdf_content:
            return False
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp.write(pdf_content)
            tmp_path = tmp.name
        
        try:
            with open(tmp_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                texto = '\n'.join(page.extract_text() for page in reader.pages)
            
            datos = extract_data_from_text(texto)
            
            if datos.get('error'):
                logger.warning(f"⚠️ PDF no parseado: {datos['error']}")
                return False
            
            return self._guardar_y_notificar(datos, msg_num, mail_connection)
        finally:
            os.unlink(tmp_path)

    def _guardar_y_notificar(self, datos, msg_num, mail_connection):
        """Guarda boleto y envía notificación"""
        from core.models import BoletoImportado
        
        sistema = datos.get('SOURCE_SYSTEM', 'UNKNOWN')
        print(f"   💾 Guardando boleto {sistema}...")
        
        # Extraer datos según sistema
        if sistema == 'SABRE':
            localizador = datos.get('reserva', {}).get('codigo_reservacion')
            numero_boleto = datos.get('reserva', {}).get('numero_boleto')
            pasajero = datos.get('pasajero', {}).get('nombre_completo')
            aerolinea = datos.get('reserva', {}).get('aerolinea_emisora')
        else:
            localizador = datos.get('SOLO_CODIGO_RESERVA') or datos.get('pnr')
            numero_boleto = datos.get('NUMERO_DE_BOLETO') or datos.get('numero_boleto')
            pasajero = datos.get('NOMBRE_DEL_PASAJERO') or datos.get('pasajero', {}).get('nombre_completo')
            aerolinea = datos.get('NOMBRE_AEROLINEA') or datos.get('reserva', {}).get('aerolinea_emisora')
        
        print(f"   Boleto: {numero_boleto}, PNR: {localizador}, Pasajero: {pasajero}")
        
        if not numero_boleto:
            print(f"   ❌ {sistema} sin número de boleto")
            return False
        
        # Guardar en BD
        try:
            print(f"   💾 Intentando guardar en BD...")
            
            # Buscar boleto existente (puede haber duplicados)
            boleto = BoletoImportado.objects.filter(numero_boleto=numero_boleto).first()
            
            if boleto:
                # Ya existe
                if not self.force_reprocess:
                    print(f"   ⏭️ Boleto {numero_boleto} ya existe en BD (usa --force para reprocesar)")
                    return False
                else:
                    print(f"   🔄 Boleto {numero_boleto} ya existe, reprocesando (--force)...")
                    # Actualizar datos
                    boleto.datos_parseados = datos
                    boleto.nombre_pasajero_completo = pasajero
                    boleto.localizador_pnr = localizador
                    boleto.aerolinea_emisora = aerolinea
                    boleto.save()
                    created = False
            else:
                # Crear nuevo - ya parseado, solo falta generar PDF
                boleto = BoletoImportado.objects.create(
                    numero_boleto=numero_boleto,
                    localizador_pnr=localizador,
                    nombre_pasajero_completo=pasajero,
                    formato_detectado=f'EML_{sistema[:3]}',
                    estado_parseo='COM',  # Ya parseado por el monitor
                    datos_parseados=datos,
                    aerolinea_emisora=aerolinea
                )
                created = True
            
            if created:
                print(f"   ✅ Boleto NUEVO guardado en BD (ID: {boleto.pk})")
            else:
                print(f"   ✅ Boleto ACTUALIZADO en BD (ID: {boleto.pk})")
        except Exception as e:
            print(f"   ❌ Error guardando boleto: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # Generar PDF profesional
        try:
            print(f"   📝 Generando PDF profesional...")
            pdf_bytes, pdf_filename = generate_ticket(datos)
            
            media_dir = os.path.join(settings.BASE_DIR, 'media', 'boletos_generados')
            os.makedirs(media_dir, exist_ok=True)
            pdf_path = os.path.join(media_dir, pdf_filename)
            
            with open(pdf_path, 'wb') as f:
                f.write(pdf_bytes)
            
            # Guardar referencia del PDF en el boleto
            from django.core.files import File
            with open(pdf_path, 'rb') as f:
                boleto.archivo_pdf_generado.save(pdf_filename, File(f), save=True)
            
            print(f"   ✅ PDF generado: {pdf_filename}")
        except Exception as e:
            print(f"   ❌ Error generando PDF: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # Enviar notificación
        resultado = self._enviar_notificacion(sistema, localizador, numero_boleto, pasajero, aerolinea, pdf_path, pdf_filename)
        
        if resultado and self.mark_as_read:
            mail_connection.store(msg_num, '+FLAGS', '\\Seen')
        
        return resultado

    def _enviar_notificacion(self, sistema, localizador, numero_boleto, pasajero, aerolinea, pdf_path, pdf_filename):
        """Envía notificación según el tipo configurado"""
        if self.notification_type == 'whatsapp':
            return self._enviar_whatsapp(sistema, localizador, numero_boleto, pasajero, aerolinea, pdf_filename)
        
        elif self.notification_type == 'email':
            return self._enviar_email(sistema, localizador, numero_boleto, pasajero, aerolinea, pdf_path)
        
        elif self.notification_type == 'whatsapp_drive':
            return self._enviar_whatsapp_drive(sistema, localizador, numero_boleto, pasajero, aerolinea, pdf_path)
        
        return False

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
                from_email=settings.EMAIL_HOST_USER,
                to=[self.destination]
            )
            
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
        """Verifica si el mensaje tiene PDF adjunto"""
        if message.is_multipart():
            for part in message.walk():
                if part.get_content_type() == 'application/pdf':
                    return True
        return False

    def _extraer_pdf(self, message):
        """Extrae el contenido del primer PDF adjunto"""
        if message.is_multipart():
            for part in message.walk():
                if part.get_content_type() == 'application/pdf':
                    return part.get_payload(decode=True)
        return None

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
