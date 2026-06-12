from typing import List, Optional

from app.models.enums import Platform
from app.services.providers.base import DiscoveredAccount, DiscoveryProvider, DiscoveryResult
from app.utils.handles import build_profile_url, parse_profile_url, strip_handle


class ManualUrlProvider(DiscoveryProvider):
    """Ingest accounts from manually provided profile URLs."""

    name = "manual_url"

    def __init__(self, urls: List[str]):
        self.urls = urls

    async def discover(
        self,
        query: str,
        platforms: Optional[List[Platform]] = None,
        limit: int = 20,
    ) -> DiscoveryResult:
        accounts: List[DiscoveredAccount] = []
        for url in self.urls[:limit]:
            platform, handle = parse_profile_url(url)
            if not platform or not handle:
                continue
            if platforms and platform not in platforms:
                continue
            accounts.append(DiscoveredAccount(
                platform=platform,
                handle=handle,
                profile_url=url,
                source=self.name,
            ))
        return DiscoveryResult(accounts=accounts, provider_name=self.name, query=query)
