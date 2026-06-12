from typing import List, Optional, Set

from sqlalchemy import or_, text
from sqlmodel import Session, select

from app.core.config import get_settings
from app.models.account import Account
from app.models.creator import Creator


def _escape_fts_query(query: str) -> str:
    """Prepare query for FTS5: quote terms and join with OR."""
    terms = [t.strip() for t in query.split() if t.strip()]
    if not terms:
        return ""
    return " OR ".join(f'"{t}"' for t in terms)


def search_accounts_fts(session: Session, query: str, limit: int = 50) -> List[str]:
    """Full-text search accounts, returns account_ids."""
    settings = get_settings()
    fts_query = _escape_fts_query(query)
    if not fts_query:
        return []

    if settings.is_sqlite:
        result = session.exec(
            text(
                """
                SELECT account_id FROM accounts_fts
                WHERE accounts_fts MATCH :q
                ORDER BY rank
                LIMIT :limit
                """
            ).bindparams(q=fts_query, limit=limit)
        )
        return [row[0] for row in result.all()]

    # Postgres: use ILIKE fallback for MVP (tsvector can be added via migration)
    terms = query.lower().split()
    stmt = select(Account.account_id)
    conditions = []
    for term in terms:
        pattern = f"%{term}%"
        conditions.append(
            or_(
                Account.handle.ilike(pattern),
                Account.display_name.ilike(pattern),
                Account.bio_text.ilike(pattern),
                Account.niche.ilike(pattern),
                Account.location_text.ilike(pattern),
                Account.hobbies.ilike(pattern),
                Account.channel_type.ilike(pattern),
            )
        )
    if conditions:
        from functools import reduce
        stmt = stmt.where(reduce(lambda a, b: a | b, conditions))
    stmt = stmt.limit(limit)
    return list(session.exec(stmt).all())


def search_creators_fts(session: Session, query: str, limit: int = 50) -> List[str]:
    settings = get_settings()
    fts_query = _escape_fts_query(query)
    if not fts_query:
        return []

    if settings.is_sqlite:
        result = session.exec(
            text(
                """
                SELECT creator_id FROM creators_fts
                WHERE creators_fts MATCH :q
                ORDER BY rank
                LIMIT :limit
                """
            ).bindparams(q=fts_query, limit=limit)
        )
        return [row[0] for row in result.all()]

    terms = query.lower().split()
    stmt = select(Creator.creator_id)
    conditions = []
    for term in terms:
        pattern = f"%{term}%"
        conditions.append(
            or_(
                Creator.canonical_name.ilike(pattern),
                Creator.home_region.ilike(pattern),
                Creator.overall_topics.ilike(pattern),
            )
        )
    if conditions:
        from functools import reduce
        stmt = stmt.where(reduce(lambda a, b: a | b, conditions))
    stmt = stmt.limit(limit)
    return list(session.exec(stmt).all())


def sync_account_fts(session: Session, account: Account) -> None:
    """Sync a single account to FTS index."""
    settings = get_settings()
    if not settings.is_sqlite:
        return
    session.exec(
        text("DELETE FROM accounts_fts WHERE account_id = :id").bindparams(id=account.account_id)
    )
    session.exec(
        text(
            """
            INSERT INTO accounts_fts (
                account_id, handle, display_name, bio_text, niche,
                secondary_niches, hobbies, location_text, channel_type
            ) VALUES (
                :account_id, :handle, :display_name, :bio_text, :niche,
                :secondary_niches, :hobbies, :location_text, :channel_type
            )
            """
        ).bindparams(
            account_id=account.account_id,
            handle=account.handle or "",
            display_name=account.display_name or "",
            bio_text=account.bio_text or "",
            niche=account.niche or "",
            secondary_niches=account.secondary_niches or "",
            hobbies=account.hobbies or "",
            location_text=account.location_text or "",
            channel_type=account.channel_type or "",
        )
    )


def sync_creator_fts(session: Session, creator: Creator) -> None:
    settings = get_settings()
    if not settings.is_sqlite:
        return
    session.exec(
        text("DELETE FROM creators_fts WHERE creator_id = :id").bindparams(id=creator.creator_id)
    )
    session.exec(
        text(
            """
            INSERT INTO creators_fts (creator_id, canonical_name, home_region, overall_topics)
            VALUES (:creator_id, :canonical_name, :home_region, :overall_topics)
            """
        ).bindparams(
            creator_id=creator.creator_id,
            canonical_name=creator.canonical_name or "",
            home_region=creator.home_region or "",
            overall_topics=creator.overall_topics or "",
        )
    )


def rebuild_all_fts(session: Session) -> None:
    """Rebuild FTS indexes from current data."""
    settings = get_settings()
    if not settings.is_sqlite:
        return
    session.exec(text("DELETE FROM accounts_fts"))
    session.exec(text("DELETE FROM creators_fts"))
    for account in session.exec(select(Account)).all():
        sync_account_fts(session, account)
    for creator in session.exec(select(Creator)).all():
        sync_creator_fts(session, creator)
    session.commit()
