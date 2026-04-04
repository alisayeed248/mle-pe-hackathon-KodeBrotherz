from datetime import datetime, timezone

from peewee import (AutoField, BooleanField, DateTimeField, IntegerField, TextField, CharField)

from app.database import BaseModel

def utc_now():
  return datetime.now(timezone.utc)

class URL(BaseModel):
  """Model for storing shortened URLs."""

  id = AutoField()
  original_url = TextField()
  short_code = CharField(max_length=10, unique=True, index=True)
  created_at = DateTimeField(default=utc_now)
  expires_at = DateTimeField(null=True)
  is_active = BooleanField(default=True)
  click_count = IntegerField(default=0)

  class Meta:
    table_name = "urls"
  
