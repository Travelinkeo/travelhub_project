import logging
from collections.abc import Callable

logger = logging.getLogger(__name__)

TIMEOUT = 10  # segundos


def _test_openai(key: str) -> tuple[bool, str]:
    import openai

    client = openai.OpenAI(api_key=key, timeout=TIMEOUT)
    client.models.list()
    return True, "Conexión exitosa con OpenAI API"


def _test_deepseek(key: str) -> tuple[bool, str]:
    import openai

    client = openai.OpenAI(api_key=key, base_url="https://api.deepseek.com", timeout=TIMEOUT)
    client.models.list()
    return True, "Conexión exitosa con DeepSeek API"


def _test_stripe(key: str) -> tuple[bool, str]:
    import stripe

    stripe.api_key = key
    stripe.Balance.retrieve()
    return True, "Conexión exitosa con Stripe API"


def _test_resend(key: str) -> tuple[bool, str]:
    import requests

    r = requests.get(
        "https://api.resend.com/audiences",
        headers={"Authorization": f"Bearer {key}"},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    return True, "Conexión exitosa con Resend API"


def _test_telegram(key: str) -> tuple[bool, str]:
    import requests

    r = requests.get(f"https://api.telegram.org/bot{key}/getMe", timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()
    if data.get("ok"):
        bot_name = data["result"].get("first_name", "")
        return True, f"Bot {bot_name} conectado correctamente"
    return False, "Token Telegram inválido"


def _test_google_maps(key: str) -> tuple[bool, str]:
    import requests

    r = requests.get(
        "https://maps.googleapis.com/maps/api/geocode/json",
        params={"address": "test", "key": key},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    data = r.json()
    if data.get("status") != "REQUEST_DENIED":
        return True, "Conexión exitosa con Google Maps API"
    return False, data.get("error_message", "API Key denegada")


def _test_sentry(key: str) -> tuple[bool, str]:
    if key.startswith("https://"):
        return True, "Formato DSN válido (no se puede probar conexión sin enviar evento)"
    return False, "Formato de DSN inválido"


def _test_cloudflare_r2(key_id: str, secret: str | None = None) -> tuple[bool, str]:
    if secret:
        return True, f"Credencial R2 presente (Access Key: {key_id[:8]}...)"
    return True, f"Access Key ID presente ({key_id[:8]}...)"


def _test_evolution(key: str) -> tuple[bool, str]:
    if len(key) >= 16:
        return True, "Formato de API Key Evolution válido"
    return False, "API Key demasiado corta"


def _test_google_oauth(key: str) -> tuple[bool, str]:
    if key.startswith(("AIza", "ya29.")):
        return True, "Formato de cliente OAuth válido"
    return True, "Cliente ID presente (no se puede probar OAuth sin redirect URI)"


def _test_generic(key: str) -> tuple[bool, str]:
    if len(key) >= 8:
        return True, "Formato parece válido"
    return False, "Clave demasiado corta (mín 8 caracteres)"


SERVICE_TESTERS: dict[str, Callable[[str], tuple[bool, str]]] = {
    "OPENAI_API_KEY": _test_openai,
    "DEEPSEEK_API_KEY": _test_deepseek,
    "STRIPE_SECRET_KEY": _test_stripe,
    "STRIPE_WEBHOOK_SECRET": _test_stripe,
    "RESEND_API_KEY": _test_resend,
    "TELEGRAM_BOT_TOKEN": _test_telegram,
    "GOOGLE_MAPS_API_KEY": _test_google_maps,
    "MAPBOX_TOKEN": _test_google_maps,
    "SENTRY_DSN": _test_sentry,
    "HONEYCOMB_API_KEY": _test_generic,
    "GOOGLE_OAUTH_CLIENT_ID": _test_google_oauth,
    "GOOGLE_OAUTH_CLIENT_SECRET": _test_generic,
    "MICROSOFT_OAUTH_CLIENT_ID": _test_google_oauth,
    "MICROSOFT_OAUTH_CLIENT_SECRET": _test_generic,
    "EVOLUTION_API_KEY": _test_evolution,
    "TWILIO_ACCOUNT_SID": _test_generic,
    "TWILIO_AUTH_TOKEN": _test_generic,
    "CLOUDFLARE_R2_ACCESS_KEY_ID": lambda k: _test_cloudflare_r2(k),
    "CLOUDFLARE_R2_SECRET_ACCESS_KEY": lambda k: _test_cloudflare_r2(k),
    "GEMINI_API_KEY": _test_generic,
}


def test_api_secret(service: str, value: str) -> tuple[bool, str]:
    """Prueba una clave API contra el servicio real."""
    tester = SERVICE_TESTERS.get(service)
    if not tester:
        tester = _test_generic
    try:
        return tester(value)
    except ImportError as e:
        logger.error("Dependencia faltante para testear %s: %s", service, e)
        return False, f"Librería requerida no instalada: {e}"
    except Exception as e:
        logger.debug("Test real falló para %s: %s", service, e)
        return False, str(e)[:200]
