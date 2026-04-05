from datetime import datetime, timezone

from peewee import AutoField, CharField, DateTimeField

from app.database import BaseModel


def utc_now():
    return datetime.now(timezone.utc)


class User(BaseModel):
    """Model for storing users."""

    id = AutoField()
    username = CharField(max_length=100, unique=True)
    email = CharField(max_length=255, unique=True)
    created_at = DateTimeField(default=utc_now)

    class Meta:
        table_name = "users"

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
