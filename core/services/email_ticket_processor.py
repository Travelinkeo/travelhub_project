"""
Sistema de procesamiento automático de boletos desde correo electrónico
"""
import imaplib
import email
from email.header import decode_header
import logging
from django.conf import settings
from django.core.files.base import ContentFile
from datetime import datetime
import os

from ..services.ticket_parser_service import orquestar_parseo_de_boleto
from ..models.boletos import BoletoImportado
from ..whatsapp_notifications import enviar_whatsapp

logger = logging.getLogger(__name__)

# Remitentes autorizados
REMITENTES_AUTORIZADOS = [
    'noreply@kiusys.com',
    'ww@kiusys.com',
    'emisiones@grupoctg.com',
    'ventas1mydestiny@gmail.com',
    'ventas2mydestiny@gmail.com',
    'ventas3mydestiny@gmail.com',
    'ventas4mydestiny@gmail.com',
    'travelinkeo@gmail.com',
    'viajes.travelinkeo@gmail.com'
]


def conectar_email():
    """Conecta al servidor de correo Gmail"""
    try:
        email_user = getattr(settings, 'EMAIL_HOST_USER', None)
        email_pass = getattr(settings, 'EMAIL_HOST_PASSWORD', None)
        
        if not email_user or not email_pass:
            logger.error("Credenciales de email no configuradas")
            return None
        
        mail = imaplib.IMAP4_SSL('imap.gmail.com')
        mail.login(email_user, email_pass)
        return mail
        
    except Exception as e:
        logger.error(f"Error conectando al correo: {e}")
        return None


def extraer_remitente(msg):
    """Extrae el email del remitente"""
    from_header = msg.get('From', '')
    if '<' in from_header and '>' in from_header:
        return from_header.split('<')[1].split('>')[0].lower()
    return from_header.lower()


def extraer_contenido_correo(msg):
    """Extrae el contenido del correo (texto/HTML) y adjuntos PDF"""
    contenido = {'texto': '', 'html': '', 'adjuntos': []}
    
    for part in msg.walk():
        content_type = part.get_content_type()
        
        # Extraer texto plano
        if content_type == 'text/plain':
            try:
                payload = part.get_payload(decode=True)
                charset = part.get_content_charset() or 'utf-8'
                contenido['texto'] = payload.decode(charset, errors='ignore')
            except:
                pass
        
        # Extraer HTML
        elif content_type == 'text/html':
            try:
                payload = part.get_payload(decode=True)
                charset = part.get_content_charset() or 'utf-8'
                contenido['html'] = payload.decode(charset, errors='ignore')
            except:
                pass
        
        # Extraer adjuntos PDF
        elif part.get('Content-Disposition') is not None:
            filename = part.get_filename()
            if filename and filename.lower().endswith('.pdf'):
                decoded = decode_header(filename)
                filename = decoded[0][0]
                if isinstance(filename, bytes):
                    filename = filename.decode()
                
                contenido['adjuntos'].append({
                    'filename': filename,
                    'data': part.get_payload(decode=True)
                })
    
    return contenido


def procesar_boleto_contenido(contenido, remitente, es_adjunto=True):
    """Procesa un boleto desde adjunto o contenido del correo"""
    try:
        from django.core.files.uploadedfile import InMemoryUploadedFile
        from io import BytesIO
        
        if es_adjunto:
            # Procesar adjunto PDF
            archivo = InMemoryUploadedFile(
                BytesIO(contenido['data']),
                None,
                contenido['filename'],
                'application/pdf',
                len(contenido['data']),
                None
            )
        else:
            # Procesar contenido del correo (KIU)
            # Crear archivo temporal con el contenido
            texto_boleto = contenido.get('html') or contenido.get('texto')
            if not texto_boleto:
                return None
            
            archivo = InMemoryUploadedFile(
                BytesIO(texto_boleto.encode('utf-8')),
                None,
                f'boleto_kiu_{datetime.now().strftime("%Y%m%d%H%M%S")}.txt',
                'text/plain',
                len(texto_boleto.encode('utf-8')),
                None
            )
        
        # Parsear boleto
        datos_parseados, mensaje = orquestar_parseo_de_boleto(archivo)
        
        if not datos_parseados:
            logger.error(f"Error parseando boleto: {mensaje}")
            return None
        
        # Guardar en base de datos
        boleto = BoletoImportado.objects.create(
            archivo_boleto=archivo,
            datos_parseados=datos_parseados
        )
        
        logger.info(f"Boleto procesado exitosamente: {boleto.id_boleto_importado}")
        
        # Generar PDF
        from ..ticket_parser import generate_ticket
        pdf_bytes, pdf_filename = generate_ticket(datos_parseados)
        
        if pdf_bytes:
            boleto.archivo_pdf_generado.save(pdf_filename, ContentFile(pdf_bytes), save=True)
            logger.info(f"PDF generado: {pdf_filename}")
        
        return boleto
        
    except Exception as e:
        logger.error(f"Error procesando boleto: {e}", exc_info=True)
        return None


def enviar_boleto_whatsapp(boleto, telefono='+584126080861'):
    """Envía el boleto generado por WhatsApp"""
    # Extraer información del boleto
    datos = boleto.datos_parseados
    source_system = datos.get('SOURCE_SYSTEM', 'N/A')
    
    # Obtener PNR según el sistema
    if source_system == 'KIU':
        pnr = datos.get('SOLO_CODIGO_RESERVA', datos.get('pnr', 'N/A'))
        pasajero_nombre = datos.get('SOLO_NOMBRE_PASAJERO', datos.get('NOMBRE_DEL_PASAJERO', 'N/A'))
        numero_boleto = datos.get('NUMERO_DE_BOLETO', 'N/A')
    else:
        pnr = datos.get('pnr', 'N/A')
        pasajero_nombre = datos.get('pasajero', {}).get('nombre_completo', 'N/A')
        numero_boleto = datos.get('numero_boleto', 'N/A')
    
    mensaje = f"""
TravelHub - Boleto Procesado

Estimado/a {pasajero_nombre},

Su boleto ha sido procesado exitosamente.

Detalles:
- PNR: {pnr}
- Boleto: {numero_boleto}
- Sistema: {source_system}

El PDF ha sido generado y guardado en el sistema.

Equipo TravelHub
""".strip()
    
    return enviar_whatsapp(telefono, mensaje)


def leer_correos_no_leidos():
    """Lee correos no leídos de remitentes autorizados y procesa boletos"""
    mail = conectar_email()
    if not mail:
        return
    
    try:
        mail.select('INBOX')
        
        # Buscar correos no leídos
        status, messages = mail.search(None, 'UNSEEN')
        
        if status != 'OK':
            logger.error("Error buscando correos")
            return
        
        email_ids = messages[0].split()
        logger.info(f"Encontrados {len(email_ids)} correos no leídos")
        
        boletos_procesados = []
        
        for email_id in email_ids:
            try:
                # Obtener correo
                status, msg_data = mail.fetch(email_id, '(RFC822)')
                
                if status != 'OK':
                    continue
                
                msg = email.message_from_bytes(msg_data[0][1])
                remitente = extraer_remitente(msg)
                
                # Verificar si es remitente autorizado
                if remitente not in REMITENTES_AUTORIZADOS:
                    logger.debug(f"Remitente no autorizado: {remitente}")
                    continue
                
                logger.info(f"Procesando correo de {remitente}")
                
                # Extraer contenido
                contenido = extraer_contenido_correo(msg)
                
                # Procesar adjuntos PDF
                for adjunto in contenido['adjuntos']:
                    boleto = procesar_boleto_contenido(adjunto, remitente, es_adjunto=True)
                    if boleto:
                        boletos_procesados.append(boleto)
                        # Enviar notificación por WhatsApp
                        try:
                            enviar_boleto_whatsapp(boleto)
                            logger.info(f"WhatsApp enviado para boleto {boleto.id_boleto_importado}")
                        except Exception as e:
                            logger.error(f"Error enviando WhatsApp: {e}")
                
                # Si no hay adjuntos y es de KIU, procesar contenido del correo
                if not contenido['adjuntos'] and remitente in ['noreply@kiusys.com', 'ww@kiusys.com']:
                    logger.info("Procesando contenido del correo KIU...")
                    boleto = procesar_boleto_contenido(contenido, remitente, es_adjunto=False)
                    if boleto:
                        boletos_procesados.append(boleto)
                        # Enviar notificación por WhatsApp
                        try:
                            enviar_boleto_whatsapp(boleto)
                            logger.info(f"WhatsApp enviado para boleto {boleto.id_boleto_importado}")
                        except Exception as e:
                            logger.error(f"Error enviando WhatsApp: {e}")
                
            except Exception as e:
                logger.error(f"Error procesando correo {email_id}: {e}")
                continue
        
        logger.info(f"Procesados {len(boletos_procesados)} boletos")
        return boletos_procesados
        
    except Exception as e:
        logger.error(f"Error en leer_correos_no_leidos: {e}")
        return []
        
    finally:
        try:
            mail.close()
            mail.logout()
        except:
            pass
