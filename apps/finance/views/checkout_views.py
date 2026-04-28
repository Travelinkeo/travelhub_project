import logging
from django.views import View
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from ..models.checkout import LinkDePago

logger = logging.getLogger(__name__)

class MagicLinkCheckoutView(View):
    template_name = 'finance/checkout/magic_link.html'

    def get(self, request, uuid_link, *args, **kwargs):
        link_pago = get_object_or_404(LinkDePago, id=uuid_link)
        venta = link_pago.venta
        agencia = venta.agencia
        
        items = venta.items.all() if hasattr(venta, 'items') else venta.itemventa_set.all()
        
        context = {
            'link': link_pago,
            'venta': venta,
            'agencia': agencia,
            'items': items,
            'is_expired': not link_pago.esta_activo and link_pago.estado == 'PEN',
        }
        return render(request, self.template_name, context)

    def post(self, request, uuid_link, *args, **kwargs):
        """
        Endpoint reactivo (HTMX) unificado para recibir reportes de pago (Zelle o Crypto).
        """
        link_pago = get_object_or_404(LinkDePago, id=uuid_link)
        
        if not link_pago.esta_activo:
            return HttpResponse('<div class="text-red-500 font-bold p-4 bg-red-100 rounded-xl text-center">Este enlace ha expirado o ya fue procesado.</div>')

        referencia = request.POST.get('referencia')
        comprobante = request.FILES.get('comprobante')
        metodo_pago = request.POST.get('metodo_pago', 'ZELLE') # Detecta si es ZELLE o CRYPTO

        if not referencia:
            return HttpResponse('<div class="text-red-500 font-bold text-sm text-center">⚠️ La referencia/hash es obligatoria.</div>')

        try:
            # 1. Actualizamos el estado del link guardando el prefijo del método
            link_pago.referencia_pago = f"[{metodo_pago}] {referencia}"
            if comprobante:
                link_pago.comprobante_imagen = comprobante
            link_pago.estado = LinkDePago.EstadoPago.EN_REVISION
            link_pago.save()

            # 2. Disparar la notificación asíncrona a Telegram
            try:
                from apps.finance.tasks import notificar_pago_zelle_task
                notificar_pago_zelle_task.apply_async(args=[str(link_pago.id)], queue='notifications')
            except Exception as tg_err:
                logger.warning(f"No se pudo encolar tarea Telegram: {tg_err}")

            # 3. Respuesta visual inteligente (HTMX UI)
            # Cambia el diseño (Verde para Zelle, Naranja/Ámbar para Crypto)
            color = "emerald" if metodo_pago == "ZELLE" else "amber"

            html_exito = f"""
            <div class="bg-{color}-50 border border-{color}-200 p-8 rounded-3xl text-center animate-fade-in-up">
                <div class="w-20 h-20 bg-{color}-500 rounded-full flex items-center justify-center mx-auto mb-4 shadow-lg shadow-{color}-500/30">
                    <span class="material-symbols-outlined text-white text-4xl">check_circle</span>
                </div>
                <h3 class="text-2xl font-black text-{color}-900 mb-2">¡Pago en Revisión!</h3>
                <p class="text-{color}-700 font-medium mb-6">Hemos recibido tu referencia <b>#{referencia}</b> mediante {metodo_pago}. Nuestro equipo está validando la transacción.</p>
                <div class="text-xs text-{color}-500 uppercase tracking-widest font-bold">TravelHub Secure Checkout</div>
            </div>
            """
            
            return HttpResponse(html_exito)

        except Exception as e:
            logger.error(f"Error procesando pago {metodo_pago} para link {uuid_link}: {e}")
            return HttpResponse('<div class="text-red-500 font-bold text-sm text-center">Ocurrió un error. Intenta nuevamente.</div>')
