import io
from typing import List, Optional

import pandas as pd
from sqlmodel import Session, select

from app.models.account import Account
from app.models.creator import Creator
from app.models.enums import Platform
from app.schemas.account import AccountBase
from app.services.ingestion import ingest_accounts


CSV_COLUMNS = [
    "platform", "handle", "display_name", "profile_url", "bio_text",
    "location_text", "external_links", "channel_type", "niche",
    "secondary_niches", "hobbies", "language", "classification_confidence",
    "follower_count", "contact_email", "creator_id", "canonical_name",
]


async def import_csv(
    session: Session,
    file_content: bytes,
    auto_classify: bool = True,
    auto_resolve_identity: bool = True,
) -> dict:
    df = pd.read_csv(io.BytesIO(file_content))
    accounts: List[AccountBase] = []
    for _, row in df.iterrows():
        try:
            platform = Platform(str(row["platform"]).strip())
        except (ValueError, KeyError):
            continue
        handle = str(row.get("handle", "")).strip()
        if not handle:
            continue
        accounts.append(AccountBase(
            platform=platform,
            handle=handle,
            display_name=str(row["display_name"]) if pd.notna(row.get("display_name")) else None,
            profile_url=str(row["profile_url"]) if pd.notna(row.get("profile_url")) else None,
            bio_text=str(row["bio_text"]) if pd.notna(row.get("bio_text")) else None,
            external_links=str(row["external_links"]) if pd.notna(row.get("external_links")) else None,
        ))
    result = await ingest_accounts(
        session, accounts,
        auto_classify=auto_classify,
        auto_resolve_identity=auto_resolve_identity,
    )
    return {
        "rows_processed": len(df),
        "ingested": result.ingested,
        "updated": result.updated,
        "account_ids": result.account_ids,
    }


def export_csv(session: Session, platform: Optional[str] = None, niche: Optional[str] = None) -> str:
    stmt = select(Account).where(Account.is_active == True)  # noqa: E712
    if platform:
        try:
            stmt = stmt.where(Account.platform == Platform(platform))
        except ValueError:
            pass
    if niche:
        stmt = stmt.where(Account.niche.ilike(f"%{niche}%"))

    accounts = session.exec(stmt).all()
    rows = []
    for acc in accounts:
        creator_name = None
        if acc.creator_id:
            creator = session.get(Creator, acc.creator_id)
            creator_name = creator.canonical_name if creator else None
        rows.append({
            "platform": acc.platform.value,
            "handle": acc.handle,
            "display_name": acc.display_name,
            "profile_url": acc.profile_url,
            "bio_text": acc.bio_text,
            "location_text": acc.location_text,
            "external_links": acc.external_links,
            "channel_type": acc.channel_type,
            "niche": acc.niche,
            "secondary_niches": acc.secondary_niches,
            "hobbies": acc.hobbies,
            "language": acc.language,
            "classification_confidence": acc.classification_confidence,
            "follower_count": acc.follower_count,
            "contact_email": acc.contact_email,
            "creator_id": acc.creator_id,
            "canonical_name": creator_name,
        })
    df = pd.DataFrame(rows, columns=CSV_COLUMNS)
    return df.to_csv(index=False)
