"""
Structured JSON logging configuration.
Outputs logs as JSON with timestamps and log levels for machine parsing.
"""
import logging
import json
import sys
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """Format log records as JSON for structured logging."""

    def format(self, record):
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add extra fields if present
        if hasattr(record, "component"):
            log_data["component"] = record.component
        if hasattr(record, "short_code"):
            log_data["short_code"] = record.short_code
        if hasattr(record, "method"):
            log_data["method"] = record.method
        if hasattr(record, "path"):
            log_data["path"] = record.path
        if hasattr(record, "status_code"):
            log_data["status_code"] = record.status_code
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms
        if hasattr(record, "error_type"):
            log_data["error_type"] = record.error_type
        if hasattr(record, "cache_hit"):
            log_data["cache_hit"] = record.cache_hit

        # Include exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


def setup_logging(app_name="url-shortener"):
    """
    Configure structured JSON logging for the application.
    Returns the root logger configured for JSON output.
    """
    # Create JSON formatter
    json_formatter = JSONFormatter()

    # Configure stream handler (stdout for Docker to capture)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(json_formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers = []  # Clear existing handlers
    root_logger.addHandler(stream_handler)

    # Configure app-specific logger
    app_logger = logging.getLogger(app_name)
    app_logger.setLevel(logging.INFO)

    # Suppress noisy loggers
    logging.getLogger("werkzeug").setLevel(logging.WARNING)

    return app_logger


def get_logger(name=None):
    """Get a logger instance for the given name."""
    if name:
        return logging.getLogger(f"url-shortener.{name}")
    return logging.getLogger("url-shortener")
