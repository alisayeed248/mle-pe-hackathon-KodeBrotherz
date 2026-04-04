from flask import jsonify


class APIError(Exception):
    """Base exception for API errors."""

    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class ValidationError(APIError):
    """400 Bad Request - validation failed."""

    def __init__(self, message: str):
        super().__init__(message, 400)


class NotFoundError(APIError):
    """404 Not Found."""

    def __init__(self, message: str):
        super().__init__(message, 404)


class ConflictError(APIError):
    """409 Conflict - duplicate resource."""

    def __init__(self, message: str = "Resource already exists"):
        super().__init__(message, 409)


class GoneError(APIError):
    """410 Gone - expired/inactive resource."""

    def __init__(self, message: str = "Resource is no longer available"):
        super().__init__(message, 410)


def register_error_handlers(app):
    """Register global error handlers that return JSON."""

    @app.errorhandler(APIError)
    def handle_api_error(error):
        return jsonify({"error": error.message}), error.status_code

    @app.errorhandler(400)
    def handle_400(error):
        return jsonify({"error": "Bad request"}), 400

    @app.errorhandler(404)
    def handle_404(error):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(405)
    def handle_405(error):
        return jsonify({"error": "Method not allowed"}), 405

    @app.errorhandler(500)
    def handle_500(error):
        # Never expose stack traces
        return jsonify({"error": "Internal server error"}), 500
