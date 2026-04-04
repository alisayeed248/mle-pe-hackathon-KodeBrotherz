from app.routes.urls import urls_bp


def register_routes(app):
    """Register all route blueprints with the Flask app."""
    app.register_blueprint(urls_bp)