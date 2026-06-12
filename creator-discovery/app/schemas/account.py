from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, computed_field

from app.models.enums import Platform
from app.utils.youtube import format_display_handle


class AccountBase(BaseModel):
    platform: Platform
    handle: str
    display_name: Optional[str] = None
    profile_url: Optional[str] = None
    bio_text: Optional[str] = None
    external_links: Optional[str] = None


class AccountIngestRequest(BaseModel):
    accounts: List[AccountBase]
    auto_classify: bool = True
    auto_resolve_identity: bool = True


class AccountIngestResponse(BaseModel):
    ingested: int
    updated: int
    account_ids: List[str]


class AccountClassifyRequest(BaseModel):
    account_ids: List[str] = Field(default_factory=list)
    force: bool = False


class AccountClassifyResponse(BaseModel):
    classified: int
    skipped: int
    results: List[dict]


class AccountRead(BaseModel):
    account_id: str
    creator_id: Optional[str] = None
    creator_name: Optional[str] = None
    platform: Platform
    handle: str
    display_name: Optional[str] = None
    profile_url: Optional[str] = None
    bio_text: Optional[str] = None
    channel_type: Optional[str] = None
    niche: Optional[str] = None
    secondary_niches: Optional[str] = None
    hobbies: Optional[str] = None
    location_text: Optional[str] = None
    contact_email: Optional[str] = None
    language: Optional[str] = None
    external_links: Optional[str] = None
    follower_count: Optional[int] = None
    classification_confidence: Optional[float] = None
    is_active: bool = True
    last_seen_at: datetime
    created_at: datetime
    updated_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def display_handle(self) -> str:
        return format_display_handle(self.platform, self.handle, self.display_name)

    model_config = {"from_attributes": True}


class AccountListResponse(BaseModel):
    items: List[AccountRead]
    total: int
    total_in_database: int


class AccountFacetsResponse(BaseModel):
    platforms: List[str]
    niches: List[str]
    channel_types: List[str]
    locations: List[str]
    total: int


class AccountFilterParams(BaseModel):
    platform: Optional[Platform] = None
    niche: Optional[str] = None
    location: Optional[str] = None
    channel_type: Optional[str] = None
    is_active: Optional[bool] = None
    creator_id: Optional[str] = None
    q: Optional[str] = None
    min_followers: Optional[int] = Field(default=None, ge=0)
    max_followers: Optional[int] = Field(default=None, ge=0)
    limit: int = 50
    offset: int = 0
