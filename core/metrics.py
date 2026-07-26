import logging

from django.db import connection
from django.http import HttpResponse
from prometheus_client import REGISTRY, Gauge, generate_latest

try:
    from django_redis import get_redis_connection
except ImportError:
    get_redis_connection = None

logger = logging.getLogger(__name__)

celery_queue_depth = Gauge(
    "travelhub_celery_queue_depth_total",
    "Number of pending tasks in Celery queues",
    ["queue"],
)

db_active_connections = Gauge(
    "travelhub_db_active_connections",
    "Active database connections from pg_stat_activity",
)
db_max_connections = Gauge(
    "travelhub_db_max_connections",
    "PostgreSQL max_connections setting",
)

QUEUES = ["celery", "notifications", "beat"]
DB_POOL_ALERT_PCT = 80


def update_celery_queue_depth():
    """update_celery_queue_depth."""
    if get_redis_connection is None:
        return
    try:
        r = get_redis_connection("default")
        for queue in QUEUES:
            try:
                depth = r.llen(queue)
                celery_queue_depth.labels(queue=queue).set(depth)
            except Exception as e:
                logger.debug("Ignored exception reading queue depth: %s", e)
    except Exception as e:
        logger.debug("Ignored exception connecting to Redis for metrics: %s", e)


def update_db_connection_pool():
    """update_db_connection_pool."""
    active = None
    max_conn = 0
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM pg_stat_activity WHERE state = 'active'")
            active = cursor.fetchone()[0]
            db_active_connections.set(active)
    except Exception as e:
        logger.debug("Failed to query pg_stat_activity: %s", e)
    try:
        with connection.cursor() as cursor:
            cursor.execute("SHOW max_connections")
            max_conn = int(cursor.fetchone()[0])
            db_max_connections.set(max_conn)
    except Exception as e:
        logger.debug("Failed to query max_connections: %s", e)

    if active is not None and max_conn > 0:
        pct = (active / max_conn) * 100
        if pct > DB_POOL_ALERT_PCT:
            logger.warning(
                "DB pool alert: %d active of %d max (%.0f%%)",
                active,
                max_conn,
                pct,
            )


def health_metrics_view(request):
    """health_metrics_view."""
    update_celery_queue_depth()
    update_db_connection_pool()
    metrics = generate_latest(REGISTRY)
    return HttpResponse(metrics, content_type="text/plain; version=0.0.4")
