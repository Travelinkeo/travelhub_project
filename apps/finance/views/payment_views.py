import json
import logging

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from apps.finance.services.binance_service import BinancePayService

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name="dispatch")
class BinanceWebhookView(View):
    """
    Endpoint para recibir notificaciones de Binance Pay.
    """

    def post(self, request, *args, **kwargs):
        # 1. Obtener headers para validación
        signature = request.headers.get("BinancePay-Signature")
        timestamp = request.headers.get("BinancePay-Timestamp")
        nonce = request.headers.get("BinancePay-Nonce")

        try:
            data = json.loads(request.body)
            logger.info(f"Webhook Binance recibido: {data.get('bizType')}")

            from django.conf import settings as dj_settings

            service = BinancePayService()

            # 2. Verificar firma (Omitir solo en DEBUG sin llaves reales)
            if not (dj_settings.DEBUG and not service.api_key):
                if not service.verify_webhook(data, signature, timestamp, nonce):
                    logger.warning("Firma de webhook Binance inválida")
                    return HttpResponse(status=401)

            # 3. Procesar datos (bizData contiene la info de la orden)
            biz_data = data.get("data")
            if biz_data and data.get("bizType") == "PAY_SUCCESS":
                success = service.process_payment_notification(biz_data)
                if success:
                    return JsonResponse({"returnCode": "SUCCESS", "returnMsg": "Oka"})

            return JsonResponse({"returnCode": "SUCCESS", "returnMsg": "Ignored or processed"})

        except json.JSONDecodeError:
            logger.warning("Binance webhook: body no es JSON válido")
            return HttpResponse(status=400)
        except Exception:
            logger.exception("Error procesando webhook de Binance")
            return JsonResponse(
                {"returnCode": "ERROR", "returnMsg": "server error"},
                status=500,
            )


class BinanceOrderCreateView(View):
    """
    Vista para iniciar el proceso de pago con Binance Pay.
    Encola una Celery task y retorna una página de carga que
    el frontend puede refrescar vía HTMX polling.
    """

    def get(self, request, factura_id, *args, **kwargs):
        from django.core.cache import cache

        from apps.finance.models import Factura

        factura = Factura.objects.filter(pk=factura_id).first()

        if not factura:
            return HttpResponse("Factura no encontrada", status=404)

        cache_key = f"binance_order:{factura_id}"
        cached = cache.get(cache_key)

        if cached:
            return HttpResponse(f"""
                <div class="text-center p-6 bg-gray-800 rounded-3xl border border-amber-500/30">
                    <p class="text-white mb-4">Orden de Binance Pay generada exitosamente.</p>
                    <a href="{cached['checkout_url']}" target="_blank"
                       class="inline-block bg-amber-500 hover:bg-amber-400 text-black font-bold py-3 px-8 rounded-xl transition-all">
                       🚀 Pagar {cached['monto']} {cached['moneda']} ahora
                    </a>
                    <p class="text-xs text-gray-500 mt-4">ID: {cached['merchant_trade_no']}</p>
                </div>
            """)

        from apps.common.tasks import create_binance_order_task

        create_binance_order_task.delay(factura_id)

        return HttpResponse(f"""
            <div class="text-center p-6 bg-gray-800 rounded-3xl border border-amber-500/30"
                 hx-trigger="load delay:3s"
                 hx-get="/pago/binance/order/{factura_id}/"
                 hx-swap="outerHTML">
                <div class="animate-pulse text-white">
                    <p class="text-lg mb-2">Generando orden de pago...</p>
                    <p class="text-sm text-gray-400">Conectando con Binance Pay</p>
                </div>
            </div>
        """)


@login_required
def registrar_pago_modal_view(request, venta_id):
    from apps.bookings.models import Venta
    from apps.finance.forms import RegistroPagoFastForm

    # Validamos que la venta pertenezca a la misma agencia del usuario logueado (Multi-Tenant Guard)
    venta = get_object_or_404(Venta, id_venta=venta_id, agencia=request.user.agencia)
    agencia = request.user.agencia
    is_htmx = request.headers.get("HX-Request") == "true"

    if request.method == "POST":
        # Manejo de MultipartFormData por el archivo 'comprobante'
        form = RegistroPagoFastForm(
            request.POST, request.FILES, agencia=agencia, venta_id=venta.id_venta
        )
        if form.is_valid():
            pago = form.save()

            # Si es HTMX, devolvemos un bloque de éxito directo para inyectar en el DOM
            if is_htmx:
                return render(
                    request, "finance/partials/pago_exitoso.html", {"pago": pago, "venta": venta}
                )

        # Si el formulario es inválido y es HTMX, re-renderizamos solo el fragmento del formulario con los errores
        if is_htmx:
            return render(
                request, "finance/partials/form_pago_inner.html", {"form": form, "venta": venta}
            )
    else:
        form = RegistroPagoFastForm(agencia=agencia, venta_id=venta.id_venta)

    return render(request, "finance/registro_pago_page.html", {"form": form, "venta": venta})
