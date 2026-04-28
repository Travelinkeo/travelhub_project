import stripe
import logging
from django.conf import settings
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views import View
from django.utils.decorators import method_decorator
from django.db import transaction

from apps.finance.models import LinkDePago

logger = logging.getLogger(__name__)

class StripeCheckoutView(View):
    """
    Genera una sesión de pago única en Stripe y redirige al cliente
    a la pasarela de Visa/Mastercard.
    """
    def dispatch(self, request, *args, **kwargs):
        stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', '')
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, uuid_link, *args, **kwargs):
        link_pago = get_object_or_404(LinkDePago, id=uuid_link)
        
        if not link_pago.esta_activo:
            return HttpResponse('<div class="p-4 text-red-500 font-bold">El enlace ha expirado.</div>', status=400)

        domain_url = request.build_absolute_uri('/')[:-1]
        
        try:
            # Crear sesión de Stripe
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[
                    {
                        'price_data': {
                            'currency': link_pago.moneda.lower(),
                            'unit_amount': int(link_pago.monto_total * 100), # Stripe cuenta en centavos (ej. 10.00 -> 1000)
                            'product_data': {
                                'name': f'Itinerario de Vuelo - PNR {link_pago.venta.localizador}',
                                'description': f'Pasajero Principal: {link_pago.venta.cliente.nombres}',
                            },
                        },
                        'quantity': 1,
                    },
                ],
                mode='payment',
                # URLs de retorno tras el pago (usamos include para namespace)
                success_url=domain_url + reverse('finance:magic_link_checkout', args=[link_pago.id]) + '?pago=exito',
                cancel_url=domain_url + reverse('finance:magic_link_checkout', args=[link_pago.id]) + '?pago=cancelado',
                
                # Identificador vital para auto-conciliar en el Webhook
                client_reference_id=str(link_pago.id), 
            )
            # Redirigir físicamente al cliente al Checkout de Stripe
            return redirect(checkout_session.url, code=303)
            
        except Exception as e:
            logger.error(f"Error creando sesión de Stripe: {e}")
            return HttpResponse(f"Error interno conectando con Stripe: {e}", status=500)


@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhookView(View):
    """
    Escucha invisible que Stripe llama automáticamente cuando la tarjeta pasa exitosamente.
    """
    def post(self, request, *args, **kwargs):
        stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', '')
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')
        endpoint_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', '')

        event = None

        # 1. Verificar firma criptográfica de Stripe (Seguridad anti-hackers)
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
        except ValueError:
            return HttpResponse(status=400)
        except stripe.error.SignatureVerificationError:
            logger.warning("Firma de Stripe inválida interceptada.")
            return HttpResponse(status=400)

        # 2. Procesar el pago completado
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            link_id = session.get('client_reference_id')
            
            if link_id:
                try:
                    # ✅ ENVOLVEMOS EL BLOQUE CRÍTICO EN TRANSACTION.ATOMIC
                    with transaction.atomic():
                        link_pago = LinkDePago.objects.select_for_update().get(id=link_id)
                        
                        if link_pago.estado == LinkDePago.EstadoPago.PAGADO:
                            logger.warning(f"⚠️ El link {link_id} ya estaba pagado. Ignorando webhook duplicado.")
                            return HttpResponse(status=200)
                            
                        # Marcamos link y venta como pagados
                        link_pago.estado = LinkDePago.EstadoPago.PAGADO
                        link_pago.referencia_pago = session.get('payment_intent')
                        link_pago.save()
                        
                        venta = link_pago.venta
                        venta.estado = 'PAG' 
                        venta.save()
                        
                        logger.info(f"✅ [STRIPE] Pago automatizado exitoso. PNR: {venta.localizador}")
                        
                except LinkDePago.DoesNotExist:
                    logger.error(f"Link de pago no encontrado para Stripe Session: {link_id}")

        return HttpResponse(status=200)
