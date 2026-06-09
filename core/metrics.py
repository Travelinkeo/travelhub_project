from django.http import HttpResponse
from prometheus_client import Gauge, generate_latest, REGISTRY

from travelhub.celery import app as celery_app

try:
    from django_redis import get_redis_connection
except ImportError:
    get_redis_connection = None

celery_queue_depth = Gauge(
    "travelhub_celery_queue_depth_total",
    "Number of pending tasks in Celery queues",
    ["queue"],
)

QUEUES = ["celery", "ia_fast", "ia_heavy", "notifications", "beat"]


def update_celery_queue_depth():
    if get_redis_connection is None:
        return
    try:
        r = get_redis_connection("default")
        for queue in QUEUES:
            try:
                depth = r.llen(queue)
                celery_queue_depth.labels(queue=queue).set(depth)
            except Exception:
                pass
    except Exception:
        pass


def health_metrics_view(request):
    update_celery_queue_depth()
    metrics = generate_latest(REGISTRY)
    return HttpResponse(metrics, content_type="text/plain; version=0.0.4")
