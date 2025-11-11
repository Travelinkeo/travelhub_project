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
    if not boleto.venta_asociada or not boleto.venta_asociada.cliente:
        return False
    
    venta = boleto.venta_asociada
    cliente = venta.cliente
    
    # Extraer datos del boleto
    datos = boleto.datos_parseados.get('normalized', {}) if boleto.datos_parseados else {}
    pnr = datos.get('reservation_code', boleto.localizador_pnr or 'N/A')
    pasajero = datos.get('passenger_name', boleto.nombre_pasajero_procesado or 'N/A')
    
    # WhatsApp
    if cliente.telefono_principal:
        mensaje = f"""✈️ *Boleto Listo - TravelHub*

Estimado/a *{cliente.get_nombre_completo()}*,

Su boleto ha sido procesado exitosamente.

📋 *Detalles:*
• PNR: *{pnr}*
• Pasajero: {pasajero}
• Aerolínea: {boleto.aerolinea_emisora or 'N/A'}

📄 Puede descargar su boleto desde su panel de cliente.

¡Buen viaje!

_TravelHub - Su agencia de confianza_"""
        
        enviar_whatsapp(cliente.telefono_principal, mensaje)
    
    # Email
    if cliente.email:
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
