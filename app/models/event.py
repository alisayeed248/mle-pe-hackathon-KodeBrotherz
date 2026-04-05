from datetime import datetime, timezone
import json

from peewee import AutoField, CharField, DateTimeField, IntegerField, TextField

from app.database import BaseModel


def utc_now():
    return datetime.now(timezone.utc)


class Event(BaseModel):
    """Model for storing URL events/analytics."""

    id = AutoField()
    url_id = IntegerField(null=True, index=True)
    user_id = IntegerField(null=True, index=True)
    event_type = CharField(max_length=50)  # created, click, updated, etc.
    timestamp = DateTimeField(default=utc_now)
    details = TextField(null=True)  # JSON string for extra details

    class Meta:
        table_name = "events"

    def to_dict(self):
        details_parsed = None
        if self.details:
            try:
                details_parsed = json.loads(self.details)
            except (json.JSONDecodeError, TypeError):
                details_parsed = self.details

        return {
            "id": self.id,
            "url_id": self.url_id,
            "user_id": self.user_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "details": details_parsed,
        }
