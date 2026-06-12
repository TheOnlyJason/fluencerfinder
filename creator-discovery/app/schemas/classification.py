from typing import List, Optional

from pydantic import BaseModel, Field


class ClassificationResult(BaseModel):
    channel_type: str = "unknown"
    primary_niche: str = "unknown"
    secondary_niches: List[str] = Field(default_factory=list)
    hobbies: List[str] = Field(default_factory=list)
    location: Optional[str] = None
    contact_email: Optional[str] = None
    language: Optional[str] = None
    classification_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    reasoning: str = ""


class IdentityLLMResult(BaseModel):
    same_creator_as: Optional[str] = None
    identity_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    reasoning: str = ""
