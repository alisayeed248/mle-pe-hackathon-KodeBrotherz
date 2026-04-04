"""
Database instrumentation for tracking query timing.
Use the timed_db_operation context manager around DB calls.
"""
import time
from contextlib import contextmanager
from peewee import OperationalError, IntegrityError
from app.metrics import track_db_query, track_db_error


def classify_error(exc):
    """
    Classify a database exception into a category for metrics.
    - "connection" = can't reach DB (pool exhausted, DB down)
    - "timeout" = query took too long
    - "integrity" = constraint violation (duplicate key, etc.)
    - "other" = something else
    """
    exc_str = str(exc).lower()

    if isinstance(exc, OperationalError):
        if "connection" in exc_str or "refused" in exc_str:
            return "connection"
        if "timeout" in exc_str:
            return "timeout"
        return "operational"

    if isinstance(exc, IntegrityError):
        return "integrity"

    return "other"


@contextmanager
def timed_db_operation(operation):
    """
    Context manager to time database operations.

    Usage:
        with timed_db_operation("select"):
            result = URL.select().where(...).first()

    Automatically tracks:
    - Duration (how long the query took)
    - Success/failure
    - Error type if failed
    """
    start_time = time.perf_counter()
    try:
        yield
        duration = time.perf_counter() - start_time
        track_db_query(operation, duration, success=True)
    except Exception as exc:
        duration = time.perf_counter() - start_time
        track_db_query(operation, duration, success=False)
        track_db_error(classify_error(exc))
        raise
