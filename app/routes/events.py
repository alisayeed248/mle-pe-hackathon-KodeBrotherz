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
    data = request.get_json(silent=True) or {}

    url_id = data.get("url_id")
    user_id = data.get("user_id")
    event_type = data.get("event_type")
    details = data.get("details")

    if not event_type:
        raise ValidationError("event_type is required")

    # Serialize details to JSON if it's a dict
    details_str = None
    if details:
        if isinstance(details, dict):
            details_str = json.dumps(details)
        else:
            details_str = str(details)

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
