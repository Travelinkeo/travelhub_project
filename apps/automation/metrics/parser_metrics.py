"""
Métricas de Precisión del Parser (P4-001)
=========================================

Trackea métricas de precisión del parser para monitoring y alerting.
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)


@dataclass
class ParserMetrics:
    """Métricas de una ejecución del parser"""

    parser_type: str  # 'ai', 'regex', 'gds_specific'
    success: bool
    duration_ms: int
    fields_extracted: int = 0
    fields_expected: int = 0
    field_accuracy: dict = field(default_factory=dict)
    error: str | None = None
    tokens_used: int = 0
    cost_usd: float = 0.0
    timestamp: datetime = field(default_factory=timezone.now)


class ParserMetricsCollector:
    """
    Colector de métricas de precisión del parser.
    Almacena métricas en Redis para dashboards y alerting.
    """

    CACHE_PREFIX = "parser_metrics:"
    METRICS_TTL = 86400 * 7  # 7 días

    # Campos esperados para cálculo de precisión
    EXPECTED_FIELDS = [
        "codigo_reserva",
        "pnr_aerolinea",
        "nombre_pasajero",
        "itinerario",
        "fecha_emision",
        "aerolinea_emisora",
        "tarifa_base",
        "impuestos_total",
        "total_boleto",
        "pnr",
        "passenger_name",
        "flights",
        "airline_pnr",
        "airline",
    ]

    @classmethod
    def _get_redis(cls):
        from django.core.cache import cache as django_cache

        try:
            return django_cache.client.get_client()
        except Exception:
            return None

    @classmethod
    def record_execution(cls, metrics: ParserMetrics) -> None:
        """Registra una ejecución del parser usando HINCRBY para evitar race conditions."""
        try:
            key = f"{cls.CACHE_PREFIX}{metrics.parser_type}:{metrics.timestamp.date()}"
            redis = cls._get_redis()

            if redis:
                pipe = redis.pipeline()
                pipe.hincrby(key, "total", 1)
                pipe.hincrby(key, "total_duration_ms", metrics.duration_ms)
                pipe.hincrby(key, "total_tokens", metrics.tokens_used)
                pipe.hexists(key, "total_cost")
                if metrics.success:
                    pipe.hincrby(key, "success", 1)
                else:
                    pipe.hincrby(key, "failed", 1)
                for field, accuracy in metrics.field_accuracy.items():
                    pipe.hincrbyfloat(key, f"field_acc:{field}:sum", accuracy)
                    pipe.hincrby(key, f"field_acc:{field}:count", 1)
                if metrics.parser_type == "regex" and metrics.error:
                    pipe.hincrby(key, "fallback_count", 1)
                feature = getattr(metrics, "feature", "generic")
                pipe.hincrby(key, f"feature:{feature}:total", 1)
                if metrics.success:
                    pipe.hincrby(key, f"feature:{feature}:success", 1)
                else:
                    pipe.hincrby(key, f"feature:{feature}:failed", 1)
                pipe.expire(key, 86400 * 30)
                pipe.execute()
            else:
                current = cache.get(
                    key,
                    {
                        "total": 0,
                        "success": 0,
                        "failed": 0,
                        "total_duration_ms": 0,
                        "total_tokens": 0,
                        "total_cost": 0.0,
                        "fields_accuracy": {},
                        "fallback_count": 0,
                        "by_feature": {},
                    },
                )
                current["total"] += 1
                current["total_duration_ms"] += metrics.duration_ms
                current["total_tokens"] += metrics.tokens_used
                if metrics.success:
                    current["success"] += 1
                else:
                    current["failed"] += 1
                for field, accuracy in metrics.field_accuracy.items():
                    if field not in current["fields_accuracy"]:
                        current["fields_accuracy"][field] = {"sum": 0.0, "count": 0}
                    current["fields_accuracy"][field]["sum"] += accuracy
                    current["fields_accuracy"][field]["count"] += 1
                if metrics.parser_type == "regex" and metrics.error:
                    current["fallback_count"] = current.get("fallback_count", 0) + 1
                feature = getattr(metrics, "feature", "generic")
                if feature not in current["by_feature"]:
                    current["by_feature"][feature] = {"total": 0, "success": 0, "failed": 0}
                current["by_feature"][feature]["total"] += 1
                if metrics.success:
                    current["by_feature"][feature]["success"] += 1
                else:
                    current["by_feature"][feature]["failed"] += 1
                cache.set(key, current, timeout=86400 * 30)
        except Exception as e:
            logger.warning(f"Error recording parser metrics: {e}")

    @classmethod
    def get_daily_stats(cls, date: datetime | None = None, parser_type: str | None = None) -> dict:
        """Obtiene estadísticas del día"""
        if date is None:
            date = timezone.now().date()

        if parser_type:
            key = f"{cls.CACHE_PREFIX}{parser_type}:{date}"
            return cache.get(key, {})

        # Agregar todos los parsers
        parsers = ["ai", "regex", "gds_specific", "kiu", "sabre", "amadeus"]
        aggregated = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "success_rate": 0.0,
            "avg_duration_ms": 0.0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "field_accuracy": {},
            "fallback_count": 0,
            "by_feature": {},
        }

        for p in parsers:
            key = f"{cls.CACHE_PREFIX}{p}:{date}"
            data = cache.get(key, {})
            if data:
                aggregated["total"] += data.get("total", 0)
                aggregated["success"] += data.get("success", 0)
                aggregated["failed"] += data.get("failed", 0)
                aggregated["total_duration_ms"] += data.get("total_duration_ms", 0)
                aggregated["total_tokens"] += data.get("total_tokens", 0)
                aggregated["total_cost"] += data.get("total_cost", 0)
                aggregated["fallback_count"] += data.get("fallback_count", 0)

                # Merge field accuracy
                for field, stats in data.get("fields_accuracy", {}).items():
                    if field not in aggregated["field_accuracy"]:
                        aggregated["field_accuracy"][field] = {"sum": 0.0, "count": 0}
                    aggregated["field_accuracy"][field]["sum"] += stats.get("sum", 0)
                    aggregated["field_accuracy"][field]["count"] += stats.get("count", 0)

                # Merge by_feature
                for feat, feat_data in data.get("by_feature", {}).items():
                    if feat not in aggregated["by_feature"]:
                        aggregated["by_feature"][feat] = {"total": 0, "success": 0, "failed": 0}
                    aggregated["by_feature"][feat]["total"] += feat_data.get("total", 0)
                    aggregated["by_feature"][feat]["success"] += feat_data.get("success", 0)
                    aggregated["by_feature"][feat]["failed"] += feat_data.get("failed", 0)

        if aggregated["total"] > 0:
            aggregated["success_rate"] = aggregated["success"] / aggregated["total"] * 100
            aggregated["avg_duration_ms"] = (
                aggregated["total_duration_ms"] / aggregated["total"]
                if "total_duration_ms" in aggregated
                else 0
            )

            # Calcular accuracy promedio por campo
            field_accuracy_pct = {}
            for field, stats in aggregated["field_accuracy"].items():
                if stats["count"] > 0:
                    field_accuracy_pct[field] = stats["sum"] / stats["count"] * 100
            aggregated["field_accuracy_pct"] = field_accuracy_pct

        return aggregated

    @classmethod
    def get_weekly_stats(cls, weeks: int = 4) -> list[dict]:
        """Estadísticas de las últimas N semanas"""
        results = []
        for i in range(weeks):
            date = timezone.now().date() - timedelta(days=i * 7)
            stats = cls.get_daily_stats(date)
            stats["week_start"] = date
            results.append(stats)
        return results

    @classmethod
    def check_alerts(cls) -> list[dict]:
        """Verifica alertas de calidad del parser"""
        alerts = []
        stats = cls.get_daily_stats()

        # Alerta: success rate < 80%
        if stats.get("total", 0) > 100:
            success_rate = stats.get("success_rate", 0)
            if success_rate < 80:
                alerts.append(
                    {
                        "level": "critical",
                        "type": "low_success_rate",
                        "message": f"Parser success rate: {success_rate:.1f}% (< 80%)",
                        "value": success_rate,
                        "threshold": 80,
                    }
                )

        # Alerta: fallback rate > 30%
        if stats.get("total", 0) > 50:
            fallback_rate = stats.get("fallback_count", 0) / stats.get("total", 1) * 100
            if fallback_rate > 30:
                alerts.append(
                    {
                        "level": "warning",
                        "type": "high_fallback_rate",
                        "message": f"Parser fallback rate: {fallback_rate:.1f}% (> 30%)",
                        "value": fallback_rate,
                        "threshold": 30,
                    }
                )

        # Alerta: costo diario > threshold
        # (tracking de costos pendiente)

        return alerts

    @classmethod
    def get_field_accuracy_report(cls, date: datetime | None = None) -> dict:
        """Reporte detallado de precisión por campo"""
        stats = cls.get_daily_stats(date)
        return stats.get("field_accuracy_pct", {})


# Decorator para medir automáticamente
def track_parser_metrics(parser_type: str, feature: str = "generic"):
    """
    Decorator para trackear métricas automáticamente.

    Uso:
        @track_parser_metrics("ai", "gds_parsing")
        def parse_with_ai(text):
            ...
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            start = time.time()
            error = None
            result = None
            success = True

            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error = str(e)
                raise
            finally:
                duration_ms = int((time.time() - start) * 1000)

                # Calcular campos extraídos
                fields_extracted = 0
                field_accuracy = {}
                if isinstance(result, dict):
                    for field in ParserMetricsCollector.EXPECTED_FIELDS:
                        if field in result and result[field]:
                            field_accuracy[field] = 1.0
                        else:
                            field_accuracy[field] = 0.0

                metrics = ParserMetrics(
                    parser_type=parser_type,
                    success=success,
                    duration_ms=duration_ms,
                    fields_extracted=fields_extracted,
                    fields_expected=len(ParserMetricsCollector.EXPECTED_FIELDS),
                    field_accuracy=field_accuracy,
                    error=error,
                )
                # Add feature as attribute
                metrics.feature = getattr(metrics, "feature", "generic")

                ParserMetricsCollector.record_execution(metrics)

        return wrapper

    return decorator
