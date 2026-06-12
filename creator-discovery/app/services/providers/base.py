from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional

from app.models.enums import Platform


@dataclass
class DiscoveredAccount:
    platform: Platform
    handle: str
    display_name: Optional[str] = None
    profile_url: Optional[str] = None
    bio_text: Optional[str] = None
    location_text: Optional[str] = None
    external_links: Optional[str] = None
    follower_count: Optional[int] = None
    source: str = "unknown"


@dataclass
class DiscoveryResult:
    accounts: List[DiscoveredAccount] = field(default_factory=list)
    provider_name: str = ""
    query: str = ""


class DiscoveryProvider(ABC):
    name: str = "base"

    @abstractmethod
    async def discover(
        self,
        query: str,
        platforms: Optional[List[Platform]] = None,
        limit: int = 20,
    ) -> DiscoveryResult:
        ...
