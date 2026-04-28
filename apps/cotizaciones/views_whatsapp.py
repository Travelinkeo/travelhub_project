import logging
from django.views import View
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from core.services.voice_parser_service import process_twilio_audio_message, process_twilio_text_message
from apps.cotizaciones.models import Cotizacion
from apps.crm.models import Cliente
from core.whatsapp_notifications import enviar_whatsapp

logger = logging.getLogger(__name__)

@method_decorator(csrf_exempt, name='dispatch')
class IncomingWhatsAppWebhook(View):
    """
    Receptor asíncrono de mensajes entrantes de WhatsApp desde Twilio.
    Actúa como orquestador del módulo Voice-to-Quote.
    """
    def post(self, request, *args, **kwargs):
        # 1. Extraer identificadores básicos
        sender_id = request.POST.get('From', '') # Formato: "whatsapp:+58414123..."
        body_text = request.POST.get('Body', '').strip()
        num_media = int(request.POST.get('NumMedia', 0))
        
        if not sender_id:
             return HttpResponse("Invalid request format.", status=400)
             
        # Limpiar el whatsapp:+ para búsquedas CRM
        raw_phone = sender_id.replace('whatsapp:', '')
        logger.info(f"[Webhook Incoming] Mensaje recibido de {raw_phone}. Media={num_media}")
        
        # Buscar cliente existente en CRM
        cliente = Cliente.objects.filter(telefono_principal__icontains=raw_phone.lstrip('+')).first()
        cliente_nombre = cliente.nombres if cliente else "Prospecto WhatsApp Twilio"

        # 2. Orquestar procesamiento IA
        intencion_data = None
        has_media = False
        if num_media > 0:
            media_type = request.POST.get('MediaContentType0', '')
            if 'audio' in media_type or 'video' in media_type:
               has_media = True
               media_url = request.POST.get('MediaUrl0', '')
               logger.info(f"Derivando Audio {media_url} al Motor Gemini 2.0 Flash...")
               intencion_data = process_twilio_audio_message(media_url)
        
        if not intencion_data and body_text and len(body_text) > 10:
             # Fallback si envió texto muy largo pero claro
             intencion_data = process_twilio_text_message(body_text)
             
        # Si no hubo audio ni intención clara de IA, solo loguear el texto (conversación normal)
        if not intencion_data or "error" in intencion_data:
             logger.info(f"Mensaje no parseable a cotización. Body: {body_text}")
             return HttpResponse("Message received, but ignored.", status=200)

        # 3. Crear Cotización en Borrador "Magia AI"
        try:
             pasajeros_str = intencion_data.get('numero_pasajeros', 1)
             try: pax = int(pasajeros_str)
             except: pax = 1
             
             destino_f = intencion_data.get('destino', 'Varios')
             transcripcion = intencion_data.get('transcripcion', body_text)
             nota_interna = f"[VOICE-TO-QUOTE IA] Intención: {intencion_data.get('intencion')}\nOrigen: {intencion_data.get('origen', 'N/D')}\nMes/Fecha: {intencion_data.get('mes_viaje', 'N/D')}\nTipo: {intencion_data.get('tipo', 'VARIO')}"
             
             nueva_cot = Cotizacion()
             nueva_cot.destino = destino_f
             nueva_cot.numero_pasajeros = max(1, pax)
             nueva_cot.estado = Cotizacion.EstadoCotizacion.BORRADOR
             nueva_cot.descripcion_general = f"[TRANSCRITO]: {transcripcion}"
             nueva_cot.notas_internas = nota_interna
             nueva_cot.moneda_id = 1 # USD por defecto para evitar constrainsts no nulos en DB legacy
             
             if cliente:
                 nueva_cot.cliente = cliente
             else:
                 # Crear prospecto ciego para enganchar la cotización y no violar Foreign Key (requiere refactor sutil o usar un cliente proxy)
                 # Usaremos al primer cliente de la BD como proxy temporal si no tiene null=True. 
                 # En el roadmap actual Cotizacion REQUIERE un Cliente (on_delete=PROTECT)
                 # Vamos a crear el prospecto en CRM
                 nuevo_prospecto, created = Cliente.objects.get_or_create(
                     telefono_principal=raw_phone,
                     defaults={
                         'nombres': 'Prospecto',
                         'apellidos': raw_phone,
                         'tipo_cliente': 'IND',
                         'email': f"{raw_phone.lstrip('+')}@whatsapp-lead.com"
                     }
                 )
                 nueva_cot.cliente = nuevo_prospecto
                 nueva_cot.nombre_cliente_manual = "Prospecto Webhook"
                 
             nueva_cot.save()
             logger.info(f"Cotización automatizada Mágicamente! ID: {nueva_cot.numero_cotizacion}")
             
             # 4. Enviar Mensaje Amistoso Confirmatorio de la IA al Prospecto
             respuesta = ""
             if has_media:
                 respuesta = f"¡Hola! He escuchado tu audio completo. 🤖🎧\nYa le he enviado tus datos a tu asesor para que analice las opciones de {destino_f}. ¡Te contactará por aquí mismo muy pronto!"
             else:
                 respuesta = f"¡Hola! He leído tu mensaje. 🤖📲\nEn breve uno de nuestros especialistas procesará tu solicitud para {destino_f} y te enviará los detalles."
                 
             # Enviar por Twilio
             enviar_whatsapp(sender_id, respuesta)
             
        except Exception as e:
             import traceback
             logger.error(f"Falla crítica ensamblando Voice-To-Quote: {e}\n{traceback.format_exc()}")
             
        # Twilio pide devolver un status 200 rápido y TwiML vacío
        response_twiml = '<?xml version="1.0" encoding="UTF-8"?><Response></Response>'
        return HttpResponse(response_twiml, content_type='text/xml', status=200)

