import logging
import time

from django.db import connection

try:
    from prometheus_client import Counter, Gauge, Histogram

    request_duration = Histogram(
        "travelhub_request_duration_seconds",
        "Request duration by path and method",
        ["method", "path", "status"],
        buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    )
    query_count = Gauge(
        "travelhub_request_db_queries",
        "Number of DB queries per request",
        ["method", "path"],
    )
    n_plus_one_alert = Counter(
        "travelhub_nplus_one_alerts_total",
        "Requests with excessive DB queries",
        ["method", "path"],
    )
except ImportError:
    request_duration = None
    query_count = None
    n_plus_one_alert = None

logger = logging.getLogger(__name__)

N_PLUS_ONE_THRESHOLD = 15
N_PLUS_ONE_TIME_THRESHOLD = 1.0


class QueryCountDebugMiddleware:
    """Middleware que monitorea queries y exporta métricas Prometheus"""

    def __init__(self, get_response):
        """__init__."""
        self.get_response = get_response

    def __call__(self, request):
        connection.queries_log.clear()
        start_time = time.time()

        response = self.get_response(request)

        duration = time.time() - start_time
        num_queries = len(connection.queries)

        path = request.path
        method = request.method
        status = response.status_code

        if request_duration is not None:
            request_duration.labels(method=method, path=path, status=str(status)).observe(duration)
        if query_count is not None:
            query_count.labels(method=method, path=path).set(num_queries)

        is_n_plus_one = num_queries > N_PLUS_ONE_THRESHOLD and duration > N_PLUS_ONE_TIME_THRESHOLD
        if is_n_plus_one:
            if n_plus_one_alert is not None:
                n_plus_one_alert.labels(method=method, path=path).inc()
            logger.warning(
                "N+1 alert: %s %s — %d queries en %.2fs",
                method,
                path,
                num_queries,
                duration,
            )
        elif num_queries > 5:
            logger.debug("%s %s — %d queries en %.2fs", method, path, num_queries, duration)

        return response


class CacheHeaderMiddleware:
    """Middleware para agregar headers de caché"""

    def __init__(self, get_response):
        """__init__."""
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if (
            request.path.startswith("/api/paises")
            or request.path.startswith("/api/monedas")
            or request.path.startswith("/api/aerolineas")
        ):
            response["Cache-Control"] = "public, max-age=3600"
        elif request.path.startswith("/api/ciudades"):
            response["Cache-Control"] = "public, max-age=1800"

        return response
