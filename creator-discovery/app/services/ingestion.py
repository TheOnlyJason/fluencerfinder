from datetime import datetime
from typing import List

from sqlmodel import Session, select

from app.models.account import Account
from app.models.enums import Platform
from app.schemas.account import AccountBase, AccountIngestResponse
from app.services.classification.classifier import classify_account
from app.services.discovery.service import ingest_discovered_account
from app.services.identity.resolver import attach_or_create_creator, resolve_identity
from app.services.providers.base import DiscoveredAccount
from app.utils.handles import build_profile_url, normalize_handle, parse_profile_url


async def ingest_accounts(
    session: Session,
    accounts: List[AccountBase],
    *,
    auto_classify: bool = True,
    auto_resolve_identity: bool = True,
) -> AccountIngestResponse:
    ingested = 0
    updated = 0
    account_ids: List[str] = []

    for item in accounts:
        handle = normalize_handle(item.handle)
        platform = item.platform

        profile_url = item.profile_url
        if profile_url and not handle:
            plat, h = parse_profile_url(profile_url)
            if plat:
                platform = plat
            if h:
                handle = h

        if not handle:
            continue

        if not profile_url:
            profile_url = build_profile_url(platform, handle)

        discovered = DiscoveredAccount(
            platform=platform,
            handle=handle,
            display_name=item.display_name,
            profile_url=profile_url,
            bio_text=item.bio_text,
            external_links=item.external_links,
            source="ingest",
        )

        existing = session.exec(
            select(Account).where(Account.platform == platform, Account.handle == handle)
        ).first()

        account = await ingest_discovered_account(
            session,
            discovered,
            auto_classify=False,
            auto_resolve=False,
        )

        if existing:
            updated += 1
        else:
            ingested += 1

        if auto_resolve_identity:
            resolution = await resolve_identity(session, account_id=account.account_id)
            attach_or_create_creator(session, account, resolution)

        if auto_classify:
            await classify_account(session, account)

        account_ids.append(account.account_id)

    return AccountIngestResponse(
        ingested=ingested,
        updated=updated,
        account_ids=account_ids,
    )
