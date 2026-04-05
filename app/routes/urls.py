import os
import json
from datetime import datetime, timezone

import redis
from flask import Blueprint, jsonify, redirect, request

from app.errors import ConflictError, GoneError, NotFoundError, ValidationError
from app.models.url import URL
from app.services import (
    generate_short_code,
    validate_custom_code,
    validate_url,
)
from app.db_instrumentation import timed_db_operation
from app.logging_config import get_logger

urls_bp = Blueprint("urls", __name__)
logger = get_logger("urls")

# Redis connection
redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    decode_responses=True,
)
CACHE_TTL = 300  # cache entries for 5 minutes


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
        with timed_db_operation("select"):
            exists = URL.select().where(URL.short_code == short_code).exists()
        if exists:
            raise ConflictError("Short code already exists")
    else:
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

    # Cache the new URL immediately
    cache_data = {
        "original_url": url_record.original_url,
        "is_active": url_record.is_active,
        "expires_at": url_record.expires_at.isoformat() if url_record.expires_at else None,
        "id": url_record.id,
    }
    redis_client.setex(f"url:{short_code}", CACHE_TTL, json.dumps(cache_data))

    short_url = f"{request.host_url}{short_code}"

    logger.info("URL shortened", extra={
        "component": "urls",
        "short_code": short_code,
    })

    return (
        jsonify({"short_code": short_code, "short_url": short_url}),
        201,
    )


@urls_bp.route("/<code>", methods=["GET"])
def redirect_url(code: str):
    """Redirect to the original URL."""
    # Check cache first
    cached = redis_client.get(f"url:{code}")
    if cached:
        data = json.loads(cached)
        logger.info("Cache hit", extra={"component": "cache", "short_code": code, "cache_hit": True})
        # Check if expired
        if data["expires_at"] and datetime.fromisoformat(data["expires_at"]) < datetime.now(timezone.utc):
            raise GoneError("Short URL has expired")
        # Check if active
        if not data["is_active"]:
            raise GoneError("Short URL is no longer active")
        # Increment click count in DB (async-ish, don't block redirect)
        with timed_db_operation("update"):
            URL.update(click_count=URL.click_count + 1).where(URL.id == data["id"]).execute()
        return redirect(data["original_url"], code=302)

    # Cache miss - hit the database
    logger.info("Cache miss", extra={"component": "cache", "short_code": code, "cache_hit": False})
    with timed_db_operation("select"):
        url_record = URL.select().where(URL.short_code == code).first()

    if not url_record:
        raise NotFoundError("Short URL not found")

    if url_record.expires_at and url_record.expires_at < datetime.now(timezone.utc):
        raise GoneError("Short URL has expired")

    if not url_record.is_active:
        raise GoneError("Short URL is no longer active")

    # Store in cache for next time
    cache_data = {
        "original_url": url_record.original_url,
        "is_active": url_record.is_active,
        "expires_at": url_record.expires_at.isoformat() if url_record.expires_at else None,
        "id": url_record.id,
    }
    redis_client.setex(f"url:{code}", CACHE_TTL, json.dumps(cache_data))

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
