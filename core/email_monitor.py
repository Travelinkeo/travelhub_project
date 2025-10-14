"""
Sistema de monitoreo de correos para captura automática de boletos
y envío por WhatsApp
"""
import imaplib
import email
import tempfile
import os
from pathlib import Path
from django.conf import settings
from core.ticket_parser import parse_ticket
from core.services.pdf_service import generate_ticket_pdf
from core.whatsapp_notifications import enviar_whatsapp
import time
import logging

logger = logging.getLogger(__name__)

try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False
    logger.warning("PyPDF2 no instalado. Instala con: pip install PyPDF2")


def enviar_documento_whatsapp(to_number, document_path, caption=""):
    """
    Envía un documento PDF por WhatsApp usando Twilio
    
    Args:
        to_number: Número en formato +584121234567
        document_path: Ruta al archivo PDF
        caption: Texto del mensaje
    
    Returns:
        dict con 'success' y 'error' o 'sid'
    """
    try:
        from twilio.rest import Client
        
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        
        # Subir el archivo a Twilio (necesita URL pública o usar media_url)
        # Por ahora enviamos solo el mensaje de texto
        # TODO: Implementar subida de archivo a servidor público o usar Twilio media
        
        if not to_number.startswith('whatsapp:'):
            to_number = f'whatsapp:{to_number}'
        
        twilio_number = settings.TWILIO_WHATSAPP_NUMBER
        if not twilio_number.startswith('whatsapp:'):
            twilio_number = f'whatsapp:{twilio_number}'
        
        message = client.messages.create(
            from_=twilio_number,
            body=caption,
            to=to_number
        )
        
        logger.info(f"✅ Documento enviado a {to_number}: {message.sid}")
        return {'success': True, 'sid': message.sid}
        
    except Exception as e:
        logger.error(f"❌ Error enviando documento: {e}")
        return {'success': False, 'error': str(e)}


class MonitorTicketsWhatsApp:
    """Monitor de correos para captura automática de boletos"""
    
    def __init__(self, phone_number, interval=60, mark_as_read=False):
        self.phone_number = phone_number
        self.interval = interval
        self.mark_as_read = mark_as_read

    def start(self):
        """Inicia el monitoreo continuo"""
        logger.info(f"🚀 Iniciando monitor de boletos -> WhatsApp {self.phone_number}")
        
        while True:
            try:
                self._procesar_correos()
            except Exception as e:
                logger.error(f"❌ Error en ciclo de monitoreo: {e}")
            
            time.sleep(self.interval)

    def _procesar_correos(self):
        """Procesa correos no leídos"""
        mail = imaplib.IMAP4_SSL(settings.GMAIL_IMAP_HOST)
        mail.login(settings.GMAIL_USER, settings.GMAIL_APP_PASSWORD)
        mail.select('inbox')
        
        _, messages = mail.search(None, '(UNSEEN)')
        
        for num in messages[0].split():
            try:
                _, msg_data = mail.fetch(num, '(RFC822)')
                message = email.message_from_bytes(msg_data[0][1])
                
                if self._procesar_mensaje(message, num, mail):
                    logger.info(f"✅ Correo {num} procesado exitosamente")
            except Exception as e:
                logger.error(f"❌ Error procesando correo {num}: {e}")
        
        mail.close()
        mail.logout()

    def _procesar_mensaje(self, message, msg_num, mail_connection):
        """Procesa un mensaje individual"""
        subject = message.get('Subject', '')
        from_addr = message.get('From', '')
        
        # KIU: Texto plano en el cuerpo
        if 'E-TICKET ITINERARY RECEIPT' in subject and 'kiusys.com' in from_addr.lower():
            return self._procesar_kiu(message, msg_num, mail_connection)
        
        # SABRE: PDF adjunto (cualquier remitente)
        if self._tiene_pdf_adjunto(message):
            return self._procesar_sabre(message, msg_num, mail_connection)
        
        return False

    def _procesar_kiu(self, message, msg_num, mail_connection):
        """Procesa boleto KIU desde texto del correo"""
        texto = self._extraer_texto(message)
        if not texto:
            return False
        
        datos = parse_ticket(texto)
        
        if datos.get('error'):
            logger.warning(f"⚠️ KIU no parseado: {datos['error']}")
            return False
        
        localizador = datos.get('codigo_reservacion')
        if not localizador:
            logger.warning("⚠️ KIU sin localizador")
            return False
        
        # Buscar o crear Venta
        from core.models import Venta
        venta, created = self._obtener_o_crear_venta(localizador, datos, 'KIU')
        
        if not created:
            logger.info(f"⏭️ Venta KIU {localizador} ya existe")
            return False
        
        # Generar PDF
        pdf_path = generate_ticket_pdf(datos)
        
        # Enviar por WhatsApp
        resultado = enviar_documento_whatsapp(
            to_number=self.phone_number,
            document_path=pdf_path,
            caption=f"✈️ Boleto KIU\n📍 {localizador}"
        )
        
        if resultado['success'] and self.mark_as_read:
            mail_connection.store(msg_num, '+FLAGS', '\\Seen')
        
        return resultado['success']

    def _procesar_sabre(self, message, msg_num, mail_connection):
        """Procesa boleto SABRE desde PDF adjunto con actualización automática"""
        if not PYPDF2_AVAILABLE:
            logger.error("PyPDF2 no disponible, no se puede procesar SABRE")
            return False
        
        pdf_content = self._extraer_pdf(message)
        if not pdf_content:
            return False
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp.write(pdf_content)
            tmp_path = tmp.name
        
        try:
            # Extraer texto del PDF
            with open(tmp_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                texto = '\n'.join(page.extract_text() for page in reader.pages)
            
            # Parser detecta automáticamente el GDS
            datos = parse_ticket(texto)
            
            if datos.get('error') or datos.get('SOURCE_SYSTEM') != 'SABRE':
                logger.info(f"⏭️ PDF ignorado: no es SABRE válido")
                return False
            
            localizador = datos.get('codigo_reservacion')
            if not localizador:
                logger.warning("⚠️ SABRE sin localizador")
                return False
            
            # Buscar si ya existe
            from core.models import Venta
            venta_existente = Venta.objects.filter(localizador=localizador).first()
            
            normalized = datos.get('normalized', {})
            tiene_tarifas = bool(normalized.get('total_amount') or normalized.get('fare_amount'))
            
            if venta_existente:
                # Actualizar si tiene tarifas nuevas
                if tiene_tarifas and not venta_existente.total_venta:
                    logger.info(f"🔄 Actualizando Venta {localizador} con tarifas")
                    self._actualizar_venta_con_tarifas(venta_existente, datos)
                    enviar = True
                    caption_extra = " (Actualizado)"
                else:
                    logger.info(f"⏭️ Venta {localizador} ya existe, sin cambios relevantes")
                    return False
            else:
                # Nueva venta
                logger.info(f"✨ Nueva Venta SABRE: {localizador}")
                venta_existente = self._obtener_o_crear_venta(localizador, datos, 'SABRE')[0]
                enviar = tiene_tarifas
                caption_extra = ""
            
            # Generar y enviar PDF solo si hay cambios
            if enviar:
                pdf_path = generate_ticket_pdf(datos)
                
                resultado = enviar_documento_whatsapp(
                    to_number=self.phone_number,
                    document_path=pdf_path,
                    caption=f"✈️ Boleto SABRE{caption_extra}\n📍 {localizador}"
                )
                
                if resultado['success'] and self.mark_as_read:
                    mail_connection.store(msg_num, '+FLAGS', '\\Seen')
                
                return resultado['success']
            
            return True
        
        finally:
            os.unlink(tmp_path)

    def _obtener_o_crear_venta(self, localizador, datos, gds):
        """Crea una Venta desde los datos parseados"""
        from core.models import Venta, VentaParseMetadata
        
        normalized = datos.get('normalized', {})
        
        venta, created = Venta.objects.get_or_create(
            localizador=localizador,
            defaults={
                'total_venta': float(normalized.get('total_amount', 0)) if normalized.get('total_amount') else 0,
                'estado': 'PEN',
            }
        )
        
        if created:
            # Guardar metadata de parseo
            VentaParseMetadata.objects.create(
                venta=venta,
                raw_data=datos,
                source_system=gds,
                amount_consistency=normalized.get('amount_consistency'),
                amount_difference=normalized.get('amount_difference'),
                segments_json=normalized.get('segments', [])
            )
        
        return venta, created

    def _actualizar_venta_con_tarifas(self, venta, datos):
        """Actualiza una Venta existente con tarifas del boleto corregido"""
        from core.models import VentaParseMetadata
        
        normalized = datos.get('normalized', {})
        
        if normalized.get('total_amount'):
            venta.total_venta = float(normalized['total_amount'])
            venta.save()
        
        # Actualizar metadata
        VentaParseMetadata.objects.update_or_create(
            venta=venta,
            defaults={
                'raw_data': datos,
                'source_system': 'SABRE',
                'amount_consistency': normalized.get('amount_consistency'),
                'amount_difference': normalized.get('amount_difference'),
                'segments_json': normalized.get('segments', [])
            }
        )
        
        logger.info(f"✅ Venta {venta.localizador} actualizada con tarifas")

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
