from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from uuid import uuid4

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.account import Account


class Creator(SQLModel, table=True):
    __tablename__ = "creators"

    creator_id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    canonical_name: str = Field(index=True)
    primary_language: Optional[str] = Field(default=None, index=True)
    home_region: Optional[str] = Field(default=None, index=True)
    overall_topics: Optional[str] = Field(default=None)
    identity_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    accounts: List["Account"] = Relationship(back_populates="creator")
