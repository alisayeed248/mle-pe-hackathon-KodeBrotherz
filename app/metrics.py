from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from flask import Blueprint, Response
import time

metrics_bp = Blueprint("metrics", __name__)

# Metrics
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
    "Number of active HTTP requests"
)

ERROR_COUNT = Counter(
    "http_errors_total",
    "Total HTTP errors",
    ["method", "endpoint", "status"]
)


@metrics_bp.route("/metrics")
def metrics():
    """Prometheus metrics endpoint."""
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


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