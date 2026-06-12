from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from app.schemas.account import AccountRead


class CreatorRead(BaseModel):
    creator_id: str
    canonical_name: str
    primary_language: Optional[str] = None
    home_region: Optional[str] = None
    overall_topics: Optional[str] = None
    identity_confidence: float
    created_at: datetime
    updated_at: datetime
    accounts: List[AccountRead] = []

    model_config = {"from_attributes": True}


class CreatorListResponse(BaseModel):
    creators: List[CreatorRead]
    total: int
