import json
import logging
from django.http import HttpResponse, JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from apps.finance.services.binance_service import BinancePayService

logger = logging.getLogger(__name__)

@method_decorator(csrf_exempt, name='dispatch')
class BinanceWebhookView(View):
    """
    Endpoint para recibir notificaciones de Binance Pay.
    """
    def post(self, request, *args, **kwargs):
        # 1. Obtener headers para validación
        signature = request.headers.get('BinancePay-Signature')
        timestamp = request.headers.get('BinancePay-Timestamp')
        nonce = request.headers.get('BinancePay-Nonce')

        try:
            data = json.loads(request.body)
            logger.info(f"Webhook Binance recibido: {data.get('bizType')}")
            
            service = BinancePayService()
            
            # 2. Verificar firma (Omitir si estamos en modo desarrollo sin llaves reales)
            if service.api_key != 'MOCK_KEY':
                if not service.verify_webhook(data, signature, timestamp, nonce):
                    logger.warning("Firma de webhook Binance inválida")
                    return HttpResponse(status=401)

            # 3. Procesar datos (bizData contiene la info de la orden)
            biz_data = data.get('data')
            if biz_data and data.get('bizType') == 'PAY_SUCCESS':
                success = service.process_payment_notification(biz_data)
                if success:
                    return JsonResponse({"returnCode": "SUCCESS", "returnMsg": "Oka"})
            
            return JsonResponse({"returnCode": "SUCCESS", "returnMsg": "Ignored or processed"})

        except Exception as e:
            logger.exception("Error procesando webhook de Binance")
            return HttpResponse(status=500)

class BinanceOrderCreateView(View):
    """
    Vista para iniciar el proceso de pago con Binance Pay.
    """
    def get(self, request, factura_id, *args, **kwargs):
        from apps.finance.models import Factura
        factura = Factura.objects.filter(pk=factura_id).first()
        
        if not factura:
            return HttpResponse("Factura no encontrada", status=404)
        
        service = BinancePayService()
        pago = service.create_order(factura)
        
        if pago and pago.checkout_url:
            # Retornamos el link de pago para que HTMX o el usuario lo use
            return HttpResponse(f"""
                <div class="text-center p-6 bg-gray-800 rounded-3xl border border-amber-500/30">
                    <p class="text-white mb-4">Orden de Binance Pay generada exitosamente.</p>
                    <a href="{pago.checkout_url}" target="_blank" 
                       class="inline-block bg-amber-500 hover:bg-amber-400 text-black font-bold py-3 px-8 rounded-xl transition-all">
                       🚀 Pagar {pago.monto} {pago.moneda} ahora
                    </a>
                    <p class="text-xs text-gray-500 mt-4">ID: {pago.merchant_trade_no}</p>
                </div>
            """)
        
        return HttpResponse("Error al generar la orden de Binance Pay", status=500)
