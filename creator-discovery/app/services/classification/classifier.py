import hashlib
import json
from datetime import datetime
from typing import Optional

from sqlmodel import Session

from app.core.config import get_settings
from app.models.account import Account
from app.prompts.classification import CLASSIFICATION_SYSTEM_PROMPT, CLASSIFICATION_USER_TEMPLATE
from app.schemas.classification import ClassificationResult
from app.utils.contact import parse_email
from app.utils.followers import parse_follower_count
from app.utils.location import infer_location, is_valid_location, sanitize_location
from app.utils.fts import sync_account_fts


def profile_content_hash(account: Account) -> str:
    """Hash profile fields to detect material changes."""
    content = "|".join([
        account.platform.value if account.platform else "",
        account.handle or "",
        account.display_name or "",
        account.bio_text or "",
        account.location_text or "",
        account.external_links or "",
    ])
    return hashlib.sha256(content.encode()).hexdigest()


def _mock_classify(account: Account) -> ClassificationResult:
    """Rule-based fallback when no API key is set."""
    bio = (account.bio_text or "").lower()
    display = (account.display_name or "").lower()
    combined = f"{bio} {display}"

    niche = "lifestyle"
    channel_type = "personal"
    hobbies: list[str] = []
    confidence = 0.55
    location = infer_location(
        account.bio_text,
        account.display_name,
        account.external_links,
        account.location_text,
        handle=account.handle,
    )

    keywords = {
        "fitness": (["fitness", "gym", "workout", "trainer", "crossfit"], "fitness"),
        "gaming": (["gaming", "gamer", "twitch", "esports", "anime"], "gaming"),
        "fashion": (["fashion", "style", "ootd", "outfit"], "fashion"),
        "beauty": (["beauty", "makeup", "skincare", "cosmetic"], "beauty"),
        "food": (["food", "recipe", "chef", "cooking", "matcha"], "food"),
        "tech": (["tech", "developer", "coding", "ai"], "tech"),
    }
    for key, (terms, ctype) in keywords.items():
        if any(t in combined for t in terms):
            niche = key
            channel_type = ctype
            confidence = 0.65
            break

    contact_email = parse_email(account.bio_text, account.external_links, account.display_name)

    if "yoga" in combined:
        hobbies.append("yoga")
    if "travel" in combined:
        hobbies.append("travel")

    return ClassificationResult(
        channel_type=channel_type,
        primary_niche=niche,
        secondary_niches=[],
        hobbies=hobbies,
        location=location,
        contact_email=contact_email,
        language=account.language or "en",
        classification_confidence=confidence,
        reasoning="Mock classification based on keyword matching (no API key set).",
    )


async def _llm_classify(account: Account) -> ClassificationResult:
    settings = get_settings()
    if settings.use_mock_llm:
        return _mock_classify(account)

    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)
        user_msg = CLASSIFICATION_USER_TEMPLATE.format(
            platform=account.platform.value,
            handle=account.handle,
            display_name=account.display_name or "",
            bio_text=account.bio_text or "",
            location_text=account.location_text or "",
            external_links=account.external_links or "",
        )
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": CLASSIFICATION_SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        raw = json.loads(response.choices[0].message.content or "{}")
        return ClassificationResult(
            channel_type=raw.get("channel_type", "unknown"),
            primary_niche=raw.get("primary_niche", "unknown"),
            secondary_niches=raw.get("secondary_niches", []),
            hobbies=raw.get("hobbies", []),
            location=raw.get("location"),
            contact_email=parse_email(raw.get("contact_email") or "") or None,
            language=raw.get("language"),
            classification_confidence=float(raw.get("classification_confidence", 0.5)),
            reasoning=raw.get("reasoning", ""),
        )
    except Exception:
        return _mock_classify(account)


def apply_classification(account: Account, result: ClassificationResult) -> None:
    account.channel_type = result.channel_type
    account.niche = result.primary_niche
    account.secondary_niches = ", ".join(result.secondary_niches) if result.secondary_niches else None
    account.hobbies = ", ".join(result.hobbies) if result.hobbies else None
    if result.location:
        account.location_text = sanitize_location(result.location) or account.location_text
    if not account.location_text:
        inferred = sanitize_location(
            infer_location(
                account.bio_text,
                account.display_name,
                account.external_links,
                handle=account.handle,
            )
        )
        if inferred:
            account.location_text = inferred
    if result.contact_email:
        account.contact_email = result.contact_email
    elif not account.contact_email:
        found = parse_email(account.bio_text, account.external_links, account.display_name)
        if found:
            account.contact_email = found
    if result.language:
        account.language = result.language
    account.classification_confidence = result.classification_confidence
    account.classification_hash = profile_content_hash(account)
    parsed_followers = parse_follower_count(account.bio_text, account.display_name)
    if parsed_followers and (not account.follower_count or parsed_followers > account.follower_count):
        account.follower_count = parsed_followers
    account.updated_at = datetime.utcnow()


async def classify_account(
    session: Session, account: Account, force: bool = False
) -> tuple[ClassificationResult, bool]:
    """Classify account. Returns (result, was_skipped)."""
    current_hash = profile_content_hash(account)
    if (
        not force
        and account.classification_hash
        and account.classification_hash == current_hash
        and account.niche
    ):
        return ClassificationResult(
            channel_type=account.channel_type or "unknown",
            primary_niche=account.niche or "unknown",
            secondary_niches=(account.secondary_niches or "").split(", ") if account.secondary_niches else [],
            hobbies=(account.hobbies or "").split(", ") if account.hobbies else [],
            location=account.location_text,
            contact_email=account.contact_email,
            language=account.language,
            classification_confidence=account.classification_confidence or 0.5,
            reasoning="Reused prior classification (profile unchanged).",
        ), True

    result = await _llm_classify(account)
    apply_classification(account, result)
    sync_account_fts(session, account)
    session.add(account)
    session.commit()
    session.refresh(account)
    return result, False
