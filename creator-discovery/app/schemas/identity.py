from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.enums import IdentityAction


class IdentityResolveRequest(BaseModel):
    account_id: Optional[str] = None
    platform: Optional[str] = None
    handle: Optional[str] = None
    display_name: Optional[str] = None
    bio_text: Optional[str] = None
    profile_url: Optional[str] = None
    external_links: Optional[str] = None
    location_text: Optional[str] = None


class IdentityMatch(BaseModel):
    creator_id: str
    canonical_name: str
    confidence: float
    signals: List[str] = Field(default_factory=list)


class IdentityResolveResponse(BaseModel):
    recommended_action: IdentityAction
    confidence: float
    matches: List[IdentityMatch] = Field(default_factory=list)
    creator_id: Optional[str] = None
    reasoning: str = ""
