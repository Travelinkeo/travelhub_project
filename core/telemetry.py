import logging
import os

logger = logging.getLogger(__name__)


def setup_telemetry():
    """
    Inicializa OpenTelemetry y configura el exportador hacia Jaeger / Grafana Tempo.

    Soporta exportador HTTP (recomendado — compatible con Python 3.12).
    Activar con: ENABLE_TELEMETRY=True en el entorno.

    Variables de entorno:
        ENABLE_TELEMETRY: 'True' para activar (default: desactivado)
        OTLP_ENDPOINT: URL del backend OTLP (default: http://jaeger:4318)
        SERVICE_NAME: Nombre del servicio en trazas (default: travelhub-backend)
    """
    if os.environ.get("ENABLE_TELEMETRY") != "True":
        return

    try:
        # Imports perezosos — solo se evalúan si la telemetría está habilitada
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.django import DjangoInstrumentor
        from opentelemetry.sdk.resources import Resource, SERVICE_NAME
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError as e:
        logger.warning("OpenTelemetry no disponible (paquetes faltantes): %s", e)
        return

    service_name = os.environ.get("SERVICE_NAME", "travelhub-backend")
    otlp_endpoint = os.environ.get("OTLP_ENDPOINT", "http://jaeger:4318")

    # Añadir /v1/traces si no está presente (formato OTLP HTTP estándar)
    if not otlp_endpoint.endswith("/v1/traces"):
        traces_endpoint = f"{otlp_endpoint.rstrip('/')}/v1/traces"
    else:
        traces_endpoint = otlp_endpoint

    resource = Resource.create({SERVICE_NAME: service_name})
    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)

    # Exportador HTTP — compatible con Python 3.12, Jaeger y Grafana Tempo
    exporter = OTLPSpanExporter(endpoint=traces_endpoint)
    provider.add_span_processor(BatchSpanProcessor(exporter))

    # Instrumentar Django automáticamente
    DjangoInstrumentor().instrument()

    logger.info(
        "✅ OpenTelemetry activo — servicio: '%s', backend: %s",
        service_name,
        traces_endpoint,
    )
