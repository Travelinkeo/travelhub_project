import hashlib
import hmac
import logging
from decimal import Decimal

from django.conf import settings
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.bookings.models import Venta
from apps.finance.models import TransaccionPago

logger = logging.getLogger(__name__)


class WebhookPagoBaseView(APIView):

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        provider_data = request.data

        webhook_id = provider_data.get("bizId") or provider_data.get("id")
        venta_id = provider_data.get("custom_venta_id") or provider_data.get("metadata", {}).get(
            "venta_id"
        )
        monto = Decimal(str(provider_data.get("amount") or 0))

        if not webhook_id or not venta_id:
            logger.error(f"Webhook malformado recibido: {provider_data}")
            return Response(
                {"error": "Missing ID or Venta ref"}, status=status.HTTP_200_OK
            )

        from core.api import system_context

        with system_context():
            try:
                with transaction.atomic():
                    reintegro = (
                        TransaccionPago.objects.filter(webhook_transaction_id=webhook_id)
                        .select_for_update()
                        .first()
                    )

                    if reintegro:
                        logger.info(f"WEBHOOK DUPLICADO DETECTADO: ID {webhook_id} ya existe.")
                        return Response(
                            {
                                "status": "success",
                                "message": "Payment already processed",
                                "idempotency_key": webhook_id,
                            },
                            status=status.HTTP_200_OK,
                        )

                    venta_qs = Venta.objects.filter(pk=venta_id)
                    venta = get_object_or_404(venta_qs)

                    nueva_transaccion = TransaccionPago.objects.create(
                        proveedor=self.get_provider_key(),
                        monto=monto,
                        venta=venta,
                        webhook_transaction_id=webhook_id,
                        data_raw=provider_data,
                    )

                    self.procesar_logica_contable(nueva_transaccion)

                logger.info(f"PAGO PROCESADO EXITOSAMENTE: {nueva_transaccion}")

            except IntegrityError:
                logger.warning(f"RACE CONDITION EVITADA: ID {webhook_id} ya siendo procesado.")
                return Response({"status": "already_processing"}, status=status.HTTP_200_OK)

            except Exception as e:
                logger.exception(f"Error critico procesando Webhook {webhook_id}: {e}")
                return Response(
                    {"status": "error", "message": "Internal process error"},
                    status=status.HTTP_200_OK,
                )

        return Response(
            {"status": "success", "transaction_id": webhook_id}, status=status.HTTP_201_CREATED
        )

    def get_provider_key(self):
        return "OTR"

    def procesar_logica_contable(self, transaccion):
        pass


class BinanceWebhookView(WebhookPagoBaseView):
    def get_provider_key(self):
        return "BIN"

    def post(self, request, *args, **kwargs):
        webhook_secret = getattr(settings, "BINANCE_WEBHOOK_SECRET", None)
        if not webhook_secret:
            if settings.DEBUG:
                logger.warning("Binance webhook: BINANCE_WEBHOOK_SECRET no configurado (DEBUG), omitiendo HMAC")
            else:
                logger.error("Binance webhook: BINANCE_WEBHOOK_SECRET no configurado en produccion")
                return Response({"error": "Webhook not configured"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        if webhook_secret:
            signature = request.headers.get("X-Binance-Signature") or request.headers.get(
                "X-Signature"
            )
            if not signature:
                logger.error("Binance webhook sin firma HMAC")
                return Response({"error": "Missing signature"}, status=status.HTTP_401_UNAUTHORIZED)

            payload = request.body
            expected = hmac.new(
                webhook_secret.encode("utf-8"), payload, hashlib.sha256
            ).hexdigest()

            if not hmac.compare_digest(signature, expected):
                logger.error("Binance webhook: firma HMAC invalida")
                return Response({"error": "Invalid signature"}, status=status.HTTP_401_UNAUTHORIZED)

        return super().post(request, *args, **kwargs)


class StripeWebhookView(WebhookPagoBaseView):
    def get_provider_key(self):
        return "STR"

    def post(self, request, *args, **kwargs):
        webhook_secret = getattr(settings, "STRIPE_WEBHOOK_SECRET", None)
        if not webhook_secret:
            if settings.DEBUG:
                logger.warning("Stripe webhook: STRIPE_WEBHOOK_SECRET no configurado (DEBUG), omitiendo HMAC")
            else:
                logger.error("Stripe webhook: STRIPE_WEBHOOK_SECRET no configurado en produccion")
                return Response({"error": "Webhook not configured"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        if webhook_secret:
            sig_header = request.headers.get("Stripe-Signature", "")
            if not sig_header:
                logger.error("Stripe webhook sin Stripe-Signature header")
                return Response({"error": "Missing signature"}, status=status.HTTP_401_UNAUTHORIZED)

            try:
                import stripe

                event = stripe.webhook.construct_event(
                    request.body, sig_header, webhook_secret
                )
                request.data["_stripe_verified_event"] = event
            except stripe.error.SignatureVerificationError:
                logger.error("Stripe webhook: firma invalida")
                return Response({"error": "Invalid signature"}, status=status.HTTP_401_UNAUTHORIZED)
            except Exception as e:
                logger.error(f"Stripe webhook: error verificando firma: {e}")
                return Response({"error": "Verification failed"}, status=status.HTTP_401_UNAUTHORIZED)

        return super().post(request, *args, **kwargs)
