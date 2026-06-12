"""Backfill YouTube caption niche enrichment for existing YouTube accounts."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlmodel import Session, select

from app.db.session import engine
from app.models.account import Account
from app.models.enums import Platform
from app.services.classification.classifier import classify_account
from app.services.enrichment.youtube_captions import enrich_youtube_captions
from app.utils.fts import sync_account_fts


async def main() -> None:
    from app.core.config import get_settings

    settings = get_settings()
    if not settings.youtube_api_key:
        print("Note: YOUTUBE_API_KEY not set — using RSS + stored channel IDs only.")

    with Session(engine) as session:
        accounts = list(
            session.exec(
                select(Account).where(
                    Account.is_active == True,  # noqa: E712
                    Account.platform == Platform.YOUTUBE,
                )
            ).all()
        )
        enriched = 0
        for account in accounts:
            if await enrich_youtube_captions(account):
                await classify_account(session, account, force=True)
                sync_account_fts(session, account)
                session.add(account)
                enriched += 1
                print(f"  enriched: {account.handle} -> niche={account.niche}")
        session.commit()
        print(f"YouTube caption backfill: {enriched}/{len(accounts)} accounts enriched")


if __name__ == "__main__":
    asyncio.run(main())
