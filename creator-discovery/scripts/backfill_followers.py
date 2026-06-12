"""Backfill follower counts from bios and web search enrichment."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlmodel import Session, select

from app.db.session import engine
from app.models.account import Account
from app.services.enrichment.follower_enrichment import enrich_accounts_followers
from app.utils.followers import parse_follower_count


async def main() -> None:
    refresh_stale = "--refresh-stale" in sys.argv
    with Session(engine) as session:
        accounts = list(session.exec(select(Account).where(Account.is_active == True)).all())  # noqa: E712

        bio_updated = 0
        for account in accounts:
            if account.follower_count and not refresh_stale:
                continue
            count = parse_follower_count(account.bio_text, account.display_name)
            if count and (not account.follower_count or count > account.follower_count):
                account.follower_count = count
                bio_updated += 1

        print(f"Parsed {bio_updated} counts from existing bios")
        targets = sum(
            1
            for a in accounts
            if not a.follower_count
            or (refresh_stale and (a.follower_count < 1_000 or "source=rightfluencer" in (a.external_links or "")))
        )
        print(f"Enriching {targets} accounts via web search (refresh_stale={refresh_stale})...")

        search_updated = await enrich_accounts_followers(
            accounts,
            only_missing=not refresh_stale,
            refresh_stale=refresh_stale,
        )
        with_counts = sum(1 for a in accounts if a.follower_count)
        session.commit()

    print(f"Enriched {search_updated} accounts with follower counts from web search")
    print(f"Total with counts: {with_counts}/{len(accounts)}")


if __name__ == "__main__":
    asyncio.run(main())
