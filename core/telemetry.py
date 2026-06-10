import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.django import DjangoInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def setup_telemetry():
    """
    Inicializa OpenTelemetry y configura el exportador hacia Jaeger / OTLP Backend.
    Debe llamarse desde manage.py o wsgi.py antes de cargar Django.
    """
    if os.environ.get("ENABLE_TELEMETRY") != "True":
        return

    # Define the service name resource
    resource = Resource.create({"service.name": "travelhub-backend"})

    # Set the Tracer Provider
    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)

    # Configurar el exportador OTLP apuntando a Jaeger (ej: localhost:4317 en dev)
    otlp_endpoint = os.environ.get("OTLP_ENDPOINT", "http://localhost:4317")
    otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)

    # Procesador de Spans por lotes
    span_processor = BatchSpanProcessor(otlp_exporter)
    provider.add_span_processor(span_processor)

    # Instrumentar Django automáticamente
    DjangoInstrumentor().instrument()

    import logging

    logging.getLogger(__name__).info(
        f"OpenTelemetry habilitado. Enviando trazas a: {otlp_endpoint}"
    )
