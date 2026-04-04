from datetime import datetime, timezone

from flask import Blueprint, jsonify, redirect, request

from app.errors import ConflictError, GoneError, NotFoundError, ValidationError
from app.models.url import URL
from app.services import (
    generate_short_code,
    validate_custom_code,
    validate_url,
)
from app.db_instrumentation import timed_db_operation

urls_bp = Blueprint("urls", __name__)


@urls_bp.route("/shorten", methods=["POST"])
def shorten_url():
    """Create a shortened URL."""
    data = request.get_json(silent=True) or {}

    original_url = data.get("url")
    custom_code = data.get("custom_code")

    # Validate URL
    is_valid, error_msg = validate_url(original_url)
    if not is_valid:
        raise ValidationError(error_msg)

    # Validate custom code if provided
    is_valid, error_msg = validate_custom_code(custom_code)
    if not is_valid:
        raise ValidationError(error_msg)

    # Generate or use custom code
    if custom_code:
        short_code = custom_code.strip()
        # Check if already exists
        with timed_db_operation("select"):
            exists = URL.select().where(URL.short_code == short_code).exists()
        if exists:
            raise ConflictError("Short code already exists")
    else:
        # Generate unique code (retry on collision)
        for _ in range(10):
            short_code = generate_short_code()
            with timed_db_operation("select"):
                exists = URL.select().where(URL.short_code == short_code).exists()
            if not exists:
                break
        else:
            raise ValidationError("Failed to generate unique short code")

    # Create the URL record
    with timed_db_operation("insert"):
        url_record = URL.create(
            original_url=original_url.strip(),
            short_code=short_code,
        )

    # Build the short URL
    short_url = f"{request.host_url}{short_code}"

    return (
        jsonify(
            {
                "short_code": short_code,
                "short_url": short_url,
            }
        ),
        201,
    )


@urls_bp.route("/<code>", methods=["GET"])
def redirect_url(code: str):
    """Redirect to the original URL."""
    with timed_db_operation("select"):
        url_record = URL.select().where(URL.short_code == code).first()

    if not url_record:
        raise NotFoundError("Short URL not found")

    # Check if expired
    if url_record.expires_at and url_record.expires_at < datetime.now(timezone.utc):
        raise GoneError("Short URL has expired")

    # Check if active
    if not url_record.is_active:
        raise GoneError("Short URL is no longer active")

    # Increment click count
    with timed_db_operation("update"):
        URL.update(click_count=URL.click_count + 1).where(URL.id == url_record.id).execute()

    return redirect(url_record.original_url, code=302)


@urls_bp.route("/<code>/stats", methods=["GET"])
def url_stats(code: str):
    """Get statistics for a shortened URL."""
    with timed_db_operation("select"):
        url_record = URL.select().where(URL.short_code == code).first()

    if not url_record:
        raise NotFoundError("Short URL not found")

    return jsonify(
        {
            "short_code": url_record.short_code,
            "original_url": url_record.original_url,
            "created_at": url_record.created_at.isoformat(),
            "expires_at": (
                url_record.expires_at.isoformat() if url_record.expires_at else None
            ),
            "is_active": url_record.is_active,
            "click_count": url_record.click_count,
        }
    )
