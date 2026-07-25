"""Proveedor de IA/configuración para automation: tracing.
"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta

from django.core.cache import cache

logger = logging.getLogger(__name__)

METRICS_TTL = 60 * 60 * 24  # 24 horas
LATENCY_TTL = 60 * 60 * 2  # 2 horas (solo retenemos latencias recientes)
LATENCY_SAMPLE_SIZE = 1000  # máx entradas de latencia por hora

# Precios por 1K tokens (USD) — referencia pública
PROVIDER_PRICING: dict[str, dict[str, float]] = {
    "gemini": {"input": 0.000075, "output": 0.0003},
    "openai": {"input": 0.00015, "output": 0.0006},
    "deepseek": {"input": 0.00007, "output": 0.00028},
}


def _estimated_cost(provider: str, tokens_in: int, tokens_out: int) -> float:
    # _estimated_cost:  estimated cost. Args: según implementación. Returns: según implementación.
    pricing = PROVIDER_PRICING.get(provider, {"input": 0.0001, "output": 0.0004})
    return (tokens_in * pricing["input"] + tokens_out * pricing["output"]) / 1000


def _categorize_error(error_str: str) -> str:
    # _categorize_error:  categorize error. Args: según implementación. Returns: según implementación.
    error_lower = error_str.lower()
    if any(w in error_lower for w in ("timeout", "timed out", "deadline")):
        return "timeout"
    if any(w in error_lower for w in ("429", "rate limit", "quota", "resource_exhausted")):
        return "rate_limit"
    if any(w in error_lower for w in ("401", "403", "unauthorized", "auth", "api key")):
        return "auth"
    return "other"


def record_call(
    provider: str,
    model: str,
    duration_ms: int,
    tokens_in: int = 0,
    tokens_out: int = 0,
    success: bool = True,
    feature: str = "unknown",
    error_str: str | None = None,
) -> None:
    """Registra métricas agregadas con costos y categorización de errores."""
    now = datetime.utcnow()
    hour_key = now.strftime("%Y%m%d%H")
    cost = _estimated_cost(provider, tokens_in, tokens_out)

    pipe = {
        f"ai_metrics:{hour_key}:count": 1,
        f"ai_metrics:{hour_key}:errors": 0 if success else 1,
        f"ai_metrics:{hour_key}:tokens_in": tokens_in,
        f"ai_metrics:{hour_key}:tokens_out": tokens_out,
        f"ai_metrics:{hour_key}:duration_ms": duration_ms,
        f"ai_metrics:{hour_key}:cost": int(cost * 100000),  # microUSD para enteros
        f"ai_metrics:{hour_key}:provider:{provider}": 1,
        f"ai_metrics:{hour_key}:feature:{feature}": 1,
    }

    if not success and error_str:
        error_type = _categorize_error(error_str)
        pipe[f"ai_metrics:{hour_key}:error_type:{error_type}"] = 1
        pipe[f"ai_metrics:{hour_key}:error_provider:{provider}"] = 1

    try:
        for key, delta in pipe.items():
            try:
                new_val = (cache.get(key) or 0) + delta
                cache.set(key, new_val, METRICS_TTL)
            except Exception:
                cache.set(key, delta, METRICS_TTL)

        _record_latency_sample(hour_key, provider, duration_ms)
    except Exception as e:
        logger.debug("Error registrando métrica: %s", e)


def record_call_simple(
    provider: str,
    duration_ms: int,
    success: bool = True,
    feature: str = "unknown",
) -> None:
    """Versión simplificada cuando no hay tokens (ej: health check)."""
    record_call(
        provider=provider,
        model="",
        duration_ms=duration_ms,
        tokens_in=0,
        tokens_out=0,
        success=success,
        feature=feature,
    )


def _record_latency_sample(hour_key: str, provider: str, duration_ms: int) -> None:
    """Almacena muestra de latencia para cálculos de percentiles."""
    key = f"ai_metrics:{hour_key}:latency:{provider}"
    try:
        samples = cache.get(key) or []
        if isinstance(samples, list) and len(samples) < LATENCY_SAMPLE_SIZE:
            samples.append(duration_ms)
            cache.set(key, samples, LATENCY_TTL)
    except Exception:
        logger.exception("Error almacenando muestra de latencia para %s", provider)


def _get_latency_samples(hour_key: str, provider: str) -> list[int]:
    # _get_latency_samples:  get latency samples. Args: según implementación. Returns: según implementación.
    try:
        return cache.get(f"ai_metrics:{hour_key}:latency:{provider}") or []
    except Exception:
        return []


def _get_percentiles(values: list[int]) -> dict[str, float]:
    # _get_percentiles:  get percentiles. Args: según implementación. Returns: según implementación.
    if not values:
        return {"p50": 0, "p95": 0, "p99": 0}
    values.sort()
    n = len(values)
    return {
        "p50": float(values[int(n * 0.5)]),
        "p95": float(values[int(n * 0.95)]),
        "p99": float(values[int(n * 0.99)]),
    }


def get_hourly_metrics(hours: int = 24) -> dict:
    """Retorna métricas agregadas de las últimas N horas con costos y percentiles."""
    now = datetime.utcnow()
    totals = defaultdict(float)
    error_types: dict[str, int] = defaultdict(int)
    all_latencies: dict[str, list[int]] = defaultdict(list)

    for i in range(hours):
        hour_key = (now - timedelta(hours=i)).strftime("%Y%m%d%H")
        try:
            totals["calls"] += cache.get(f"ai_metrics:{hour_key}:count") or 0
            totals["errors"] += cache.get(f"ai_metrics:{hour_key}:errors") or 0
            totals["tokens_in"] += cache.get(f"ai_metrics:{hour_key}:tokens_in") or 0
            totals["tokens_out"] += cache.get(f"ai_metrics:{hour_key}:tokens_out") or 0
            totals["duration_ms"] += cache.get(f"ai_metrics:{hour_key}:duration_ms") or 0
            totals["cost_usd"] += (cache.get(f"ai_metrics:{hour_key}:cost") or 0) / 100000

            for etype in ("timeout", "rate_limit", "auth", "other"):
                val = cache.get(f"ai_metrics:{hour_key}:error_type:{etype}") or 0
                error_types[etype] += val

            for provider in ("gemini", "openai", "deepseek"):
                latencies = _get_latency_samples(hour_key, provider)
                all_latencies[provider].extend(latencies)
        except Exception:
            logger.exception("Error obteniendo métricas para hora %s", hour_key)
            continue

    percentiles = {}
    for provider, latencies in all_latencies.items():
        percentiles[provider] = _get_percentiles(latencies)
    percentiles["all"] = _get_percentiles([v for vals in all_latencies.values() for v in vals])

    total_calls = totals.get("calls", 0) or 1

    return {
        "period_hours": hours,
        "total_calls": int(totals.get("calls", 0)),
        "total_errors": int(totals.get("errors", 0)),
        "error_rate": round(totals.get("errors", 0) / total_calls * 100, 2),
        "total_tokens_in": int(totals.get("tokens_in", 0)),
        "total_tokens_out": int(totals.get("tokens_out", 0)),
        "avg_duration_ms": round(totals["duration_ms"] / total_calls, 1),
        "estimated_cost_usd": round(totals.get("cost_usd", 0), 6),
        "error_types": dict(error_types),
        "latency_percentiles": percentiles,
    }
