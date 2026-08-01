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
from apps.finance.models_stubs import TransaccionPago

logger = logging.getLogger(__name__)


class WebhookSignatureError(Exception):
    """Error de verificación de firma con status code HTTP asociado."""

    def __init__(self, message: str, status_code: int = status.HTTP_401_UNAUTHORIZED):
        """__init__."""
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class WebhookPagoBaseView(APIView):
    """WebhookPagoBaseView.

    Fail-closed por defecto: requiere que la subclase implemente
    verify_signature(). Cualquier webhook sin verificación de firma
    es rechazado con 401.
    """

    permission_classes = [AllowAny]

    def verify_signature(self, request) -> None:
        """Debe implementarse en cada subclase. Fail-closed: rechaza por defecto."""
        raise WebhookSignatureError("Signature verification required")

    def post(self, request, *args, **kwargs):
        """post."""
        try:
            self.verify_signature(request)
        except WebhookSignatureError as e:
            logger.error(f"{self.__class__.__name__} webhook rechazado: {e.message}")
            return Response({"error": e.message}, status=e.status_code)

        provider_data = request.data

        webhook_id = provider_data.get("bizId") or provider_data.get("id")
        venta_id = provider_data.get("custom_venta_id") or provider_data.get("metadata", {}).get(
            "venta_id"
        )
        monto = Decimal(str(provider_data.get("amount") or 0))

        if not webhook_id or not venta_id:
            logger.error(f"Webhook malformado recibido: {provider_data}")
            return Response({"error": "Missing ID or Venta ref"}, status=status.HTTP_200_OK)

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
        """get_provider_key."""
        return "OTR"

    def procesar_logica_contable(self, transaccion):
        """procesar_logica_contable."""
        pass


class BinanceWebhookView(WebhookPagoBaseView):
    """BinanceWebhookView."""

    def get_provider_key(self):
        """get_provider_key."""
        return "BIN"

    def verify_signature(self, request) -> None:
        """Valida firma HMAC-SHA256 de Binance."""
        webhook_secret = getattr(settings, "BINANCE_WEBHOOK_SECRET", None)
        if not webhook_secret:
            logger.error(
                "Binance webhook: BINANCE_WEBHOOK_SECRET no configurado - rechazando (fail-closed)"
            )
            raise WebhookSignatureError(
                "Webhook not configured", status_code=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        signature = request.headers.get("X-Binance-Signature") or request.headers.get("X-Signature")
        if not signature:
            logger.error("Binance webhook sin firma HMAC")
            raise WebhookSignatureError("Missing signature")

        payload = request.body
        expected = hmac.new(webhook_secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()

        if not hmac.compare_digest(signature, expected):
            logger.error("Binance webhook: firma HMAC invalida")
            raise WebhookSignatureError("Invalid signature")


class StripeWebhookView(WebhookPagoBaseView):
    """StripeWebhookView."""

    def get_provider_key(self):
        """get_provider_key."""
        return "STR"

    def verify_signature(self, request) -> None:
        """Valida firma Stripe-Signature."""
        webhook_secret = getattr(settings, "STRIPE_WEBHOOK_SECRET", None)
        if not webhook_secret:
            logger.error(
                "Stripe webhook: STRIPE_WEBHOOK_SECRET no configurado - rechazando (fail-closed)"
            )
            raise WebhookSignatureError(
                "Webhook not configured", status_code=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        sig_header = request.headers.get("Stripe-Signature", "")
        if not sig_header:
            logger.error("Stripe webhook sin Stripe-Signature header")
            raise WebhookSignatureError("Missing signature")

        try:
            import stripe

            event = stripe.Webhook.construct_event(request.body, sig_header, webhook_secret)
            request.data["_stripe_verified_event"] = event
        except stripe.SignatureVerificationError:
            logger.error("Stripe webhook: firma invalida")
            raise WebhookSignatureError("Invalid signature") from None
        except Exception as e:
            logger.error(f"Stripe webhook: error verificando firma: {e}")
            raise WebhookSignatureError("Verification failed") from e
