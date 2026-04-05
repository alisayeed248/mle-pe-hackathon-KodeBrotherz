from dotenv import load_dotenv
from flask import Flask, jsonify, request, g

from app.database import db, init_db
from app.errors import register_error_handlers
from app.routes import register_routes
from app.metrics import metrics_bp, start_request_tracking, end_request_tracking
from app.logging_config import setup_logging, get_logger


def create_app():
    load_dotenv()

    # Setup structured JSON logging
    setup_logging()
    logger = get_logger("app")

    app = Flask(__name__)

    init_db(app)

    from app import models  # noqa: F401 - registers models with Peewee

    # Create tables if they don't exist (handle race condition with multiple workers)
    from app.models.url import URL

    try:
        db.create_tables([URL], safe=True)
        logger.info("Database tables initialized", extra={"component": "database"})
    except Exception:
        # Table already exists or being created by another worker - that's fine
        pass

    register_error_handlers(app)
    register_routes(app)

    # Register metrics blueprint
    app.register_blueprint(metrics_bp)

    @app.route("/health")
    def health():
        return jsonify(status="ok")

    # Request tracking for metrics
    @app.before_request
    def before_request():
        g.start_time = start_request_tracking()

    @app.after_request
    def after_request(response):
        if hasattr(g, "start_time"):
            # Use endpoint name or path
            endpoint = request.endpoint or request.path
            duration_ms = (end_request_tracking(
                g.start_time, request.method, endpoint, response.status_code
            ) or 0) * 1000

            # Log request completion (skip /metrics and /health for noise reduction)
            if endpoint not in ("metrics.metrics", "health"):
                log_extra = {
                    "component": "http",
                    "method": request.method,
                    "path": request.path,
                    "status_code": response.status_code,
                    "duration_ms": round(duration_ms, 2),
                }
                if response.status_code >= 400:
                    get_logger("http").warning("Request failed", extra=log_extra)
                else:
                    get_logger("http").info("Request completed", extra=log_extra)
        return response

    return app
