from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from sqlmodel import Field, Relationship, SQLModel

from app.models.enums import Platform

if TYPE_CHECKING:
    from app.models.creator import Creator


class Account(SQLModel, table=True):
    __tablename__ = "accounts"

    account_id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    creator_id: Optional[str] = Field(default=None, foreign_key="creators.creator_id", index=True)
    platform: Platform = Field(index=True)
    handle: str = Field(index=True)
    display_name: Optional[str] = Field(default=None)
    profile_url: Optional[str] = Field(default=None)
    bio_text: Optional[str] = Field(default=None)
    channel_type: Optional[str] = Field(default=None, index=True)
    niche: Optional[str] = Field(default=None, index=True)
    secondary_niches: Optional[str] = Field(default=None)
    hobbies: Optional[str] = Field(default=None)
    location_text: Optional[str] = Field(default=None, index=True)
    # Geocoded from location_text (city-centroid precision). geo_precision:
    # "city" (usable for radius search) | "region" | "country" (too coarse).
    latitude: Optional[float] = Field(default=None)
    longitude: Optional[float] = Field(default=None)
    geo_precision: Optional[str] = Field(default=None)
    geocoded_at: Optional[datetime] = Field(default=None)
    contact_email: Optional[str] = Field(default=None, index=True)
    language: Optional[str] = Field(default=None)
    external_links: Optional[str] = Field(default=None)
    follower_count: Optional[int] = Field(default=None, index=True)
    classification_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    is_active: bool = Field(default=True, index=True)
    last_seen_at: datetime = Field(default_factory=datetime.utcnow)
    classification_hash: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    creator: Optional["Creator"] = Relationship(back_populates="accounts")
