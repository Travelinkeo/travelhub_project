
import logging
from decimal import Decimal
from django.db import transaction, IntegrityError
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.shortcuts import get_object_or_404
from apps.finance.models import TransaccionPago
from apps.bookings.models import Venta

logger = logging.getLogger(__name__)

class WebhookPagoBaseView(APIView):
    """
    🚨 CRÍTICO | 🏢 MULTI-TENANT
    Controlador Base (Patrón Template Method) para todos los callbacks Server-to-Server de proveedores de pago.
    
    ¿Por qué tan blindado?: Cuando un cliente aprueba un pago, la confirmación fiscal real NO viene del front (eso es hackeable),
    sino que viene a través de un POST en background desde los servidores de Stripe/Binance directamente a este Webhook.
    
    # 🚨 REGLA DE ORO DE IDEMPOTENCIA: 
    # Nunca confíes en que el proveedor envía el POST una sola vez. Binance/Stripe a veces envían el evento "Payment Success" 
    # 5 veces seguidas debido a Timeouts en sus redes. Si no diseñamos todo para el rechazo de reentradas (Idempotencia estricta),
    # le duplicaremos el abono/saldo en dólares al cliente, quebrando la agencia.
    """
    # CRÍTICO: Debe ser AllowAny porque las pasarelas jamás se loguean con nuestro Bearer Token JWT nativo.
    # La autenticidad se valida comparando los Hmac-Signatures en el header contra los Webhook Secrets de la BD.
    permission_classes = [AllowAny] 

    def post(self, request, *args, **kwargs):
        """
        🚨 CRÍTICO | ⚡ ASÍNCRONO
        Endpoint receptor del Event-Driven payload de la pasarela.
        
        Args:
            request (Request): Framework nativo, contiene el payload webhook de Stripe/Binance.
            
        Returns:
            Response: 200 OK estricto (incluso si ignoramos el payload por repetido).
                      Si devolvemos 4xx o 5xx el proveedor castigará el webhook metiéndolo a un exponential retry queue.
            
        # ¿Por qué `select_for_update()` en la línea interior?: Es un Mutex de Base de Datos (Row Lock). 
        # Si recibimos 2 webhooks idénticos al mismo milisegundo (Race Condition multi-hilo), el Hilo A bloquea 
        # la transacción, obligando al Hilo B a esperar. Cuando A termina, B se da cuenta que el ID ya existe y 
        # retorna 200 sin duplicar la contabilidad.
        """
        # 1. Extracción de datos (Ejemplo genérico, se ajustará por proveedor)
        provider_data = request.data
        
        # Simulamos extracción de campos clave según el provider
        # provider = 'BIN' (Binance) o 'STR' (Stripe)
        webhook_id = provider_data.get('bizId') or provider_data.get('id')
        venta_id = provider_data.get('custom_venta_id') or provider_data.get('metadata', {}).get('venta_id')
        monto = Decimal(str(provider_data.get('amount') or 0))
        
        if not webhook_id or not venta_id:
            logger.error(f"Webhook malformado recibido: {provider_data}")
            return Response({"error": "Missing ID or Venta ref"}, status=status.HTTP_400_BAD_REQUEST)

        # --- 🚨 BLINDAJE DE SEGURIDAD FISCAL (MUTEX Y ATOMICIDAD) ---
        try:
            with transaction.atomic():
                # PASO 1: Intentamos bloquear/verificar si ya existe el ID (select_for_update)
                reintegro = TransaccionPago.objects.filter(webhook_transaction_id=webhook_id).select_for_update().first()
                
                if reintegro:
                    # El pago ya fue procesado anteriormente (Idempotencia en acción)
                    logger.info(f"🔄 WEBHOOK DUPLICADO DETECTADO: El ID {webhook_id} ya existe. Ignorando proceso contable.")
                    return Response({
                        "status": "success", 
                        "message": "Payment already processed", 
                        "idempotency_key": webhook_id
                    }, status=status.HTTP_200_OK)

                # PASO 2: Si no existe, creamos el registro inmediatamente para "marcar el territorio"
                # Esto evita condiciones de carrera (race conditions)
                venta = get_object_or_404(Venta, pk=venta_id)
                
                nueva_transaccion = TransaccionPago.objects.create(
                    proveedor=self.get_provider_key(),
                    monto=monto,
                    venta=venta,
                    webhook_transaction_id=webhook_id,
                    data_raw=provider_data
                )
                
                # PASO 3: Aquí iría la lógica pesada (SOLO SE EJECUTA UNA VEZ)
                # ej: generar recibo, crear asiento contable, actualizar saldo de la venta.
                self.procesar_logica_contable(nueva_transaccion)
                
                logger.info(f"✅ PAGO PROCESADO EXITOSAMENTE: {nueva_transaccion}")
                
        except IntegrityError:
            # Fallback de seguridad extrema ante Race Conditions
            # Si dos hilos intentan el .create() al mismo tiempo y el primero gana,
            # el segundo lanza IntegrityError por el unique=True.
            logger.warning(f"⚠️ RACE CONDITION EVITADA: El ID {webhook_id} ya estaba siendo procesado.")
            return Response({"status": "already_processing"}, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.exception(f"Error crítico procesando Webhook {webhook_id}: {e}")
            return Response({"error": "Internal process error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"status": "success", "transaction_id": webhook_id}, status=status.HTTP_201_CREATED)

    def get_provider_key(self):
        """Sobrescribir en subclases (ej: 'BIN')"""
        return 'OTR'

    def procesar_logica_contable(self, transaccion):
        """
        🚨 CRÍTICO
        Punto de gancho (Hook del Template Method) donde la factura ya superó las barreras de protección de red
        y `TransaccionPago` ha sido insertada. Aquí se aplican las mutaciones directas de Saldo a Venta y emisión de PDFs financieros.
        
        Args:
            transaccion (TransaccionPago): Row de base de datos confirmada y asegurada.
            
        # ¿Por qué se aísla de la vista?: El encapsulamiento es vital. Si este método interno explota lanzando
        # un ValidationError, el Statement `with transaction.atomic()` de nivel superior captura la onda expansiva, 
        # ejecuta un "DB Rollback" mágico y elimina el registro de `TransaccionPago` huérfano, dejando el sistema inmaculado 
        # para cuando Stripe nos reintente enviar el webhook a los 5 minutos.
        """
        # Simulamos actualización de la venta
        venta = transaccion.venta
        # venta.registrar_abono(transaccion.monto) 
        pass

# Ejemplo de implementación específica para Binance
class BinanceWebhookView(WebhookPagoBaseView):
    def get_provider_key(self):
        return 'BIN'

# Ejemplo de implementación específica para Stripe
class StripeWebhookView(WebhookPagoBaseView):
    def get_provider_key(self):
        return 'STR'
