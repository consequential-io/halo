"""Logging Configuration - Structured JSON logging."""

import logging
import json
import sys
from datetime import datetime, timezone
from typing import Optional


class JSONFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.

    Outputs logs in JSON format suitable for log aggregation systems.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        # Add extra fields if present
        if hasattr(record, "extra_fields"):
            log_obj.update(record.extra_fields)

        return json.dumps(log_obj)


class ContextualLogger(logging.LoggerAdapter):
    """
    Logger adapter that adds contextual information to log records.
    """

    def process(self, msg, kwargs):
        extra = kwargs.get("extra", {})
        if self.extra:
            extra.update(self.extra)
        kwargs["extra"] = {"extra_fields": extra}
        return msg, kwargs


def setup_logging(
    level: str = "INFO",
    json_output: bool = True,
    app_name: str = "agatha"
) -> None:
    """
    Set up application logging.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_output: If True, output JSON formatted logs
        app_name: Application name for log context
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))

    # Clear existing handlers
    root_logger.handlers.clear()

    # Create handler
    handler = logging.StreamHandler(sys.stdout)

    if json_output:
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        ))

    root_logger.addHandler(handler)

    # Set log levels for noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("google").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def get_logger(name: str, **context) -> ContextualLogger:
    """
    Get a contextual logger.

    Args:
        name: Logger name
        **context: Additional context to include in all log messages

    Returns:
        ContextualLogger instance
    """
    logger = logging.getLogger(name)
    return ContextualLogger(logger, context)


# Request context logger factory
def get_request_logger(
    name: str,
    request_id: Optional[str] = None,
    user_id: Optional[str] = None,
    **extra
) -> ContextualLogger:
    """
    Get a logger with request context.

    Args:
        name: Logger name
        request_id: Request identifier
        user_id: User identifier
        **extra: Additional context

    Returns:
        ContextualLogger instance
    """
    context = {}
    if request_id:
        context["request_id"] = request_id
    if user_id:
        context["user_id"] = user_id
    context.update(extra)

    return get_logger(name, **context)
