"""
WhatsApp Unified Service
Consolidated service for all WhatsApp operations:
- Message sending (Evolution API + Meta Cloud API fallback)
- Session/QR management (Evolution API wrapper)
- Notifications (Twilio + templates)
- AI Bot (inbound message processing + CRM lead creation)
"""
import logging
import os
from typing import Any

import requests
from django.conf import settings

from apps.common.services.circuit_breaker import whatsapp_circuit_breaker
from apps.communications.services.evolution_api_service import EvolutionService

logger = logging.getLogger(__name__)

# ============================================================================
# SECTION 1: MESSAGE SENDING (Evolution + Meta Fallback)
# ============================================================================

def enviar_mensaje_meta_api(numero_cliente: str, mensaje: str, agencia=None) -> dict[str, Any]:
    """
    Envía mensajes a través de WhatsApp Cloud API (Meta).
    Mantenido como fallback para mensajes de texto.
    """
    try:
        token = settings.WHATSAPP_TOKEN
        phone_id = settings.WHATSAPP_PHONE_ID

        if agencia and hasattr(agencia, 'configuracion_api') and agencia.configuracion_api:
            token = agencia.configuracion_api.get('WHATSAPP_TOKEN', token)
            phone_id = agencia.configuracion_api.get('WHATSAPP_PHONE_ID', phone_id)

        if not token or not phone_id:
            logger.error("WhatsApp Meta Config Missing")
            return {'success': False, 'error_message': 'Configuración de Meta faltante'}

        url = f"https://graph.facebook.com/v18.0/{phone_id}/messages"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        clean_number = "".join(filter(str.isdigit, str(numero_cliente)))

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": clean_number,
            "type": "text",
            "text": {"body": mensaje}
        }

        response = requests.post(url, json=payload, headers=headers, timeout=20)

        if response.status_code in [200, 201]:
            return {'success': True, 'provider': 'meta', 'data': response.json()}
        else:
            return {'success': False, 'error_message': response.text}

    except Exception as e:
        logger.exception(f"Error en Meta API: {str(e)}")
        return {'success': False, 'error_message': str(e)}


def send_whatsapp_message(number: str, text: str, agencia=None, media_url=None, file_name=None) -> dict[str, Any]:
    """
    PUNTO DE ENTRADA UNIFICADO.
    Decide inteligentemente qué proveedor usar.
    Multi-tenant: cada agencia tiene su propia instancia Evolution (subdominio_slug).
    """
    if not agencia or not getattr(agencia, 'subdominio_slug', None):
        logger.error(f"WhatsApp: sin agencia o subdominio_slug. number={number}")
        return {"success": False, "error_message": "Se requiere una agencia con subdominio configurado"}

    instance_name = agencia.subdominio_slug

    # 1. Intentar vía EVOLUTION API (Soporta Media)
    try:
        success = False
        if media_url:
            success = EvolutionService.send_media(
                instance_name, number, media_url, caption=text, file_name=file_name
            )
        else:
            success = EvolutionService.send_text(instance_name, number, text)

        if success:
            return {'success': True, 'provider': 'evolution'}
    except Exception as e:
        logger.warning(f"⚠️ Evolution API falló para {number}: {e}")

    # 2. FALLBACK A META (Solo si es texto)
    if not media_url:
        logger.info(f"🔄 Reintentando vía Meta API para {number}...")
        return enviar_mensaje_meta_api(number, text, agencia=agencia)

    return {
        'success': False,
        'error_message': 'No se pudo enviar el mensaje por ningún proveedor (Evolution/Meta)'
    }


# ============================================================================
# SECTION 2: SESSION/QR MANAGEMENT (Evolution API Wrapper)
# ============================================================================

class WhatsAppService:
    """
    Wrapper de compatibilidad para session management con Evolution API v2.
    Mantiene la interfaz anterior redirigiendo a EvolutionService.
    """

    @classmethod
    def get_status(cls, session_name: str):
        """Mapea el estado de Evolution a los estados esperados por la UI."""
        state = EvolutionService.get_instance_state(session_name)
        logger.info(f"WhatsAppService.get_status for {session_name} -> {state}")

        if state == "open":
            return "WORKING"
        elif state == "connecting":
            return "CONNECTING"

        return "DISCONNECTED"

    @classmethod
    def start_session(cls, session_name: str):
        """Crea la instancia en Evolution."""
        return EvolutionService.create_instance(session_name)

    @classmethod
    def get_qr_code(cls, session_name: str):
        """
        Obtiene el QR de Evolution.
        Evolution API v2.2.x no expone QR via REST. Retorna la URL del Manager UI.
        """
        qr_data = EvolutionService.get_qr_code(session_name)

        if qr_data:
            if isinstance(qr_data, str):
                base64 = qr_data
            elif isinstance(qr_data, dict):
                base64 = qr_data.get("base64") or qr_data.get("code")
                if not base64:
                    base64 = None
            else:
                base64 = None

            if base64 and isinstance(base64, str):
                if base64.startswith("data:image"):
                    return base64
                return f"data:image/png;base64,{base64}"

        return EvolutionService.get_manager_qr_url(session_name)

    @classmethod
    def send_message(cls, chat_id: str, text: str, session_name: str = "default"):
        """Envía mensaje vía Evolution."""
        number = chat_id.replace("@c.us", "").replace("@g.us", "")
        return EvolutionService.send_text(session_name, number, text)

    @classmethod
    def logout(cls, session_name: str):
        """Desconecta y elimina la instancia en Evolution."""
        return EvolutionService.delete_instance(session_name)


# ============================================================================
# SECTION 3: NOTIFICATIONS (Twilio + Templates)
# ============================================================================

TWILIO_AVAILABLE = False
try:
    from twilio.rest import Client
    TWILIO_AVAILABLE = True
except ImportError:
    logger.warning("Twilio no está instalado. Instala con: pip install twilio")


def get_twilio_client():
    """Obtiene el cliente de Twilio configurado"""
    if not TWILIO_AVAILABLE:
        return None

    account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', None)
    auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', None)

    if not account_sid or not auth_token:
        logger.warning("Credenciales de Twilio no configuradas")
        return None

    return Client(account_sid, auth_token)


def enviar_whatsapp(telefono: str, mensaje: str, **kwargs) -> bool:
    """
    Envía un mensaje de WhatsApp vía Twilio.

    Args:
        telefono: Número en formato internacional (ej: +584121234567)
        mensaje: Texto del mensaje
        media_url: (Opcional) URL pública del archivo a adjuntar
    """
    client = get_twilio_client()
    if not client:
        logger.warning(f"No se puede enviar WhatsApp a {telefono}: Twilio no disponible")
        return False

    try:
        twilio_number = getattr(settings, 'TWILIO_WHATSAPP_NUMBER', None)
        if not twilio_number:
            logger.error("TWILIO_WHATSAPP_NUMBER no configurado")
            return False

        # Asegurar formato whatsapp:+número
        if not telefono.startswith('whatsapp:'):
            telefono = f'whatsapp:{telefono}'
        if not twilio_number.startswith('whatsapp:'):
            twilio_number = f'whatsapp:{twilio_number}'

        msg_params = {
            'from_': twilio_number,
            'body': mensaje,
            'to': telefono
        }

        # Soporte para adjuntos (PDF/Imagen) si se proporciona URL pública
        if kwargs.get('media_url'):
            msg_params['media_url'] = [kwargs['media_url']]

        message = client.messages.create(**msg_params)

        logger.info(f"WhatsApp enviado a {telefono}: {message.sid}")
        return True

    except Exception as e:
        logger.error(f"Error enviando WhatsApp a {telefono}: {e}")
        return False


def enviar_whatsapp_confirmacion_venta(venta) -> bool:
    """Envía WhatsApp de confirmación cuando se crea una venta"""
    if not venta.cliente or not venta.cliente.telefono_principal:
        logger.warning(f"Venta {venta.id_venta} sin cliente o teléfono")
        return False

    mensaje = f"""
🌍 *TravelHub - Confirmación de Reserva*

Estimado/a *{venta.cliente.get_nombre_completo()}*,

Su reserva ha sido creada exitosamente.

📋 *Detalles:*
• Localizador: *{venta.localizador}*
• Fecha: {venta.fecha_venta.strftime('%d/%m/%Y')}
• Total: {venta.moneda.simbolo if venta.moneda else ''}{venta.total_venta}
• Estado: {venta.get_estado_display()}

Gracias por confiar en nosotros.

_Equipo TravelHub_
""".strip()

    return enviar_whatsapp(venta.cliente.telefono_principal, mensaje)


def enviar_whatsapp_cambio_estado(venta, estado_anterior: str) -> bool:
    """Envía WhatsApp cuando cambia el estado de la venta"""
    if not venta.cliente or not venta.cliente.telefono_principal:
        return False

    mensaje = f"""
🔄 *TravelHub - Actualización de Reserva*

Estimado/a *{venta.cliente.get_nombre_completo()}*,

El estado de su reserva ha sido actualizado.

📋 *Detalles:*
• Localizador: *{venta.localizador}*
• Estado anterior: {estado_anterior}
• Estado actual: *{venta.get_estado_display()}*

Si tiene alguna pregunta, no dude en contactarnos.

_Equipo TravelHub_
""".strip()

    return enviar_whatsapp(venta.cliente.telefono_principal, mensaje)


def enviar_whatsapp_recordatorio_pago(venta) -> bool:
    """Envía recordatorio de pago pendiente por WhatsApp"""
    if not venta.cliente or not venta.cliente.telefono_principal:
        return False

    if venta.saldo_pendiente <= 0:
        return False

    mensaje = f"""
⏰ *TravelHub - Recordatorio de Pago*

Estimado/a *{venta.cliente.get_nombre_completo()}*,

Le recordamos que tiene un saldo pendiente en su reserva.

📋 *Detalles:*
• Localizador: *{venta.localizador}*
• Total: {venta.moneda.simbolo if venta.moneda else ''}{venta.total_venta}
• Pagado: {venta.moneda.simbolo if venta.moneda else ''}{venta.total_venta - venta.saldo_pendiente}
• *Saldo pendiente: {venta.moneda.simbolo if venta.moneda else ''}{venta.saldo_pendiente}*

Por favor, proceda con el pago para confirmar su reserva.

_Equipo TravelHub_
""".strip()

    return enviar_whatsapp(venta.cliente.telefono_principal, mensaje)


def enviar_whatsapp_confirmacion_pago(pago_venta) -> bool:
    """Envía confirmación cuando se registra un pago por WhatsApp"""
    venta = pago_venta.venta
    if not venta.cliente or not venta.cliente.telefono_principal:
        return False

    saldo_msg = "✅ *Su reserva está completamente pagada.*" if venta.saldo_pendiente <= 0 else f"Saldo restante: {venta.moneda.simbolo if venta.moneda else ''}{venta.saldo_pendiente}"

    mensaje = f"""
💰 *TravelHub - Confirmación de Pago*

Estimado/a *{venta.cliente.get_nombre_completo()}*,

Hemos recibido su pago correctamente. ¡Gracias!

📋 *Detalles del pago:*
• Localizador: *{venta.localizador}*
• Monto pagado: {pago_venta.moneda.simbolo if pago_venta.moneda else ''}{pago_venta.monto}
• Fecha: {pago_venta.fecha_pago.strftime('%d/%m/%Y')}
• Método: {pago_venta.get_metodo_display()}

{saldo_msg}

_Equipo TravelHub_
""".strip()

    return enviar_whatsapp(venta.cliente.telefono_principal, mensaje)


# ============================================================================
# SECTION 4: AI BOT (Inbound Processing + CRM Lead Creation)
# ============================================================================

try:
    from pydantic import BaseModel

    from apps.automation.services.ai_engine import ai_engine
    from apps.communications.services.telegram_unified import enviar_alerta_telegram
    from apps.crm.models import Cliente, OportunidadViaje

    class AnalisisMensajeSchema(BaseModel):
        es_solicitud_viaje: bool
        origen: str
        destino: str
        fechas: str
        pasajeros: int
        respuesta_bot: str

    PROMPT_VENDEDOR_IA = """
Eres el Asistente Inteligente de Ventas de TravelHub, una agencia de viajes premium.
Un cliente te acaba de escribir por WhatsApp. Analiza su mensaje.
1. Extrae su intención de viaje.
2. Redacta una respuesta ultra-natural, profesional y amigable usando emojis sin exagerar.
3. NUNCA inventes precios. Tu trabajo es recopilar requerimientos para el agente humano.
"""

    def procesar_mensaje_entrante(telefono_cliente: str, nombre_perfil: str, mensaje_texto: str) -> bool:
        """
        Procesa mensaje entrante de WhatsApp con IA.
        - Analiza intención de viaje
        - Crea lead en CRM si aplica
        - Envía respuesta automática
        - Notifica al agente por Telegram
        """
        try:
            # 1. Llamar a Gemini de forma estructurada
            raw_resultado = ai_engine.call_gemini(
                prompt=f"Mensaje del cliente: {mensaje_texto}",
                system_instruction=PROMPT_VENDEDOR_IA + "\n\nResponde estrictamente en formato JSON con estas llaves: es_solicitud_viaje (bool), origen (str), destino (str), fechas (str), pasajeros (int), respuesta_bot (str)."
            )

            # 2. Validar y convertir a objeto de datos
            try:
                datos = {
                    "es_solicitud_viaje": raw_resultado.get("es_solicitud_viaje", False),
                    "origen": raw_resultado.get("origen", ""),
                    "destino": raw_resultado.get("destino", ""),
                    "fechas": raw_resultado.get("fechas", ""),
                    "pasajeros": raw_resultado.get("pasajeros", 1),
                    "respuesta_bot": raw_resultado.get("respuesta_bot", "Entendido. Un agente te contactará pronto.")
                }
                resultado = AnalisisMensajeSchema(**datos)
            except Exception as e:
                logger.error(f"Fallo en validacion de esquema AI: {e} | Raw: {raw_resultado}")
                if os.environ.get('DEBUG_AI'):
                    raise e
                return False

            # 3. Registrar o buscar al cliente
            telefono_limpio = telefono_cliente.replace("+", "").strip()

            cliente, _ = Cliente.objects.get_or_create(
                telefono_principal=telefono_limpio,
                defaults={'nombres': nombre_perfil}
            )

            # 4. Si quiere viajar, crear Tarjeta en el Kanban (Lead)
            if resultado.es_solicitud_viaje:
                OportunidadViaje.objects.create(
                    cliente=cliente,
                    origen=resultado.origen,
                    destino=resultado.destino,
                    fechas_texto=resultado.fechas,
                    cantidad_pasajeros=resultado.pasajeros,
                    notas_ia=f"Interés en viajar de {resultado.origen} a {resultado.destino} en {resultado.fechas}. Pax: {resultado.pasajeros}"
                )
                logger.info(f"✨ ¡Nuevo Lead creado! {nombre_perfil} ➔ {resultado.destino}")

                # 5. Avisar al humano (Agente) por Telegram
                enviar_alerta_telegram(
                    f"🤖 *NUEVO LEAD CAPTADO POR IA*\n\n"
                    f"👤 *Cliente:* {nombre_perfil} ({telefono_cliente})\n"
                    f"✈️ *Ruta:* {resultado.origen or '?'} ➔ {resultado.destino or '?'}\n"
                    f"📅 *Fechas:* {resultado.fechas or '?'}\n"
                    f"💬 *Dijo:* _{mensaje_texto}_"
                )

            # 6. Enviar la respuesta al cliente por WhatsApp
            enviar_mensaje_meta_api(telefono_cliente, resultado.respuesta_bot)

            # 7. Guardar Respuesta en Historial
            try:
                from apps.crm.models import MensajeWhatsApp
                MensajeWhatsApp.objects.create(
                    cliente=cliente,
                    direccion='OUT',
                    texto=resultado.respuesta_bot,
                    es_bot=True,
                    agencia=cliente.agencia
                )
            except Exception as e_hist:
                logger.error(f"Error guardando historial WA OUT: {e_hist}")

            return True

        except Exception as e:
            logger.error(f"Error en Bot de WhatsApp: {e}")
            if 'DEBUG_AI' in os.environ:
                raise e
            return False

except ImportError as e:
    logger.warning(f"WhatsApp Bot dependencies not available: {e}")

    def procesar_mensaje_entrante(telefono_cliente: str, nombre_perfil: str, mensaje_texto: str) -> bool:
        logger.error("WhatsApp Bot no disponible: faltan dependencias (pydantic, ai_engine, crm models)")
        return False
