"""Event/Analytics routes."""
import json
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

from app.models.event import Event
from app.errors import NotFoundError, ValidationError
from app.logging_config import get_logger

events_bp = Blueprint("events", __name__, url_prefix="/events")
logger = get_logger("events")


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


@events_bp.route("", methods=["GET"])
def list_events():
    """List events with optional filtering."""
    url_id = request.args.get("url_id", type=int)
    user_id = request.args.get("user_id", type=int)
    event_type = request.args.get("event_type")

    query = Event.select().order_by(Event.id)

    if url_id is not None:
        query = query.where(Event.url_id == url_id)
    if user_id is not None:
        query = query.where(Event.user_id == user_id)
    if event_type is not None:
        query = query.where(Event.event_type == event_type)

    events = [event.to_dict() for event in query]
    return jsonify(events), 200


@events_bp.route("/<int:event_id>", methods=["GET"])
def get_event(event_id: int):
    """Get an event by ID."""
    event = Event.select().where(Event.id == event_id).first()
    if not event:
        raise NotFoundError("Event not found")
    return jsonify(event.to_dict()), 200


@events_bp.route("", methods=["POST"])
def create_event():
    """Create a new event."""
    data = validate_json_body()

    url_id = data.get("url_id")
    user_id = data.get("user_id")
    event_type = data.get("event_type")
    details = data.get("details")

    # Validate event_type (Deceitful Scroll - must be string)
    if not event_type:
        raise ValidationError("event_type is required")
    if not isinstance(event_type, str):
        raise ValidationError("event_type must be a string")

    # Validate optional fields types
    if url_id is not None and not isinstance(url_id, int):
        raise ValidationError("url_id must be an integer")
    if user_id is not None and not isinstance(user_id, int):
        raise ValidationError("user_id must be an integer")

    # Serialize details to JSON if it's a dict (Deceitful Scroll - validate details)
    details_str = None
    if details is not None:
        if isinstance(details, dict):
            details_str = json.dumps(details)
        elif isinstance(details, str):
            details_str = details
        else:
            raise ValidationError("details must be a string or object")

    event = Event.create(
        url_id=url_id,
        user_id=user_id,
        event_type=event_type,
        timestamp=utc_now(),
        details=details_str,
    )

    logger.info("Event created", extra={
        "component": "events",
        "event_id": event.id,
        "event_type": event_type
    })

    return jsonify(event.to_dict()), 201
