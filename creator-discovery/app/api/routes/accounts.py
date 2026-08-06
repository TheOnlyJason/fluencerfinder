from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, desc, func, nulls_last, or_
from sqlmodel import Session, select

from app.core.auth import require_admin
from app.core.deps import get_db
from app.data.place_coords import geocode_place, searchable_places
from app.utils.geo_search import count_approximate_nearby, geo_search_accounts
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
    platforms: Optional[List[Platform]] = None,
    niches: Optional[List[str]] = None,
    locations: Optional[List[str]] = None,
    channel_type: Optional[str] = None,
    is_active: Optional[bool] = True,
    creator_id: Optional[str] = None,
    q: Optional[str] = None,
    min_followers: Optional[int] = None,
    max_followers: Optional[int] = None,
    tiers: Optional[List[int]] = None,
):
    if platforms:
        stmt = stmt.where(Account.platform.in_(platforms))
    if niches:
        # Match accounts in ANY of the selected niches (each expands to related terms).
        niche_clauses = [c for c in (_niche_filter(n) for n in niches) if c is not None]
        if niche_clauses:
            stmt = stmt.where(or_(*niche_clauses))
    if locations:
        loc_clauses = []
        for location in locations:
            city = location.split(",")[0].strip()
            loc_clauses.append(
                or_(
                    Account.location_text.ilike(f"%{location}%"),
                    Account.location_text.ilike(f"%{city}%"),
                    Account.bio_text.ilike(f"%{city}%"),
                )
            )
        if loc_clauses:
            stmt = stmt.where(or_(*loc_clauses))
    if tiers:
        from app.utils.tiers import tier_bounds

        tier_clauses = []
        for t in tiers:
            low, high = tier_bounds(t)
            conds = []
            if low is not None:
                conds.append(Account.follower_count >= low)
            if high is not None:
                conds.append(Account.follower_count <= high)
            if conds:
                tier_clauses.append(and_(*conds))
        if tier_clauses:
            stmt = stmt.where(or_(*tier_clauses))
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
        from app.core.config import get_settings

        pattern = f"%{q}%"
        q_clauses = [
            Account.handle.ilike(pattern),
            Account.display_name.ilike(pattern),
            Account.bio_text.ilike(pattern),
            Account.niche.ilike(pattern),
            Account.location_text.ilike(pattern),
            Account.channel_type.ilike(pattern),
            Account.hobbies.ilike(pattern),
            Account.secondary_niches.ilike(pattern),
        ]
        # Only match against contact emails when they're exposed, so a public
        # deployment can't probe whether an email exists via search.
        if get_settings().expose_contact_emails:
            q_clauses.append(Account.contact_email.ilike(pattern))
        stmt = stmt.where(or_(*q_clauses))
    if min_followers is not None:
        stmt = stmt.where(Account.follower_count >= min_followers)
    if max_followers is not None:
        stmt = stmt.where(Account.follower_count <= max_followers)
    return stmt


def _to_account_reads(
    session: Session,
    accounts: List[Account],
    distances: Optional[dict] = None,
) -> List[AccountRead]:
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
        if distances is not None:
            miles = distances.get(account.account_id)
            data.distance_miles = round(miles, 1) if miles is not None else None
        results.append(data)
    return results


def _resolve_center(near: str):
    """Resolve a 'near' value to (lat, lng, label). Accepts 'lat,lng' or a place name."""
    near = near.strip()
    if "," in near:
        parts = [p.strip() for p in near.split(",")]
        # Treat as coordinates only if both parts are numeric (else it's "City, ST").
        if len(parts) == 2:
            try:
                lat, lng = float(parts[0]), float(parts[1])
                if -90 <= lat <= 90 and -180 <= lng <= 180:
                    return lat, lng, near
            except ValueError:
                pass
    hit = geocode_place(near)
    if hit and hit.precision in ("city", "metro"):
        return hit.lat, hit.lng, near
    return None


@router.get("/geo/places")
def geo_places():
    """Place names usable as a radius-search center (for the frontend picker)."""
    return {"places": searchable_places()}


@router.post("/ingest", response_model=AccountIngestResponse)
async def ingest(
    request: AccountIngestRequest,
    session: Session = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    return await ingest_accounts(
        session,
        request.accounts,
        auto_classify=request.auto_classify,
        auto_resolve_identity=request.auto_resolve_identity,
    )


@router.post("/classify", response_model=AccountClassifyResponse)
async def classify(
    request: AccountClassifyRequest,
    session: Session = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    classified = 0
    skipped = 0
    results = []

    # Each classify is a billed LLM call. The API requires an explicit, bounded
    # list; classifying the entire catalog is an offline job (scripts/), not a
    # single request that could fan out to thousands of paid calls.
    account_ids = request.account_ids
    if not account_ids:
        raise HTTPException(
            status_code=400,
            detail="account_ids is required (bulk re-classification of all accounts is disabled via the API).",
        )
    if len(account_ids) > 50:
        raise HTTPException(status_code=400, detail="Too many account_ids (max 50 per request).")

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
    from app.utils.location import location_facet_counts

    # Only the columns facets need — hydrating full ORM rows (bios, embeddings)
    # for every account made this endpoint needlessly heavy.
    rows = session.exec(
        select(
            Account.platform,
            Account.niche,
            Account.channel_type,
            Account.location_text,
        ).where(Account.is_active == True)  # noqa: E712
    ).all()

    def _unique(values: List[Optional[str]], *, skip_unknown: bool = False) -> List[str]:
        seen = set()
        out = []
        for value in values:
            if not value:
                continue
            if skip_unknown and value.lower() == "unknown":
                continue
            key = value.strip()
            # Case-insensitive dedupe ("Fortnite" vs "fortnite")
            fold = key.lower()
            if key and fold not in seen:
                seen.add(fold)
                out.append(key)
        return sorted(out, key=str.lower)

    # Locations: canonicalized, junk-filtered, ranked by creator count so the
    # biggest markets (LA, NYC, ...) lead instead of an A–Z slice that cut off
    # before ever reaching them.
    locations = [name for name, _ in location_facet_counts(r[3] for r in rows)][:40]

    return AccountFacetsResponse(
        platforms=_unique([r[0].value for r in rows]),
        niches=_unique([r[1] for r in rows], skip_unknown=True),
        channel_types=_unique([r[2] for r in rows], skip_unknown=True),
        locations=locations,
        total=len(rows),
    )


@router.get("", response_model=AccountListResponse)
def list_accounts(
    session: Session = Depends(get_db),
    platforms: Optional[List[Platform]] = Query(default=None),
    niches: Optional[List[str]] = Query(default=None),
    locations: Optional[List[str]] = Query(default=None),
    channel_type: Optional[str] = None,
    is_active: Optional[bool] = True,
    creator_id: Optional[str] = None,
    q: Optional[str] = None,
    min_followers: Optional[int] = Query(default=None, ge=0),
    max_followers: Optional[int] = Query(default=None, ge=0),
    tiers: Optional[List[int]] = Query(default=None),
    near: Optional[str] = Query(default=None, description="Radius-search center: a place name or 'lat,lng'"),
    radius_miles: float = Query(default=25, ge=1, le=500),
    sort: str = Query(default="followers", pattern="^(followers|new|recent|handle|distance)$"),
    limit: int = Query(default=200, le=500),
    offset: int = Query(default=0, ge=0),
):
    base_filters = dict(
        platforms=platforms,
        niches=niches,
        locations=locations,
        channel_type=channel_type,
        is_active=is_active,
        creator_id=creator_id,
        q=q,
        min_followers=min_followers,
        max_followers=max_followers,
        tiers=tiers,
    )

    total_in_database = session.exec(
        select(func.count())
        .select_from(Account)
        .where(Account.is_active == True)  # noqa: E712
    ).one()

    # Radius ("near") search: resolve a center, find creators within radius (ranked
    # by distance), then apply the normal filters to that bounded set. The geo
    # result is small (<= a few hundred) so we page it in Python.
    if near:
        center = _resolve_center(near)
        if center is None:
            # Unknown/partial place (free-text input) is not an error — return an
            # empty result with near_resolved=None so the UI can say "not found"
            # instead of showing an "API is down" banner.
            return AccountListResponse(
                items=[], total=0, total_in_database=total_in_database, near_resolved=None
            )
        lat, lng, near_resolved = center
        geo_hits = geo_search_accounts(session, lat, lng, radius_miles, limit=500)
        distances = {aid: miles for aid, miles in geo_hits}
        approx = count_approximate_nearby(session, lat, lng, radius_miles)
        if not distances:
            return AccountListResponse(
                items=[], total=0, total_in_database=total_in_database,
                approximate_nearby=approx, near_resolved=near_resolved,
            )
        stmt = _apply_account_filters(select(Account), **base_filters)
        stmt = stmt.where(Account.account_id.in_(list(distances)))
        matched = session.exec(stmt).all()
        # Every sort ends on account_id so the paginated (offset/limit) result is
        # stable — critical here because all creators in one city share the same
        # centroid (distance ties are the norm, not the exception). Descending
        # sorts use a two-pass stable sort (account_id asc, then the key desc).
        matched.sort(key=lambda a: a.account_id)
        if sort == "handle":
            matched.sort(key=lambda a: a.handle.lower())
        elif sort == "followers":
            matched.sort(key=lambda a: a.follower_count or 0, reverse=True)
        elif sort in ("new", "recent"):
            matched.sort(key=lambda a: a.created_at, reverse=True)
        else:  # distance (default in near mode)
            matched.sort(key=lambda a: distances.get(a.account_id, 1e9))
        page = matched[offset : offset + limit]
        return AccountListResponse(
            items=_to_account_reads(session, page, distances=distances),
            total=len(matched),
            total_in_database=total_in_database,
            approximate_nearby=approx,
            near_resolved=near_resolved,
        )

    count_stmt = select(func.count()).select_from(Account)
    count_stmt = _apply_account_filters(count_stmt, **base_filters)
    total = session.exec(count_stmt).one()

    stmt = select(Account)
    stmt = _apply_account_filters(stmt, **base_filters)
    # Every branch ends in the unique account_id: without a total order, ties
    # (e.g. the same handle on two platforms) can be resolved differently by
    # consecutive offset/limit queries, duplicating or skipping rows across pages.
    if sort == "followers":
        stmt = stmt.order_by(
            nulls_last(desc(Account.follower_count)),
            desc(Account.updated_at),
            Account.account_id,
        )
    elif sort == "handle":
        stmt = stmt.order_by(Account.handle.asc(), Account.account_id)
    else:
        # new / recent — when the account was first added to the database
        stmt = stmt.order_by(desc(Account.created_at), Account.account_id)
    stmt = stmt.offset(offset).limit(limit)
    accounts = session.exec(stmt).all()

    return AccountListResponse(
        items=_to_account_reads(session, accounts),
        total=total,
        total_in_database=total_in_database,
    )
