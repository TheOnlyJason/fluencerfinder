import json
from datetime import datetime
from typing import List, Optional
from urllib.parse import urlparse

from sqlmodel import Session, select

from app.core.config import get_settings
from app.models.account import Account
from app.models.creator import Creator
from app.models.enums import IdentityAction
from app.prompts.identity import IDENTITY_SYSTEM_PROMPT, IDENTITY_USER_TEMPLATE
from app.schemas.identity import IdentityMatch, IdentityResolveResponse
from app.utils.handles import (
    display_name_similarity,
    handle_similarity,
    normalize_handle,
)
from app.utils.fts import sync_creator_fts


def _extract_domains(links: Optional[str]) -> set[str]:
    if not links:
        return set()
    domains = set()
    for part in links.replace(",", " ").split():
        part = part.strip()
        if not part:
            continue
        try:
            if "://" not in part:
                part = "https://" + part
            host = urlparse(part).netloc.lower()
            if host.startswith("www."):
                host = host[4:]
            if host:
                domains.add(host)
        except Exception:
            continue
    return domains


def _deterministic_score(new: dict, existing_account: Account, creator: Creator) -> tuple[float, list[str]]:
    signals: list[str] = []
    score = 0.0

    h_sim = handle_similarity(new.get("handle", ""), existing_account.handle)
    if h_sim >= 0.95:
        score += 0.45
        signals.append("exact_handle_match")
    elif h_sim >= 0.6:
        score += 0.3
        signals.append("similar_handle")
    elif h_sim >= 0.5:
        score += 0.2
        signals.append("related_handle")

    d_sim = display_name_similarity(new.get("display_name"), existing_account.display_name)
    if d_sim >= 0.9:
        score += 0.2
        signals.append("display_name_match")
    elif d_sim >= 0.6:
        score += 0.1
        signals.append("similar_display_name")

    new_bio = (new.get("bio_text") or "").lower()
    exist_bio = (existing_account.bio_text or "").lower()
    if new_bio and exist_bio and len(new_bio) > 20 and new_bio[:50] == exist_bio[:50]:
        score += 0.15
        signals.append("bio_similarity")

    new_loc = (new.get("location_text") or "").lower()
    exist_loc = (existing_account.location_text or "").lower()
    if new_loc and exist_loc and (new_loc in exist_loc or exist_loc in new_loc):
        score += 0.1
        signals.append("shared_location")

    new_domains = _extract_domains(new.get("external_links"))
    exist_domains = _extract_domains(existing_account.external_links)
    shared = new_domains & exist_domains
    if shared:
        score += 0.2
        signals.append(f"shared_link_domain:{','.join(shared)}")

    if creator.canonical_name and new.get("display_name"):
        cn_sim = display_name_similarity(creator.canonical_name, new.get("display_name"))
        if cn_sim >= 0.7:
            score += 0.1
            signals.append("creator_name_match")

    return min(score, 1.0), signals


async def _llm_identity_boost(
    new: dict, candidates: List[tuple[Creator, float, list[str]]]
) -> Optional[tuple[str, float, str]]:
    settings = get_settings()
    if settings.use_mock_llm or not candidates:
        return None

    try:
        from openai import AsyncOpenAI

        candidates_json = json.dumps([
            {
                "creator_id": c.creator_id,
                "canonical_name": c.canonical_name,
                "home_region": c.home_region,
                "existing_score": score,
                "signals": signals,
            }
            for c, score, signals in candidates[:5]
        ], indent=2)

        # Bounded — the SDK default is 600s; a hung identity call must not stall
        # the caller (the offline /identity/resolve admin path).
        client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            timeout=20.0,
            max_retries=1,
        )
        user_msg = IDENTITY_USER_TEMPLATE.format(
            platform=new.get("platform", ""),
            handle=new.get("handle", ""),
            display_name=new.get("display_name", ""),
            bio_text=new.get("bio_text", ""),
            location_text=new.get("location_text", ""),
            external_links=new.get("external_links", ""),
            candidates_json=candidates_json,
        )
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": IDENTITY_SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        raw = json.loads(response.choices[0].message.content or "{}")
        cid = raw.get("same_creator_as")
        conf = float(raw.get("identity_confidence", 0))
        reasoning = raw.get("reasoning", "")
        if cid and conf > 0:
            return cid, conf, reasoning
    except Exception:
        pass
    return None


async def resolve_identity(
    session: Session,
    *,
    account_id: Optional[str] = None,
    platform: Optional[str] = None,
    handle: Optional[str] = None,
    display_name: Optional[str] = None,
    bio_text: Optional[str] = None,
    profile_url: Optional[str] = None,
    external_links: Optional[str] = None,
    location_text: Optional[str] = None,
) -> IdentityResolveResponse:
    if account_id:
        account = session.get(Account, account_id)
        if not account:
            return IdentityResolveResponse(
                recommended_action=IdentityAction.CREATE,
                confidence=0.0,
                reasoning="Account not found.",
            )
        new = {
            "platform": account.platform.value,
            "handle": account.handle,
            "display_name": account.display_name,
            "bio_text": account.bio_text,
            "external_links": account.external_links,
            "location_text": account.location_text,
        }
    else:
        new = {
            "platform": platform or "",
            "handle": normalize_handle(handle or ""),
            "display_name": display_name,
            "bio_text": bio_text,
            "external_links": external_links,
            "location_text": location_text,
        }

    if not new["handle"]:
        return IdentityResolveResponse(
            recommended_action=IdentityAction.REVIEW,
            confidence=0.0,
            reasoning="Handle is required for identity resolution.",
        )

    # Check exact platform+handle match
    from app.models.enums import Platform
    try:
        plat = Platform(new["platform"]) if new["platform"] else None
    except ValueError:
        plat = None

    if plat:
        existing = session.exec(
            select(Account).where(Account.platform == plat, Account.handle == new["handle"])
        ).first()
        if existing and existing.creator_id:
            creator = session.get(Creator, existing.creator_id)
            return IdentityResolveResponse(
                recommended_action=IdentityAction.ATTACH,
                confidence=0.99,
                creator_id=existing.creator_id,
                matches=[IdentityMatch(
                    creator_id=existing.creator_id,
                    canonical_name=creator.canonical_name if creator else "Unknown",
                    confidence=0.99,
                    signals=["exact_platform_handle"],
                )],
                reasoning="Exact platform+handle match found in database.",
            )

    # Score against all creators
    creators = session.exec(select(Creator)).all()
    matches: List[IdentityMatch] = []
    candidate_tuples: List[tuple[Creator, float, list[str]]] = []

    for creator in creators:
        accounts = session.exec(
            select(Account).where(Account.creator_id == creator.creator_id)
        ).all()
        best_score = 0.0
        best_signals: list[str] = []
        for acc in accounts:
            score, signals = _deterministic_score(new, acc, creator)
            if score > best_score:
                best_score = score
                best_signals = signals
        if best_score > 0.3:
            matches.append(IdentityMatch(
                creator_id=creator.creator_id,
                canonical_name=creator.canonical_name,
                confidence=best_score,
                signals=best_signals,
            ))
            candidate_tuples.append((creator, best_score, best_signals))

    matches.sort(key=lambda m: m.confidence, reverse=True)

    llm_result = await _llm_identity_boost(new, candidate_tuples)
    if llm_result:
        cid, llm_conf, llm_reason = llm_result
        for m in matches:
            if m.creator_id == cid:
                m.confidence = max(m.confidence, llm_conf)
                m.signals.append("llm_identity_match")
        reasoning = llm_reason
    else:
        reasoning = "Deterministic identity scoring."

    if matches and matches[0].confidence >= 0.75:
        return IdentityResolveResponse(
            recommended_action=IdentityAction.ATTACH,
            confidence=matches[0].confidence,
            creator_id=matches[0].creator_id,
            matches=matches[:5],
            reasoning=reasoning,
        )
    if matches and matches[0].confidence >= 0.5:
        return IdentityResolveResponse(
            recommended_action=IdentityAction.REVIEW,
            confidence=matches[0].confidence,
            creator_id=matches[0].creator_id,
            matches=matches[:5],
            reasoning=reasoning + " Moderate confidence — review recommended.",
        )

    return IdentityResolveResponse(
        recommended_action=IdentityAction.CREATE,
        confidence=0.0,
        matches=matches[:5],
        reasoning="No strong match found. Create new creator.",
    )


def attach_or_create_creator(
    session: Session,
    account: Account,
    resolution: IdentityResolveResponse,
) -> Creator:
    """Apply identity resolution to link account to creator."""
    if resolution.recommended_action == IdentityAction.ATTACH and resolution.creator_id:
        creator = session.get(Creator, resolution.creator_id)
        if creator:
            account.creator_id = creator.creator_id
            creator.identity_confidence = max(creator.identity_confidence, resolution.confidence)
            creator.updated_at = datetime.utcnow()
            session.add(account)
            session.add(creator)
            session.commit()
            return creator

    name = account.display_name or account.handle
    creator = Creator(
        canonical_name=name,
        primary_language=account.language,
        home_region=account.location_text,
        overall_topics=account.niche,
        identity_confidence=resolution.confidence or 0.5,
    )
    session.add(creator)
    session.commit()
    session.refresh(creator)

    account.creator_id = creator.creator_id
    session.add(account)
    session.commit()

    sync_creator_fts(session, creator)
    return creator
