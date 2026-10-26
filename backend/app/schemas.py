
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TattooSessionCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    artist_id: UUID
    client_name: str = Field(min_length=2, max_length=150)
    client_phone: str | None = Field(default=None, max_length=30)
    tattoo_description: str | None = Field(default=None, max_length=2000)
    tattooed_at: datetime
    follow_up_days: int = Field(default=30, ge=1, le=365)


class TattooSessionCreated(BaseModel):
    session_id: UUID
    client_id: UUID
    artist_id: UUID
    client_name: str
    tattooed_at: datetime
    follow_up_days: int
    access_url: str
    access_expires_at: datetime
    status: str = "created"

class TattooFollowUpAccess(BaseModel):
    session_id: UUID
    client_name: str
    artist_name: str
    tattoo_description: str | None
    tattooed_at: datetime
    follow_up_days: int
    access_expires_at: datetime
