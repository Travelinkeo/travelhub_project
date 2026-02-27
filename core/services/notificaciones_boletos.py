"""
Sistema de notificaciones proactivas para boletos
"""
import logging
from datetime import datetime, timedelta
from django.utils import timezone
from core.whatsapp_notifications import enviar_whatsapp
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)


def notificar_boleto_procesado(boleto):
    """
    Notifica al cliente cuando su boleto está listo
    """
    # Relaxed check: Allow notification even without Venta (Admin needs to know)
    agencia_nombre = "TravelHub"
    cliente = None
    
    if boleto.venta_asociada:
        venta = boleto.venta_asociada
        cliente = venta.cliente
        agencia_nombre = venta.agencia.nombre if venta.agencia else "TravelHub"
    
    # Extraer datos del boleto
    datos = boleto.datos_parseados.get('normalized', {}) if boleto.datos_parseados else {}
    pnr = datos.get('reservation_code', boleto.localizador_pnr or 'N/A')
    pasajero = datos.get('passenger_name', boleto.nombre_pasajero_procesado or 'N/A')
    
    # pnr duplicate lines removed
    
    print(f"DEBUG: notificar_boleto_procesado called for boleto {boleto.pk}")
    
    # WhatsApp (OVERRIDE: Send to Admin always)
    admin_phone = getattr(settings, 'ADMIN_WHATSAPP_NUMBER', '+584126080861')
    is_enabled = getattr(settings, 'WHATSAPP_NOTIFICATIONS_ENABLED', False)
    
    print(f"DEBUG: WhatsApp Enabled: {is_enabled}, Admin: {admin_phone}")

    if is_enabled and admin_phone:
        # agencia_nombre already defined above
        
        mensaje = f"""✈️ *Boleto Generado - {agencia_nombre}*

Estimado Armando,

Se ha procesado un nuevo boleto de forma automática.

📋 *Detalles:*
• PNR: *{pnr}*
• Pasajero: {pasajero}
• Aerolínea: {boleto.aerolinea_emisora or 'N/A'}
• Boleto: {boleto.numero_boleto}
"""

        # Generar URL completa del PDF
        pdf_url = ""
        try:
            if boleto.archivo_pdf_generado:
                # Si estamos en Cloudinary/S3, .url ya trae el link completo
                try:
                    pdf_url = boleto.archivo_pdf_generado.url
                except:
                    # Fallback para FileSystemStorage local si .url falla o es relativo
                    pdf_url = f"{settings.MEDIA_URL if 'http' in settings.MEDIA_URL else 'https://travelhub.travelinkeo.com' + settings.MEDIA_URL}{boleto.archivo_pdf_generado.name}"
                
                # Asegurar que sea absoluto para Twilio
                if pdf_url and not pdf_url.startswith('http'):
                     pdf_url = f"https://travelhub.travelinkeo.com{pdf_url}"

                print(f"DEBUG: Generated PDF URL: {pdf_url}")
            else:
                print("DEBUG: No PDF file generated in boleto object")
        except Exception as e:
            print(f"DEBUG: Error generating PDF URL: {e}")
            pdf_url = ""

        # Send with explicit result logging
        success = enviar_whatsapp(admin_phone, mensaje, media_url=pdf_url)
        if success:
             logger.info(f"WhatsApp de notificación enviado a Admin ({admin_phone})")
             print("DEBUG: WhatsApp sent successfully")
        else:
             logger.error(f"Failed to send WhatsApp to Admin ({admin_phone})")
             print("DEBUG: WhatsApp failed to send")
    else:
        print("DEBUG: WhatsApp skipped - Disabled or No Admin Phone")
    
    # Email
    if cliente and cliente.email:
        # 🛡️ Guard: Skip placeholder emails to avoid bounce-backs
        if "@sin-email.com" in cliente.email.lower():
            logger.info(f"🔕 Notificación omitida para email de marcador de posición: {cliente.email}")
            return True

        try:
            send_mail(
                subject=f'Boleto Listo - PNR {pnr}',
                message=f'Su boleto para {pasajero} está listo. PNR: {pnr}',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[cliente.email],
                fail_silently=True
            )
        except Exception as e:
            logger.error(f"Error enviando email: {e}")
    
    return True


def enviar_recordatorio_vuelo(boleto, horas_antes=24):
    """
    Envía recordatorio X horas antes del vuelo
    """
    if not boleto.venta_asociada or not boleto.venta_asociada.cliente:
        return False
    
    venta = boleto.venta_asociada
    cliente = venta.cliente
    
    # Extraer datos
    datos = boleto.datos_parseados.get('normalized', {}) if boleto.datos_parseados else {}
    pnr = datos.get('reservation_code', boleto.localizador_pnr or 'N/A')
    pasajero = datos.get('passenger_name', boleto.nombre_pasajero_procesado or 'N/A')
    
    # Obtener primer vuelo
    vuelos = datos.get('flights', [])
    if not vuelos:
        return False
    
    primer_vuelo = vuelos[0]
    origen = primer_vuelo.get('origin', 'N/A')
    destino = primer_vuelo.get('destination', 'N/A')
    fecha = primer_vuelo.get('date', 'N/A')
    hora = primer_vuelo.get('time', 'N/A')
    
    if cliente.telefono_principal:
        mensaje = f"""⏰ *Recordatorio de Vuelo - TravelHub*

Estimado/a *{cliente.get_nombre_completo()}*,

Su vuelo sale en {horas_antes} horas.

✈️ *Detalles del Vuelo:*
• PNR: *{pnr}*
• Pasajero: {pasajero}
• Ruta: {origen} → {destino}
• Fecha: {fecha}
• Hora: {hora}
• Aerolínea: {boleto.aerolinea_emisora or 'N/A'}

💡 *Recomendaciones:*
• Llegue al aeropuerto 3 horas antes
• Tenga su documento de identidad
• Verifique el peso de su equipaje

¡Buen viaje!

_TravelHub_"""
        
        enviar_whatsapp(cliente.telefono_principal, mensaje)
        return True
    
    return False
