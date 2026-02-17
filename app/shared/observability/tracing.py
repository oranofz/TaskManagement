"""Distributed tracing configuration using OpenTelemetry."""
from typing import Optional
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION, DEPLOYMENT_ENVIRONMENT
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.propagate import set_global_textmap
from loguru import logger

# Global tracer instance
_tracer: Optional[trace.Tracer] = None


def setup_tracing(
    service_name: str = "task-management-system",
    service_version: str = "1.0.0",
    environment: str = "development",
    otlp_endpoint: Optional[str] = None
) -> trace.Tracer:
    """
    Setup OpenTelemetry distributed tracing.

    Args:
        service_name: Name of the service for tracing
        service_version: Version of the service
        environment: Deployment environment (development, staging, production)
        otlp_endpoint: OTLP exporter endpoint (optional, defaults to console exporter)

    Returns:
        Configured tracer instance
    """
    global _tracer

    # Create resource with service information
    resource = Resource.create({
        SERVICE_NAME: service_name,
        SERVICE_VERSION: service_version,
        DEPLOYMENT_ENVIRONMENT: environment,
    })

    # Create tracer provider
    provider = TracerProvider(resource=resource)

    # Configure exporter based on environment
    if otlp_endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
            exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
            logger.info(f"OpenTelemetry configured with OTLP exporter: {otlp_endpoint}")
        except ImportError:
            logger.warning("OTLP exporter not available, falling back to console exporter")
            exporter = ConsoleSpanExporter()
    else:
        # Use console exporter for development/testing
        exporter = ConsoleSpanExporter()
        logger.info("OpenTelemetry configured with console exporter")

    # Add batch processor for performance
    processor = BatchSpanProcessor(exporter)
    provider.add_span_processor(processor)

    # Set global tracer provider
    trace.set_tracer_provider(provider)

    # Set global text map propagator for context propagation
    set_global_textmap(TraceContextTextMapPropagator())

    # Create tracer instance
    _tracer = trace.get_tracer(service_name, service_version)

    logger.info(
        f"OpenTelemetry tracing initialized",
        service_name=service_name,
        service_version=service_version,
        environment=environment
    )

    return _tracer


def instrument_fastapi(app) -> None:
    """
    Instrument FastAPI application with OpenTelemetry.

    Args:
        app: FastAPI application instance
    """
    FastAPIInstrumentor.instrument_app(
        app,
        excluded_urls="/health,/ready,/live,/docs,/openapi.json,/redoc"
    )
    logger.info("FastAPI instrumented with OpenTelemetry")


def instrument_sqlalchemy(engine) -> None:
    """
    Instrument SQLAlchemy engine with OpenTelemetry.

    Args:
        engine: SQLAlchemy engine instance
    """
    SQLAlchemyInstrumentor().instrument(
        engine=engine.sync_engine,
        enable_commenter=True
    )
    logger.info("SQLAlchemy instrumented with OpenTelemetry")


def instrument_redis() -> None:
    """
    Instrument Redis client with OpenTelemetry.
    """
    RedisInstrumentor().instrument()
    logger.info("Redis instrumented with OpenTelemetry")


def get_tracer() -> trace.Tracer:
    """
    Get the configured tracer instance.

    Returns:
        Tracer instance

    Raises:
        RuntimeError: If tracing has not been initialized
    """
    global _tracer
    if _tracer is None:
        # Initialize with defaults if not already done
        _tracer = setup_tracing()
    return _tracer


def create_span(
    name: str,
    attributes: Optional[dict] = None,
    kind: trace.SpanKind = trace.SpanKind.INTERNAL
):
    """
    Create a new span for manual tracing.

    Args:
        name: Name of the span
        attributes: Optional attributes to add to the span
        kind: Type of span (INTERNAL, SERVER, CLIENT, PRODUCER, CONSUMER)

    Returns:
        Context manager for the span
    """
    tracer = get_tracer()
    span = tracer.start_as_current_span(name, kind=kind)

    if attributes:
        current_span = trace.get_current_span()
        for key, value in attributes.items():
            current_span.set_attribute(key, value)

    return span


def get_current_trace_id() -> Optional[str]:
    """
    Get the current trace ID if available.

    Returns:
        Trace ID as hex string or None
    """
    current_span = trace.get_current_span()
    if current_span and current_span.is_recording():
        return format(current_span.get_span_context().trace_id, '032x')
    return None

def add_span_attributes(**attributes) -> None:
    """
    Add attributes to the current span.

    Args:
        **attributes: Key-value pairs to add as span attributes
    """
    current_span = trace.get_current_span()
    if current_span and current_span.is_recording():
        for key, value in attributes.items():
            if value is not None:
                current_span.set_attribute(key, str(value))
