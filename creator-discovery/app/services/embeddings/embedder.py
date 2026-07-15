"""Text embeddings for semantic creator search.

Uses OpenAI's `text-embedding-3-small` (1536 dims) by default. All search code
must degrade gracefully when no API key is configured (returns None), so callers
can fall back to keyword/FTS search.
"""
import logging
from typing import List, Optional

from app.core.config import get_settings

logger = logging.getLogger(__name__)

EMBED_MODEL = "text-embedding-3-small"
EMBED_DIM = 1536
# OpenAI allows large batches; keep them modest to stay well under token limits.
MAX_BATCH = 256


def build_profile_text(account) -> str:
    """Compose the text we embed to represent a creator profile."""
    platform = getattr(account.platform, "value", account.platform)
    parts = [
        account.display_name,
        f"@{account.handle}" if account.handle else None,
        platform,
        account.niche,
        account.secondary_niches,
        account.channel_type,
        account.hobbies,
        account.location_text,
        account.bio_text,
    ]
    text = " | ".join(str(p).strip() for p in parts if p and str(p).strip())
    return text or (account.handle or "creator")


def embeddings_enabled() -> bool:
    return bool(get_settings().openai_api_key)


def embed_texts_sync(texts: List[str]) -> Optional[List[List[float]]]:
    """Synchronous embedding (used by the backfill script)."""
    settings = get_settings()
    if not settings.openai_api_key or not texts:
        return None
    from openai import OpenAI

    # Offline/backfill path (scripts) — more generous than the request path.
    client = OpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        timeout=30.0,
        max_retries=2,
    )
    out: List[List[float]] = []
    for i in range(0, len(texts), MAX_BATCH):
        batch = texts[i : i + MAX_BATCH]
        resp = client.embeddings.create(model=EMBED_MODEL, input=batch)
        out.extend(d.embedding for d in resp.data)
    return out


async def embed_texts(texts: List[str]) -> Optional[List[List[float]]]:
    settings = get_settings()
    if not settings.openai_api_key or not texts:
        return None
    try:
        from openai import AsyncOpenAI

        # Short timeout: called inside the search request path; on failure the
        # caller degrades to keyword-only search instead of hanging.
        client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            timeout=8.0,
            max_retries=1,
        )
        resp = await client.embeddings.create(model=EMBED_MODEL, input=texts)
        return [d.embedding for d in resp.data]
    except Exception as exc:  # noqa: BLE001
        logger.warning("Embedding request failed: %s", exc)
        return None


async def embed_text(text: str) -> Optional[List[float]]:
    if not text or not text.strip():
        return None
    out = await embed_texts([text])
    return out[0] if out else None
