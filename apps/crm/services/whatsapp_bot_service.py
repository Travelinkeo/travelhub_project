import os
import logging
from pydantic import BaseModel, Field
from typing import Optional
from core.services.ai_engine import ai_engine
from apps.crm.models import Cliente
from apps.crm.models import OportunidadViaje

from core.services.whatsapp_service import enviar_mensaje_meta_api
from core.services.telegram_service import enviar_alerta_telegram

logger = logging.getLogger(__name__)

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

def procesar_mensaje_entrante(telefono_cliente: str, nombre_perfil: str, mensaje_texto: str):
    try:
        # Llamar a Gemini de forma estructurada (Modo Raw JSON para evitar líos de Schema)
        raw_resultado = ai_engine.call_gemini(
            prompt=f"Mensaje del cliente: {mensaje_texto}",
            # No pasamos response_schema aquí para evitar errores de API
            system_instruction=PROMPT_VENDEDOR_IA + "\n\nResponde estrictamente en formato JSON con estas llaves: es_solicitud_viaje (bool), origen (str), destino (str), fechas (str), pasajeros (int), respuesta_bot (str)."
        )
        
        # Validar y convertir a objeto de datos (Para usar .notacion)
        try:
            # Asegurar que las llaves existan con valores por defecto si la IA las omite
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
            if os.environ.get('DEBUG_AI'): raise e
            return False

        # 2. Registrar o buscar al cliente
        # Limpieza básica de teléfono para evitar duplicados
        telefono_limpio = telefono_cliente.replace("+", "").strip()
        
        cliente, _ = Cliente.objects.get_or_create(
            telefono_principal=telefono_limpio,
            defaults={'nombres': nombre_perfil}
        )
        
        # 3. Si quiere viajar, crear Tarjeta en el Kanban (Lead)
        if resultado.es_solicitud_viaje:
            # 3. Crear Lead Kanban
            oportunidad = OportunidadViaje.objects.create(
                cliente=cliente,
                origen=resultado.origen,
                destino=resultado.destino,
                fechas_texto=resultado.fechas,
                cantidad_pasajeros=resultado.pasajeros,
                notas_ia=f"Interés en viajar de {resultado.origen} a {resultado.destino} en {resultado.fechas}. Pax: {resultado.pasajeros}"
            )
            logger.info(f"✨ ¡Nuevo Lead creado! {nombre_perfil} ➔ {resultado.destino}")

            # 4. Avisar al humano (Agente) por Telegram
            enviar_alerta_telegram(
                f"🤖 *NUEVO LEAD CAPTADO POR IA*\n\n"
                f"👤 *Cliente:* {nombre_perfil} ({telefono_cliente})\n"
                f"✈️ *Ruta:* {resultado.origen or '?'} ➔ {resultado.destino or '?'}\n"
                f"📅 *Fechas:* {resultado.fechas or '?'}\n"
                f"💬 *Dijo:* _{mensaje_texto}_"
            )

        # 5. Enviar la respuesta mágica al cliente por WhatsApp
        enviar_mensaje_meta_api(telefono_cliente, resultado.respuesta_bot)
        
        # --- NUEVO: Guardar Respuesta en Historial ---
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
        if 'DEBUG_AI' in os.environ: raise e
        return False
