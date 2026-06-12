from pathlib import Path
from typing import List, Optional

import pandas as pd

from app.models.enums import Platform
from app.services.providers.base import DiscoveredAccount, DiscoveryProvider, DiscoveryResult


class CsvDiscoveryProvider(DiscoveryProvider):
    """Search a CSV file for matching creators."""

    name = "csv"

    def __init__(self, csv_path: Path):
        self.csv_path = csv_path

    async def discover(
        self,
        query: str,
        platforms: Optional[List[Platform]] = None,
        limit: int = 20,
    ) -> DiscoveryResult:
        if not self.csv_path.exists():
            return DiscoveryResult(accounts=[], provider_name=self.name, query=query)

        df = pd.read_csv(self.csv_path)
        terms = query.lower().split()
        accounts: List[DiscoveredAccount] = []

        for _, row in df.iterrows():
            try:
                platform = Platform(str(row.get("platform", "")).strip())
            except ValueError:
                continue
            if platforms and platform not in platforms:
                continue

            searchable = " ".join(str(row.get(c, "")) for c in df.columns).lower()
            if not any(t in searchable for t in terms):
                continue

            accounts.append(DiscoveredAccount(
                platform=platform,
                handle=str(row.get("handle", "")).strip(),
                display_name=str(row.get("display_name", "")) if pd.notna(row.get("display_name")) else None,
                profile_url=str(row.get("profile_url", "")) if pd.notna(row.get("profile_url")) else None,
                bio_text=str(row.get("bio_text", "")) if pd.notna(row.get("bio_text")) else None,
                location_text=str(row.get("location_text", "")) if pd.notna(row.get("location_text")) else None,
                external_links=str(row.get("external_links", "")) if pd.notna(row.get("external_links")) else None,
                source=self.name,
            ))
            if len(accounts) >= limit:
                break

        return DiscoveryResult(accounts=accounts, provider_name=self.name, query=query)
