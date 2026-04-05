from app.routes.urls import urls_bp
from app.routes.chaos import chaos_bp


def register_routes(app):
    """Register all route blueprints with the Flask app."""
    app.register_blueprint(urls_bp)
    app.register_blueprint(chaos_bp)