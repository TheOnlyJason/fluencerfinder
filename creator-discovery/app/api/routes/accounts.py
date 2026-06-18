from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func, nulls_last, or_
from sqlmodel import Session, select

from app.core.deps import get_db
from app.models.account import Account
from app.models.creator import Creator
from app.models.enums import Platform
from app.schemas.account import (
    AccountClassifyRequest,
    AccountClassifyResponse,
    AccountFacetsResponse,
    AccountIngestRequest,
    AccountIngestResponse,
    AccountListResponse,
    AccountRead,
)
from app.services.classification.classifier import classify_account
from app.services.ingestion import ingest_accounts

router = APIRouter(prefix="/accounts", tags=["accounts"])


from app.utils.query_parse import expand_topic_terms


def _niche_filter(niche: str):
    """Match niche/topic including related terms (gamer matches gaming)."""
    clauses = []
    for term in expand_topic_terms(niche):
        pattern = f"%{term}%"
        clauses.append(
            or_(
                Account.niche.ilike(pattern),
                Account.channel_type.ilike(pattern),
                Account.hobbies.ilike(pattern),
                Account.secondary_niches.ilike(pattern),
                Account.bio_text.ilike(pattern),
                Account.handle.ilike(pattern),
                Account.display_name.ilike(pattern),
            )
        )
    return or_(*clauses) if clauses else None


def _apply_account_filters(
    stmt,
    *,
    platform: Optional[Platform] = None,
    niche: Optional[str] = None,
    location: Optional[str] = None,
    channel_type: Optional[str] = None,
    is_active: Optional[bool] = True,
    creator_id: Optional[str] = None,
    q: Optional[str] = None,
    min_followers: Optional[int] = None,
    max_followers: Optional[int] = None,
    tier: Optional[int] = None,
):
    if tier is not None:
        from app.utils.tiers import tier_bounds

        low, high = tier_bounds(tier)
        if low is not None and (min_followers is None or low > min_followers):
            min_followers = low
        if high is not None and (max_followers is None or high < max_followers):
            max_followers = high
    if platform:
        stmt = stmt.where(Account.platform == platform)
    if niche:
        niche_clause = _niche_filter(niche)
        if niche_clause is not None:
            stmt = stmt.where(niche_clause)
    if location:
        city = location.split(",")[0].strip()
        stmt = stmt.where(
            or_(
                Account.location_text.ilike(f"%{location}%"),
                Account.location_text.ilike(f"%{city}%"),
                Account.bio_text.ilike(f"%{city}%"),
            )
        )
    if channel_type:
        pattern = f"%{channel_type}%"
        stmt = stmt.where(
            or_(
                Account.channel_type.ilike(pattern),
                Account.niche.ilike(pattern),
            )
        )
    if is_active is not None:
        stmt = stmt.where(Account.is_active == is_active)
    if creator_id:
        stmt = stmt.where(Account.creator_id == creator_id)
    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(
            or_(
                Account.handle.ilike(pattern),
                Account.display_name.ilike(pattern),
                Account.bio_text.ilike(pattern),
                Account.niche.ilike(pattern),
                Account.location_text.ilike(pattern),
                Account.contact_email.ilike(pattern),
                Account.channel_type.ilike(pattern),
                Account.hobbies.ilike(pattern),
                Account.secondary_niches.ilike(pattern),
            )
        )
    if min_followers is not None:
        stmt = stmt.where(Account.follower_count >= min_followers)
    if max_followers is not None:
        stmt = stmt.where(Account.follower_count <= max_followers)
    return stmt


def _to_account_reads(session: Session, accounts: List[Account]) -> List[AccountRead]:
    creator_ids = {a.creator_id for a in accounts if a.creator_id}
    creators_by_id = {}
    if creator_ids:
        creators = session.exec(select(Creator).where(Creator.creator_id.in_(creator_ids))).all()
        creators_by_id = {c.creator_id: c for c in creators}

    results = []
    for account in accounts:
        data = AccountRead.model_validate(account)
        creator = creators_by_id.get(account.creator_id) if account.creator_id else None
        if creator:
            data.creator_name = creator.canonical_name
        results.append(data)
    return results


@router.post("/ingest", response_model=AccountIngestResponse)
async def ingest(request: AccountIngestRequest, session: Session = Depends(get_db)):
    return await ingest_accounts(
        session,
        request.accounts,
        auto_classify=request.auto_classify,
        auto_resolve_identity=request.auto_resolve_identity,
    )


@router.post("/classify", response_model=AccountClassifyResponse)
async def classify(request: AccountClassifyRequest, session: Session = Depends(get_db)):
    classified = 0
    skipped = 0
    results = []

    account_ids = request.account_ids
    if not account_ids:
        accounts = session.exec(select(Account).where(Account.is_active == True)).all()  # noqa: E712
        account_ids = [a.account_id for a in accounts]

    for aid in account_ids:
        account = session.get(Account, aid)
        if not account:
            continue
        result, was_skipped = await classify_account(session, account, force=request.force)
        if was_skipped:
            skipped += 1
        else:
            classified += 1
        results.append({"account_id": aid, "skipped": was_skipped, "niche": result.primary_niche})

    return AccountClassifyResponse(classified=classified, skipped=skipped, results=results)


@router.get("/facets", response_model=AccountFacetsResponse)
def account_facets(session: Session = Depends(get_db)):
    accounts = session.exec(select(Account).where(Account.is_active == True)).all()  # noqa: E712

    def _unique(values: List[Optional[str]], *, skip_unknown: bool = False) -> List[str]:
        seen = set()
        out = []
        for value in values:
            if not value:
                continue
            if skip_unknown and value.lower() == "unknown":
                continue
            key = value.strip()
            if key and key not in seen:
                seen.add(key)
                out.append(key)
        return sorted(out, key=str.lower)

    return AccountFacetsResponse(
        platforms=_unique([a.platform.value for a in accounts]),
        niches=_unique([a.niche for a in accounts], skip_unknown=True),
        channel_types=_unique([a.channel_type for a in accounts], skip_unknown=True),
        locations=_unique([a.location_text for a in accounts])[:40],
        total=len(accounts),
    )


@router.get("", response_model=AccountListResponse)
def list_accounts(
    session: Session = Depends(get_db),
    platform: Optional[Platform] = None,
    niche: Optional[str] = None,
    location: Optional[str] = None,
    channel_type: Optional[str] = None,
    is_active: Optional[bool] = True,
    creator_id: Optional[str] = None,
    q: Optional[str] = None,
    min_followers: Optional[int] = Query(default=None, ge=0),
    max_followers: Optional[int] = Query(default=None, ge=0),
    tier: Optional[int] = Query(default=None, ge=1, le=5),
    sort: str = Query(default="followers", pattern="^(followers|new|recent|handle)$"),
    limit: int = Query(default=200, le=500),
    offset: int = Query(default=0, ge=0),
):
    base_filters = dict(
        platform=platform,
        niche=niche,
        location=location,
        channel_type=channel_type,
        is_active=is_active,
        creator_id=creator_id,
        q=q,
        min_followers=min_followers,
        max_followers=max_followers,
        tier=tier,
    )

    count_stmt = select(func.count()).select_from(Account)
    count_stmt = _apply_account_filters(count_stmt, **base_filters)
    total = session.exec(count_stmt).one()

    total_in_database = session.exec(
        select(func.count())
        .select_from(Account)
        .where(Account.is_active == True)  # noqa: E712
    ).one()

    stmt = select(Account)
    stmt = _apply_account_filters(stmt, **base_filters)
    if sort == "followers":
        stmt = stmt.order_by(
            nulls_last(desc(Account.follower_count)),
            desc(Account.updated_at),
        )
    elif sort == "handle":
        stmt = stmt.order_by(Account.handle.asc())
    else:
        # new / recent — when the account was first added to the database
        stmt = stmt.order_by(desc(Account.created_at))
    stmt = stmt.offset(offset).limit(limit)
    accounts = session.exec(stmt).all()

    return AccountListResponse(
        items=_to_account_reads(session, accounts),
        total=total,
        total_in_database=total_in_database,
    )
