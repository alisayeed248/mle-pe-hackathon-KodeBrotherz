from dotenv import load_dotenv
from flask import Flask, jsonify, request, g

from app.database import db, init_db
from app.errors import register_error_handlers
from app.routes import register_routes
from app.metrics import metrics_bp, start_request_tracking, end_request_tracking


def create_app():
    load_dotenv()

    app = Flask(__name__)

    init_db(app)

    from app import models  # noqa: F401 - registers models with Peewee

    # Create tables if they don't exist (handle race condition with multiple workers)
    from app.models.url import URL

    try:
        db.create_tables([URL], safe=True)
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
            end_request_tracking(
                g.start_time, request.method, endpoint, response.status_code
            )
        return response

    return app
