"""OpenTelemetry distributed tracing configuration."""
import os

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor


def init_tracing(app):
    """Initialize OpenTelemetry tracing for the Flask app."""

    # Check if tracing endpoint is configured
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not otlp_endpoint:
        print("OTEL_EXPORTER_OTLP_ENDPOINT not set, tracing disabled")
        return

    service_name = os.getenv("OTEL_SERVICE_NAME", "url-shortener")

    # Create resource with service info
    resource = Resource.create({
        "service.name": service_name,
        "service.instance.id": os.getenv("HOSTNAME", "unknown"),
    })

    # Create tracer provider
    provider = TracerProvider(resource=resource)

    # Configure OTLP exporter to send traces to Tempo
    otlp_exporter = OTLPSpanExporter(
        endpoint=otlp_endpoint,
        insecure=True,
    )

    # Add batch processor for efficient trace export
    provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

    # Set as global tracer provider
    trace.set_tracer_provider(provider)

    # Auto-instrument Flask
    FlaskInstrumentor().instrument_app(app)

    # Auto-instrument Redis
    RedisInstrumentor().instrument()

    # Auto-instrument PostgreSQL (psycopg2)
    Psycopg2Instrumentor().instrument()

    print(f"Tracing initialized: {service_name} -> {otlp_endpoint}")


def get_current_trace_id():
    """Get the current trace ID for log correlation."""
    span = trace.get_current_span()
    if span:
        ctx = span.get_span_context()
        if ctx.is_valid:
            return format(ctx.trace_id, '032x')
    return None
