import hashlib
import hmac
import json
import time
import uuid
import requests
import logging
from django.conf import settings
from apps.finance.models import PagoBinance, Factura

logger = logging.getLogger(__name__)

class BinancePayService:
    """
    Servicio para interactuar con la API de Binance Pay (v2).
    Documentación: https://developers.binance.com/docs/binance-pay/introduction
    """

    def __init__(self):
        self.base_url = "https://bpay.binanceapi.com"
        self.api_key = getattr(settings, 'BINANCE_PAY_API_KEY', 'MOCK_KEY')
        self.secret_key = getattr(settings, 'BINANCE_PAY_SECRET_KEY', 'MOCK_SECRET')

    def _generate_signature(self, payload: str, timestamp: str, nonce: str) -> str:
        """
        Genera la firma HMAC-SHA512 requerida por Binance.
        Formato: payload + timestamp + nonce
        """
        payload_to_sign = f"{timestamp}\n{nonce}\n{payload}\n"
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            payload_to_sign.encode('utf-8'),
            hashlib.sha512
        ).hexdigest().upper()
        return signature

    def _get_headers(self, payload: str):
        timestamp = str(int(time.time() * 1000))
        nonce = str(uuid.uuid4())[:32]
        signature = self._generate_signature(payload, timestamp, nonce)

        return {
            "Content-Type": "application/json",
            "BinancePay-Timestamp": timestamp,
            "BinancePay-Nonce": nonce,
            "BinancePay-Certificate-SN": self.api_key,
            "BinancePay-Signature": signature
        }

    def create_order(self, factura: Factura):
        """
        Crea una orden en Binance Pay para una factura específica.
        """
        merchant_trade_no = f"TH-{factura.id_factura}-{uuid.uuid4().hex[:8]}"
        
        payload_dict = {
            "env": {"terminalType": "WEB"},
            "merchantTradeNo": merchant_trade_no,
            "orderAmount": str(factura.monto_total),
            "currency": "USDT",
            "goods": {
                "goodsType": "01",
                "goodsCategory": "6000", # Travel
                "referenceGoodsId": f"INV-{factura.numero_factura}",
                "goodsName": f"Servicios Turísticos - {factura.numero_factura}"
            },
            "cancelUrl": f"{settings.WEB_APP_URL}/finance/invoice/{factura.id_factura}/cancel",
            "returnUrl": f"{settings.WEB_APP_URL}/finance/invoice/{factura.id_factura}/success"
        }

        payload = json.dumps(payload_dict)
        url = f"{self.base_url}/binancepay/openapi/v2/order"

        try:
            # Crear registro local primero
            pago = PagoBinance.objects.create(
                factura=factura,
                merchant_trade_no=merchant_trade_no,
                monto=factura.monto_total,
                estado=PagoBinance.EstadoPago.INICIAL
            )

            # Si estamos en modo MOCK (sin llaves reales), simulamos respuesta
            if self.api_key == 'MOCK_KEY':
                pago.prepay_id = f"MOCK_{uuid.uuid4().hex}"
                pago.checkout_url = "https://mock.binance.com/checkout"
                pago.save()
                return pago

            response = requests.post(url, headers=self._get_headers(payload), data=payload)
            res_json = response.json()

            pago.raw_response = res_json
            if res_json.get('status') == 'SUCCESS':
                data = res_json['data']
                pago.prepay_id = data['prepayId']
                pago.checkout_url = data['checkoutUrl']
                pago.save()
                return pago
            else:
                pago.estado = PagoBinance.EstadoPago.FALLIDO
                pago.save()
                logger.error(f"Error Binance Create Order: {res_json}")
                return None

        except Exception as e:
            logger.exception("Error calling Binance Pay API")
            return None

    def verify_webhook(self, data: dict, signature: str, timestamp: str, nonce: str) -> bool:
        """
        Verifica que la notificación venga realmente de Binance.
        """
        payload = json.dumps(data)
        expected_signature = self._generate_signature(payload, timestamp, nonce)
        return hmac.compare_digest(expected_signature, signature)

    def process_payment_notification(self, biz_data: dict):
        """
        Procesa la notificación de éxito (C2B_PAYMENT).
        Actualiza factura y dispara contabilidad.
        """
        merchant_trade_no = biz_data.get('merchantTradeNo')
        pago = PagoBinance.objects.filter(merchant_trade_no=merchant_trade_no).first()

        if not pago:
            return False

        if biz_data.get('status') == 'PAY_SUCCESS':
            pago.estado = PagoBinance.EstadoPago.EXITOSO
            pago.save()

            # Actualizar Factura
            factura = pago.factura
            factura.estado = 'PAG'  # Pagada
            factura.save()

            # Disparar Asiento Contable
            self._create_accounting_entry(pago)
            
            logger.info(f"Factura {factura.numero_factura} pagada vía Binance Pay.")
            return True

        return False

    def _create_accounting_entry(self, pago: PagoBinance):
        """
        Crea el asiento contable de ingreso por el pago de Binance Pay.
        """
        try:
            from contabilidad.models import AsientoContable, DetalleAsiento, PlanContable
            from decimal import Decimal

            with transaction.atomic():
                factura = pago.factura
                asiento = AsientoContable.objects.create(
                    tipo_asiento=AsientoContable.TipoAsiento.DIARIO,
                    fecha_contable=timezone.now().date(),
                    descripcion_general=f"Cobro Factura {factura.numero_factura} vía Binance Pay ({pago.merchant_trade_no})",
                    moneda=factura.moneda,
                    referencia_documento=factura.numero_factura,
                    estado=AsientoContable.EstadoAsiento.CONTABILIZADO,
                    tasa_cambio_aplicada=factura.tasa_cambio
                )

                # DEBE: Efectivo / Binance (Usando Caja General USD como placeholder)
                cuenta_caja = PlanContable.objects.get(codigo_cuenta='1.1.01.02')
                DetalleAsiento.objects.create(
                    asiento=asiento,
                    linea=1,
                    cuenta_contable=cuenta_caja,
                    debe=pago.monto,
                    descripcion_linea=f"Ingreso Binance Pay - Order {pago.merchant_trade_no}"
                )

                # HABER: Cuentas por Cobrar Clientes
                cuenta_cxc = PlanContable.objects.get(codigo_cuenta='1.1.02.02')
                DetalleAsiento.objects.create(
                    asiento=asiento,
                    linea=2,
                    cuenta_contable=cuenta_cxc,
                    haber=pago.monto,
                    descripcion_linea=f"Cancelación saldo Factura {factura.numero_factura}"
                )

                asiento.calcular_totales()
                logger.info(f"Asiento contable de pago {asiento.id_asiento} creado exitosamente.")
                return asiento

        except Exception as e:
            logger.error(f"Error creando asiento contable para pago Binance {pago.id_pago_binance}: {e}")
            return None
