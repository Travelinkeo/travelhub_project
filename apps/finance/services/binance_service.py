import hashlib
import hmac
import logging
import time
import uuid
from decimal import Decimal

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


class BinancePayService:
    """
    Servicio para interactuar con la API de Binance Pay (v2).
    """

    def __init__(self):
        """__init__."""
        self.base_url = "https://bpay.binanceapi.com"
        self.api_key = getattr(settings, "BINANCE_PAY_API_KEY", "")
        self.secret_key = getattr(settings, "BINANCE_PAY_SECRET_KEY", "")

    def _generate_signature(self, payload: str, timestamp: str, nonce: str) -> str:
        """_generate_signature."""
        payload_to_sign = f"{timestamp}\n{nonce}\n{payload}\n"
        signature = (
            hmac.new(
                self.secret_key.encode("utf-8"), payload_to_sign.encode("utf-8"), hashlib.sha512
            )
            .hexdigest()
            .upper()
        )
        return signature

    def _get_headers(self, payload: str):
        """_get_headers."""
        timestamp = str(int(time.time() * 1000))
        nonce = str(uuid.uuid4())[:32]
        signature = self._generate_signature(payload, timestamp, nonce)
        return {
            "content-type": "application/json",
            "BinancePay-Timestamp": timestamp,
            "BinancePay-Nonce": nonce,
            "BinancePay-Signature": signature,
            "BinancePay-Certificate-SN": self.api_key,
        }

    def create_order(self, venta, amount: Decimal, currency: str = "USD") -> dict | None:
        """create_order."""
        merchant_trade_no = f"TH{venta.pk:06d}{int(timezone.now().timestamp())}"
        payload = {
            "env": {"terminalType": "WEB"},
            "merchantTradeNo": merchant_trade_no,
            "orderAmount": float(amount),
            "currency": currency,
            "goods": {
                "goodsType": "01",
                "goodsName": f"TravelHub - Venta {venta.localizador}",
                "goodsDetail": f"Reserva {venta.localizador}",
            },
        }
        import json as _json

        try:
            import requests

            resp = requests.post(
                f"{self.base_url}/binancepay/openapi/v2/order",
                headers=self._get_headers(_json.dumps(payload)),
                json=payload,
                timeout=30,
            )
            data = resp.json()
            if data.get("status") == "SUCCESS":
                return data["data"]
            logger.error(f"Binance order error: {data}")
            return None
        except Exception as e:
            logger.error(f"Binance create_order exception: {e}")
            return None
