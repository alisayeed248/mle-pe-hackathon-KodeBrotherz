import os
import time
from flask import Blueprint, Response

# Check if we're in multiprocess mode (Gunicorn)
if os.environ.get('PROMETHEUS_MULTIPROC_DIR'):
    from prometheus_client import (
        Counter, Histogram, Gauge,
        generate_latest, CONTENT_TYPE_LATEST,
        CollectorRegistry, multiprocess
    )

    # Create a custom registry for multiprocess
    def get_metrics():
        registry = CollectorRegistry()
        multiprocess.MultiProcessCollector(registry)
        return generate_latest(registry)
else:
    from prometheus_client import (
        Counter, Histogram, Gauge,
        generate_latest, CONTENT_TYPE_LATEST
    )

    def get_metrics():
        return generate_latest()

metrics_bp = Blueprint("metrics", __name__)

# === HTTP Metrics ===
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"]
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

ACTIVE_REQUESTS = Gauge(
    "http_requests_active",
    "Number of active HTTP requests",
    multiprocess_mode='livesum'
)

ERROR_COUNT = Counter(
    "http_errors_total",
    "Total HTTP errors",
    ["method", "endpoint", "status"]
)

# === Database Metrics ===
DB_QUERY_DURATION = Histogram(
    "db_query_duration_seconds",
    "Database query duration in seconds",
    ["operation"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5]
)

DB_QUERIES_TOTAL = Counter(
    "db_queries_total",
    "Total database queries",
    ["operation", "status"]
)

DB_ERRORS_TOTAL = Counter(
    "db_errors_total",
    "Total database errors",
    ["error_type"]
)


@metrics_bp.route("/metrics")
def metrics():
    """Prometheus metrics endpoint."""
    return Response(get_metrics(), mimetype=CONTENT_TYPE_LATEST)


def start_request_tracking():
    """Call at the start of each request."""
    ACTIVE_REQUESTS.inc()
    return time.perf_counter()


def end_request_tracking(start_time, method, endpoint, status_code):
    """Call at the end of each request."""
    ACTIVE_REQUESTS.dec()
    latency = time.perf_counter() - start_time

    REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status_code).inc()
    REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(latency)

    if status_code >= 400:
        ERROR_COUNT.labels(method=method, endpoint=endpoint, status=status_code).inc()


# === Database instrumentation helpers ===
def track_db_query(operation, duration, success=True):
    """Track a database query."""
    DB_QUERY_DURATION.labels(operation=operation).observe(duration)
    DB_QUERIES_TOTAL.labels(operation=operation, status="success" if success else "error").inc()


def track_db_error(error_type):
    """Track a database error by type."""
    DB_ERRORS_TOTAL.labels(error_type=error_type).inc()