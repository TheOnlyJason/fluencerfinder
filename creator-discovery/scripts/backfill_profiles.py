"""Backfill location and contact email for existing accounts."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlmodel import Session, select

from app.db.session import engine
from app.models.account import Account
from app.services.enrichment.profile_enrichment import (
    apply_profile_enrichment,
    enrich_account_profile,
)
from app.utils.contact import parse_email, parse_location
from app.utils.location import infer_location, is_valid_location, sanitize_location


async def main() -> None:
    with Session(engine) as session:
        accounts = list(session.exec(select(Account).where(Account.is_active == True)).all())  # noqa: E712

        cleared = 0
        for account in accounts:
            if account.location_text and not is_valid_location(account.location_text):
                account.location_text = None
                cleared += 1
        if cleared:
            print(f"Cleared {cleared} invalid locations")

        parsed = 0
        for account in accounts:
            if not account.location_text:
                loc = infer_location(
                    account.bio_text,
                    account.display_name,
                    account.external_links,
                    handle=account.handle,
                )
                loc = sanitize_location(loc)
                if loc:
                    account.location_text = loc
                    parsed += 1
            if not account.contact_email:
                email = parse_email(account.bio_text, account.external_links, account.display_name)
                if email:
                    account.contact_email = email
                    parsed += 1

        print(f"Parsed {parsed} fields from existing bios")

        need_enrich = [
            a for a in accounts if not a.location_text or not a.contact_email
        ]
        print(f"Enriching {len(need_enrich)} accounts via web search (no LLM)...")

        enriched = 0
        for account in need_enrich:
            profile = await enrich_account_profile(account, quick=False)
            if apply_profile_enrichment(account, profile):
                enriched += 1

        with_location = sum(1 for a in accounts if a.location_text)
        with_email = sum(1 for a in accounts if a.contact_email)
        session.commit()

    print(f"Enriched {enriched} accounts")
    print(f"With location: {with_location}/{len(accounts)}")
    print(f"With email: {with_email}/{len(accounts)}")


if __name__ == "__main__":
    asyncio.run(main())
