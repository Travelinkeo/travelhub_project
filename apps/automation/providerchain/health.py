"""Proveedor de IA/configuración para automation: health.
"""

import json
import logging
from datetime import datetime, timedelta

from django.core.cache import cache
from django.utils import timezone

from core.models import APISecret

from .registry import provider_registry

logger = logging.getLogger(__name__)

HEALTH_INTERVAL_SECONDS = 60 * 60  # 1 hora
HEALTH_HISTORY_MAX = 168  # 7 días × 24 checks


def run_health_checks(force: bool = False) -> list[dict]:
    """
    Ejecuta health checks para todos los proveedores y claves API.
    Respeta el intervalo de 1 hora a menos que force=True.
    """
    last_run_key = "health_check_providers_last_run"
    now = timezone.now()

    if not force:
        last_run = cache.get(last_run_key)
        if last_run:
            elapsed = (now - last_run).total_seconds()
            if elapsed < HEALTH_INTERVAL_SECONDS:
                logger.debug("Health checks reciente (%ds atrás), saltando", elapsed)
                return []

    results = []

    # 1. Probar proveedores de IA
    for provider in provider_registry.all():
        ok = provider.test_connection()
        status = "ok" if ok else "fail"
        results.append(
            {
                "type": "provider",
                "name": provider.provider_name,
                "status": status,
                "supports_structured": provider.supports_structured_output,
                "is_emergency": provider.is_emergency_only,
            }
        )
        if ok:
            provider_registry.close_circuit(provider.provider_name)
            logger.info("Health: %s OK", provider.provider_name)
        else:
            logger.warning("Health: %s FAIL", provider.provider_name)

    # 2. Probar conexión de claves API registradas (test_status = "unknown" o último test > 24h)
    cutoff = timezone.now() - timedelta(hours=24)
    secrets_to_test = APISecret.objects.filter(
        is_active=True,
    ).filter(test_status="unknown") | APISecret.objects.filter(
        is_active=True,
        last_tested__lt=cutoff,
    )

    for secret in secrets_to_test.distinct():
        from core.api import test_api_secret as real_test

        success, msg = real_test(secret.service, secret.value)
        secret.last_tested = timezone.now()
        secret.test_status = "ok" if success else "fail"
        secret.save(update_fields=["last_tested", "test_status"])
        results.append(
            {
                "type": "api_secret",
                "name": secret.service,
                "status": secret.test_status,
                "detail": msg,
            }
        )

    # 3. Guardar histórico en Redis (lista JSON, capped a 168 entradas)
    _store_history(results)

    cache.set(last_run_key, now, HEALTH_INTERVAL_SECONDS)
    logger.info("Health checks completados: %d tests", len(results))
    return results


def _store_history(results: list[dict]) -> None:
    """Guarda el resultado de un health check en el histórico Redis."""
    try:
        from django.utils import timezone

        entry = {
            "ts": timezone.now().isoformat(),
            "results": results,
        }
        key = "health_history"
        cache.client.get_client().lpush(key, json.dumps(entry))
        cache.client.get_client().ltrim(key, 0, HEALTH_HISTORY_MAX - 1)
        cache.client.get_client().expire(key, 86400 * 30)  # 30 días TTL
    except Exception as e:
        logger.debug("Error guardando histórico de salud: %s", e)


def get_health_history(hours: int = 24) -> list[dict]:
    """Retorna el histórico de health checks de las últimas N horas."""
    try:
        client = cache.client.get_client()
        raw = client.lrange("health_history", 0, HEALTH_HISTORY_MAX - 1)
        cutoff = timezone.now() - timedelta(hours=hours)
        entries = []
        for item in raw:
            entry = json.loads(item)
            ts = datetime.fromisoformat(entry["ts"])
            if ts >= cutoff:
                entries.append(entry)
        return entries
    except Exception as e:
        logger.debug("Error leyendo histórico de salud: %s", e)
        return []


def get_health_summary() -> dict:
    """Retorna un resumen del estado de salud actual."""
    providers = []
    for provider in provider_registry.all():
        from .registry import provider_registry as reg

        circuit_open = reg._circuit_open(provider.provider_name)
        providers.append(
            {
                "name": provider.provider_name,
                "circuit_open": circuit_open,
                "supports_structured": provider.supports_structured_output,
                "is_emergency": provider.is_emergency_only,
            }
        )

    secrets_ok = APISecret.objects.filter(is_active=True, test_status="ok").count()
    secrets_fail = APISecret.objects.filter(is_active=True, test_status="fail").count()
    secrets_unknown = APISecret.objects.filter(is_active=True, test_status="unknown").count()

    return {
        "providers": providers,
        "api_secrets": {
            "ok": secrets_ok,
            "fail": secrets_fail,
            "unknown": secrets_unknown,
            "total": secrets_ok + secrets_fail + secrets_unknown,
        },
    }
