from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, computed_field, model_validator

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
    # Distance from a radius-search center, set only on "near" searches.
    distance_miles: Optional[float] = None
    is_active: bool = True
    last_seen_at: datetime
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def _redact_contact_email(self) -> "AccountRead":
        """Strip scraped contact emails unless explicitly exposed.

        This is the single chokepoint for every account payload (list, search,
        JSON export), so a public deployment never leaks contact emails. Enable
        via EXPOSE_CONTACT_EMAILS=true on a private/trusted instance.
        """
        from app.core.config import get_settings

        if self.contact_email is not None and not get_settings().expose_contact_emails:
            self.contact_email = None
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    def display_handle(self) -> str:
        return format_display_handle(self.platform, self.handle, self.display_name)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def tier(self) -> Optional[int]:
        from app.utils.tiers import follower_tier

        return follower_tier(self.follower_count)

    model_config = {"from_attributes": True}


class AccountListResponse(BaseModel):
    items: List[AccountRead]
    total: int
    total_in_database: int
    # Radius search only: creators with a location too coarse to place precisely
    # (e.g. state-level) that the UI can offer to include.
    approximate_nearby: int = 0
    # Radius search only: the resolved center place name (echoed back for the UI).
    near_resolved: Optional[str] = None


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
