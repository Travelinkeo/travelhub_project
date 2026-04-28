import json
import logging
from django.http import HttpResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from apps.crm.tasks_bot import whatsapp_ai_task

logger = logging.getLogger(__name__)

@method_decorator(csrf_exempt, name='dispatch')
class WhatsAppWebhookView(View):
    """
    Webhook oficial para recibir mensajes de la API de WhatsApp Cloud (Meta).
    """
    def get(self, request, *args, **kwargs):
        """ Validación del Webhook de Meta (Token Challenge) """
        verify_token = getattr(settings, 'WHATSAPP_VERIFY_TOKEN', 'travelhub_secure_token_123')
        mode = request.GET.get('hub.mode')
        token = request.GET.get('hub.verify_token')
        challenge = request.GET.get('hub.challenge')

        if mode and token:
            if mode == 'subscribe' and token == verify_token:
                logger.info("✅ Webhook de WhatsApp verificado exitosamente.")
                return HttpResponse(challenge, status=200)
            else:
                return HttpResponse('Token inválido', status=403)
        return HttpResponse('TravelHub WhatsApp Bot Activo', status=200)

    def post(self, request, *args, **kwargs):
        """ Recepción de mensajes entrantes de clientes """
        try:
            body = json.loads(request.body)
            
            if body.get('object') == 'whatsapp_business_account':
                for entry in body.get('entry', []):
                    for change in entry.get('changes', []):
                        value = change.get('value', {})
                        messages = value.get('messages', [])
                        contacts = value.get('contacts', [])
                        
                        if messages and contacts:
                            mensaje = messages[0]
                            contacto = contacts[0]
                            
                            # Filtramos para solo leer mensajes de texto por ahora
                            if mensaje.get('type') == 'text':
                                texto = mensaje['text']['body']
                                telefono = mensaje['from']
                                nombre_perfil = contacto.get('profile', {}).get('name', 'Cliente Nuevo')
                                
                                logger.info(f"📩 Mensaje WA de {nombre_perfil}: {texto}")
                                
                                # --- NUEVO: Guardar en Historial para Inbox ---
                                try:
                                    from apps.crm.models import Cliente, MensajeWhatsApp
                                    telefono_limpio = telefono.replace("+", "").strip()
                                    cliente, _ = Cliente.objects.get_or_create(
                                        telefono_principal=telefono_limpio,
                                        defaults={'nombres': nombre_perfil}
                                    )
                                    MensajeWhatsApp.objects.create(
                                        cliente=cliente,
                                        direccion='IN',
                                        texto=texto,
                                        agencia=cliente.agencia
                                    )
                                except Exception as e_hist:
                                    logger.error(f"Error guardando historial WA IN: {e_hist}")

                                # Despachamos al Bot IA por el carril rápido de Celery
                                try:
                                    whatsapp_ai_task.apply_async(
                                        args=[telefono, nombre_perfil, texto],
                                        queue='ia_fast'
                                    )
                                except Exception as e:
                                    # Fallback directo si Celery falla
                                    logger.warning(f"Falla de Celery, procesando sincrónicamente: {e}")
                                    from apps.crm.services.whatsapp_bot_service import procesar_mensaje_entrante
                                    procesar_mensaje_entrante(telefono, nombre_perfil, texto)

            return HttpResponse('EVENT_RECEIVED', status=200)

        except Exception as e:
            logger.error(f"Error procesando webhook WA: {e}")
            return HttpResponse(status=500)
