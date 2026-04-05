from datetime import datetime, timezone

from peewee import (AutoField, BooleanField, DateTimeField, IntegerField, TextField, CharField, ForeignKeyField)

from app.database import BaseModel


def utc_now():
    return datetime.now(timezone.utc)


class URL(BaseModel):
    """Model for storing shortened URLs."""

    id = AutoField()
    user_id = IntegerField(null=True, index=True)  # Foreign key to users table
    original_url = TextField()
    short_code = CharField(max_length=10, unique=True, index=True)
    title = CharField(max_length=255, null=True)
    created_at = DateTimeField(default=utc_now)
    updated_at = DateTimeField(default=utc_now)
    expires_at = DateTimeField(null=True)
    is_active = BooleanField(default=True)
    click_count = IntegerField(default=0)

    class Meta:
        table_name = "urls"

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "short_code": self.short_code,
            "original_url": self.original_url,
            "title": self.title,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "click_count": self.click_count,
        }
  
