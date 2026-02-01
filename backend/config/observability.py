"""Observability Configuration - OpenTelemetry + Google ADK tracing."""

import os
import logging
from typing import Optional
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Check for observability dependencies
HAS_OPENTELEMETRY = False
HAS_FI_INSTRUMENTATION = False
HAS_TRACEAI_ADK = False

try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    from opentelemetry.sdk.resources import Resource
    HAS_OPENTELEMETRY = True
except ImportError:
    trace = None  # type: ignore
    TracerProvider = None  # type: ignore
    BatchSpanProcessor = None  # type: ignore
    ConsoleSpanExporter = None  # type: ignore
    Resource = None  # type: ignore

try:
    from fi_instrumentation import register
    from fi_instrumentation.fi_types import ProjectType
    HAS_FI_INSTRUMENTATION = True
except ImportError:
    register = None  # type: ignore
    ProjectType = None  # type: ignore

try:
    from traceai_google_adk import GoogleADKInstrumentor
    HAS_TRACEAI_ADK = True
except ImportError:
    GoogleADKInstrumentor = None  # type: ignore


class ObservabilityManager:
    """
    Manager for observability features including tracing and metrics.
    """

    _instance: Optional["ObservabilityManager"] = None
    _tracer_provider = None
    _initialized: bool = False

    def __new__(cls) -> "ObservabilityManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def setup(
        self,
        project_name: str = "agatha",
        enable_console_export: bool = False,
        enable_fi: bool = True
    ) -> None:
        """
        Set up observability with tracing.

        Args:
            project_name: Project name for traces
            enable_console_export: Export traces to console (for debugging)
            enable_fi: Use FI instrumentation if available
        """
        if self._initialized:
            logger.debug("Observability already initialized")
            return

        self._initialized = True

        # Try FI instrumentation first (production)
        if enable_fi and HAS_FI_INSTRUMENTATION and register:
            try:
                self._tracer_provider = register(
                    project_type=ProjectType.OBSERVE,
                    project_name=project_name
                )
                logger.info(f"FI instrumentation registered for project: {project_name}")

                # Instrument Google ADK if available
                if HAS_TRACEAI_ADK and GoogleADKInstrumentor:
                    GoogleADKInstrumentor().instrument(tracer_provider=self._tracer_provider)
                    logger.info("Google ADK instrumented")

                return
            except Exception as e:
                logger.warning(f"FI instrumentation failed: {e}")

        # Fall back to basic OpenTelemetry
        if HAS_OPENTELEMETRY:
            try:
                resource = Resource.create({
                    "service.name": project_name,
                    "service.version": "0.1.0",
                })

                self._tracer_provider = TracerProvider(resource=resource)

                if enable_console_export:
                    self._tracer_provider.add_span_processor(
                        BatchSpanProcessor(ConsoleSpanExporter())
                    )

                trace.set_tracer_provider(self._tracer_provider)
                logger.info(f"OpenTelemetry initialized for project: {project_name}")

                # Instrument Google ADK if available
                if HAS_TRACEAI_ADK and GoogleADKInstrumentor:
                    GoogleADKInstrumentor().instrument(tracer_provider=self._tracer_provider)
                    logger.info("Google ADK instrumented")

            except Exception as e:
                logger.warning(f"OpenTelemetry setup failed: {e}")
        else:
            logger.info("Observability disabled - no tracing libraries available")

    def get_tracer(self, name: str = "agatha"):
        """Get a tracer for creating spans."""
        if HAS_OPENTELEMETRY and trace:
            return trace.get_tracer(name)
        return MockTracer()

    @contextmanager
    def span(self, name: str, attributes: dict = None):
        """
        Context manager for creating spans.

        Args:
            name: Span name
            attributes: Optional attributes to add to the span
        """
        tracer = self.get_tracer()
        with tracer.start_as_current_span(name) as span:
            if attributes and hasattr(span, 'set_attributes'):
                span.set_attributes(attributes)
            yield span


class MockTracer:
    """Mock tracer for when OpenTelemetry is not available."""

    def start_as_current_span(self, name: str, **kwargs):
        return MockSpan(name)


class MockSpan:
    """Mock span for when OpenTelemetry is not available."""

    def __init__(self, name: str):
        self.name = name

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def set_attributes(self, attributes: dict):
        pass

    def add_event(self, name: str, attributes: dict = None):
        pass

    def set_status(self, status):
        pass


# Singleton instance
_observability: Optional[ObservabilityManager] = None


def setup_observability(
    project_name: str = None,
    enable_console_export: bool = False
) -> ObservabilityManager:
    """
    Set up observability for the application.

    Args:
        project_name: Project name (defaults to FI_PROJECT_NAME env var)
        enable_console_export: Export traces to console

    Returns:
        ObservabilityManager instance
    """
    global _observability

    if project_name is None:
        from config.settings import settings
        project_name = settings.fi_project_name

    if _observability is None:
        _observability = ObservabilityManager()

    _observability.setup(
        project_name=project_name,
        enable_console_export=enable_console_export
    )

    return _observability


def get_observability() -> ObservabilityManager:
    """Get the observability manager instance."""
    global _observability
    if _observability is None:
        _observability = setup_observability()
    return _observability


def get_tracer(name: str = "agatha"):
    """Get a tracer for creating spans."""
    return get_observability().get_tracer(name)


@contextmanager
def trace_span(name: str, attributes: dict = None):
    """
    Context manager for creating traced spans.

    Args:
        name: Span name
        attributes: Optional span attributes

    Usage:
        with trace_span("process_request", {"user_id": "123"}):
            # Your code here
    """
    with get_observability().span(name, attributes) as span:
        yield span
