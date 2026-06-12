from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.enums import Platform
from app.schemas.account import AccountRead


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Discovery intent e.g. 'gamer in Los Angeles with 10K-100K followers'")
    platforms: Optional[List[Platform]] = None
    niche: Optional[str] = None
    location: Optional[str] = None
    min_followers: Optional[int] = Field(default=None, ge=0)
    max_followers: Optional[int] = Field(default=None, ge=0)
    limit: int = Field(default=50, ge=1, le=150)
    use_external_providers: bool = True


class ParsedSearchCriteria(BaseModel):
    topic: Optional[str] = None
    location: Optional[str] = None
    min_followers: Optional[int] = None
    max_followers: Optional[int] = None


class SearchResultItem(BaseModel):
    account: AccountRead
    creator_name: Optional[str] = None
    source: str = "database"


class SearchResponse(BaseModel):
    query: str
    results: List[SearchResultItem]
    total: int
    sources: dict
    from_database: int
    from_providers: int
    matched_in_database: int = 0
    parsed: Optional[ParsedSearchCriteria] = None
