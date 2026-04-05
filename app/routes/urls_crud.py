"""URL CRUD routes (separate from redirect logic)."""
import json
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

from app.models.url import URL
from app.models.event import Event
from app.services import generate_short_code
from app.errors import NotFoundError, ValidationError
from app.logging_config import get_logger

urls_crud_bp = Blueprint("urls_crud", __name__, url_prefix="/urls")
logger = get_logger("urls_crud")


def utc_now():
    return datetime.now(timezone.utc)


def validate_json_body():
    """Validate that request has proper JSON body (Fractured Vessel)."""
    content_type = request.content_type or ""
    if request.method in ("POST", "PUT") and request.data:
        if "application/json" not in content_type:
            raise ValidationError("Content-Type must be application/json")
        try:
            data = request.get_json(force=True)
            if data is None:
                raise ValidationError("Request body must be valid JSON")
            if not isinstance(data, dict):
                raise ValidationError("Request body must be a JSON object")
            return data
        except Exception as e:
            if "ValidationError" in str(type(e)):
                raise
            raise ValidationError("Request body must be valid JSON")
    return request.get_json(silent=True) or {}


@urls_crud_bp.route("", methods=["GET"])
def list_urls():
    """List all URLs with optional filtering and pagination."""
    user_id = request.args.get("user_id", type=int)
    is_active = request.args.get("is_active")
    page = request.args.get("page", type=int, default=1)
    per_page = request.args.get("per_page", type=int, default=100)

    query = URL.select().order_by(URL.id)

    if user_id is not None:
        query = query.where(URL.user_id == user_id)

    if is_active is not None:
        # Handle string "true"/"false"
        active_bool = is_active.lower() in ("true", "1", "yes")
        query = query.where(URL.is_active == active_bool)

    # Always paginate to prevent OOM
    query = query.paginate(page, per_page)

    urls = [url.to_dict() for url in query]
    return jsonify(urls), 200


@urls_crud_bp.route("/<int:url_id>", methods=["GET"])
def get_url(url_id: int):
    """Get a URL by ID."""
    url = URL.select().where(URL.id == url_id).first()
    if not url:
        raise NotFoundError("URL not found")
    return jsonify(url.to_dict()), 200


@urls_crud_bp.route("", methods=["POST"])
def create_url():
    """Create a new URL."""
    data = validate_json_body()

    original_url = data.get("original_url")
    user_id = data.get("user_id")
    title = data.get("title")
    custom_code = data.get("short_code") or data.get("custom_code")

    # Validate required fields (Deceitful Scroll)
    if not original_url:
        raise ValidationError("original_url is required")
    if not isinstance(original_url, str):
        raise ValidationError("original_url must be a string")

    # Validate optional fields
    if user_id is not None and not isinstance(user_id, int):
        raise ValidationError("user_id must be an integer")
    if title is not None and not isinstance(title, str):
        raise ValidationError("title must be a string")
    if custom_code is not None and not isinstance(custom_code, str):
        raise ValidationError("short_code must be a string")

    # Generate short code if not provided
    if custom_code:
        short_code = custom_code.strip()
        # Check if it already exists
        existing = URL.select().where(URL.short_code == short_code).first()
        if existing:
            raise ValidationError("Short code already exists")
    else:
        for _ in range(10):
            short_code = generate_short_code()
            existing = URL.select().where(URL.short_code == short_code).first()
            if not existing:
                break
        else:
            raise ValidationError("Failed to generate unique short code")

    url = URL.create(
        original_url=original_url.strip(),
        short_code=short_code,
        user_id=user_id,
        title=title.strip() if title else None,
        created_at=utc_now(),
        updated_at=utc_now(),
    )

    # Create a "created" event
    Event.create(
        url_id=url.id,
        user_id=user_id,
        event_type="created",
        timestamp=utc_now(),
        details=json.dumps({
            "short_code": short_code,
            "original_url": original_url.strip()
        })
    )

    logger.info("URL created", extra={"component": "urls", "url_id": url.id})
    return jsonify(url.to_dict()), 201


@urls_crud_bp.route("/<int:url_id>", methods=["PUT"])
def update_url(url_id: int):
    """Update a URL."""
    url = URL.select().where(URL.id == url_id).first()
    if not url:
        raise NotFoundError("URL not found")

    data = validate_json_body()

    if "title" in data:
        if data["title"] is not None and not isinstance(data["title"], str):
            raise ValidationError("title must be a string")
        url.title = data["title"].strip() if data["title"] else None
    if "is_active" in data:
        if not isinstance(data["is_active"], bool):
            raise ValidationError("is_active must be a boolean")
        url.is_active = data["is_active"]
    if "original_url" in data:
        if not isinstance(data["original_url"], str):
            raise ValidationError("original_url must be a string")
        url.original_url = data["original_url"].strip()

    url.updated_at = utc_now()
    url.save()

    # Create an "updated" event
    Event.create(
        url_id=url.id,
        user_id=url.user_id,
        event_type="updated",
        timestamp=utc_now(),
        details=json.dumps({"changes": list(data.keys())})
    )

    logger.info("URL updated", extra={"component": "urls", "url_id": url.id})
    return jsonify(url.to_dict()), 200


@urls_crud_bp.route("/<int:url_id>", methods=["DELETE"])
def delete_url(url_id: int):
    """Delete a URL."""
    url = URL.select().where(URL.id == url_id).first()
    if not url:
        raise NotFoundError("URL not found")

    url.delete_instance()

    logger.info("URL deleted", extra={"component": "urls", "url_id": url_id})
    return jsonify({"message": "URL deleted"}), 200
