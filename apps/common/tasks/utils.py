import json
import logging
import os

from celery import shared_task
from django.conf import settings

from apps.common.utils.celery_utils import idempotent_task

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    queue="default",
    max_retries=2,
    default_retry_delay=30,
    time_limit=120,
    soft_time_limit=100,
)
def generate_pdf_task(self, html_content, margins=0.0):
    """generate_pdf_task."""
    from apps.common.services.pdf_renderer import PdfRendererService

    try:
        pdf_bytes = PdfRendererService.render_html_to_pdf(html_content, margins)
        logger.info(f"PDF generated: {len(pdf_bytes)} bytes")
        return pdf_bytes
    except Exception as exc:
        logger.error(f"PDF generation task error: {exc}")
        self.retry(exc=exc)


@shared_task(
    queue="default", max_retries=2, default_retry_delay=5, time_limit=60, soft_time_limit=50
)
@idempotent_task(timeout=3600, key_prefix="celery_binance_order")
def create_binance_order_task(factura_id):
    """create_binance_order_task."""
    from celery import current_task
    from django.core.cache import cache

    from apps.finance.models import Factura
    from apps.finance.services.binance_service import BinancePayService

    try:
        factura = Factura.objects.get(pk=factura_id)
        service = BinancePayService()
        pago = service.create_order(factura)
        if pago:
            cache_key = f"binance_order:{factura_id}"
            cache.set(
                cache_key,
                {
                    "prepay_id": pago.prepay_id,
                    "checkout_url": pago.checkout_url,
                    "monto": str(pago.monto),
                    "moneda": pago.moneda,
                    "merchant_trade_no": pago.merchant_trade_no,
                },
                3600,
            )
            logger.info(f"Binance order created for factura {factura_id}: {pago.prepay_id}")
            return {"prepay_id": pago.prepay_id, "checkout_url": pago.checkout_url}
        logger.error(f"Binance order creation failed for factura {factura_id}")
        return None
    except Exception as exc:
        logger.error(f"Binance order task error for factura {factura_id}: {exc}")
        current_task.retry(exc=exc)


@shared_task(
    bind=True,
    queue="default",
    max_retries=3,
    default_retry_delay=30,
    time_limit=120,
    soft_time_limit=100,
)
def fetch_unsplash_image_task(self, query):
    """fetch_unsplash_image_task."""
    import requests

    access_key = os.environ.get("UNSPLASH_ACCESS_KEY")
    if not access_key:
        logger.warning("UNSPLASH_ACCESS_KEY no configurada")
        return None

    try:
        url = "https://api.unsplash.com/search/photos"
        params = {
            "query": f"{query} travel landscape",
            "orientation": "portrait",
            "per_page": 1,
            "client_id": access_key,
        }
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data["results"]:
                image_url = data["results"][0]["urls"]["regular"]
                img_response = requests.get(image_url, timeout=10)
                if img_response.status_code == 200:
                    from base64 import b64encode

                    b64_data = b64encode(img_response.content).decode("utf-8")
                    logger.info(f"Unsplash image fetched for query: {query}")
                    return {
                        "base64": b64_data,
                        "content_type": img_response.headers.get("Content-Type", "image/jpeg"),
                    }
        logger.warning(f"No Unsplash results for query: {query}")
        return None
    except Exception as exc:
        logger.error(f"Unsplash fetch error for query {query}: {exc}")
        self.retry(exc=exc)


@shared_task(
    bind=True,
    queue="default",
    max_retries=2,
    default_retry_delay=10,
    time_limit=30,
    soft_time_limit=20,
)
def fetch_airline_logo_task(self, airline_name):
    """fetch_airline_logo_task."""
    import requests

    try:
        json_path = os.path.join(settings.BASE_DIR, "core", "data", "airlines.json")
        if not os.path.exists(json_path):
            return None

        with open(json_path, encoding="utf-8") as f:
            airlines_data = json.load(f)

        iata_code = None
        airline_name_lower = airline_name.lower().strip()

        for item in airlines_data:
            if airline_name_lower == item["name"].lower():
                iata_code = item["code"]
                break
            elif airline_name_lower in item["name"].lower():
                if not iata_code:
                    iata_code = item["code"]

        if not iata_code and len(airline_name) == 2:
            iata_code = airline_name.upper()

        if not iata_code:
            return None

        logo_url = f"https://pics.avs.io/200/200/{iata_code}.png"
        response = requests.get(logo_url, timeout=5)
        if response.status_code == 200:
            from base64 import b64encode

            b64_data = b64encode(response.content).decode("utf-8")
            logger.info(f"Airline logo fetched: {airline_name} ({iata_code})")
            return {"base64": b64_data, "content_type": "image/png"}
        return None
    except Exception as exc:
        logger.error(f"Airline logo fetch error for {airline_name}: {exc}")
        self.retry(exc=exc)


@shared_task(
    bind=True,
    queue="notifications",
    max_retries=3,
    default_retry_delay=30,
    time_limit=60,
    soft_time_limit=50,
)
def fetch_bcv_rates_task(self):
    """fetch_bcv_rates_task."""
    from apps.finance.services.bcv_scraper import obtener_tasas_bcv

    try:
        tasas = obtener_tasas_bcv()
        if tasas:
            logger.info(f"BCV rates fetched: {list(tasas.keys())}")
        else:
            logger.warning("No BCV rates fetched")
        return {k: str(v) for k, v in tasas.items()} if tasas else None
    except Exception as exc:
        logger.error(f"BCV rates fetch error: {exc}")
        self.retry(exc=exc)


@shared_task(
    bind=True,
    queue="default",
    max_retries=3,
    default_retry_delay=30,
    time_limit=60,
    soft_time_limit=50,
)
def fetch_tasas_venezuela_task(self):
    """fetch_tasas_venezuela_task."""
    from apps.contabilidad.tasas_venezuela_client import TasasVenezuelaClient

    try:
        tasas = TasasVenezuelaClient.obtener_todas_tasas()
        if tasas:
            logger.info(f"Venezuela rates fetched: {len(tasas)} sources")
        else:
            logger.warning("No Venezuela rates fetched")
        return tasas
    except Exception as exc:
        logger.error(f"Venezuela rates fetch error: {exc}")
        self.retry(exc=exc)


@shared_task(
    bind=True,
    queue="default",
    max_retries=3,
    default_retry_delay=30,
    time_limit=60,
    soft_time_limit=50,
)
def fetch_image_base64_task(self, image_source):
    """fetch_image_base64_task."""
    from apps.common.utils.images import get_image_as_base64

    try:
        result = get_image_as_base64(image_source)
        if result:
            logger.info(f"Image fetched as base64 from: {str(image_source)[:80]}")
        else:
            logger.warning(f"Image fetch returned None: {str(image_source)[:80]}")
        return result
    except Exception as exc:
        logger.error(f"Image base64 fetch error: {exc}")
        self.retry(exc=exc)
