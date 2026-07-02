"""LLM-based natural-language parsing of creator-search queries.

Turns free text like "nano fitness creators in Texas with high engagement" into
structured filters (topic, location, follower range, platforms) plus a clean
semantic query for embedding. Falls back to the regex parser when no API key is
configured or the call fails.
"""
import json
import logging
from typing import Optional

from app.core.config import get_settings
from app.models.enums import Platform
from app.utils.query_parse import ParsedDiscoveryQuery, parse_discovery_query

logger = logging.getLogger(__name__)

_VALID_PLATFORMS = {p.value for p in Platform}

_SYSTEM_PROMPT = """You parse influencer/creator search queries into structured JSON filters.

Return ONLY a JSON object with these keys:
- "topic": the niche/subject as a short lowercase phrase (e.g. "fitness", "sustainable fashion"), or null if none.
- "location": a city/region/country if mentioned (e.g. "Los Angeles", "Texas"), or null.
- "min_followers": integer lower bound on followers, or null.
- "max_followers": integer upper bound on followers, or null.
- "platforms": array of any explicitly requested platforms, each one of ["Instagram","TikTok","X","YouTube","Twitch"]; empty array if none.
- "semantic_query": a concise natural-language description of the kind of creator the user wants, suitable for semantic similarity search. Keep it focused on the content/persona, not the numeric filters.

Rules:
- Convert follower shorthand: "10k"=10000, "1m"=1000000, "100K-1M" => min 100000 max 1000000.
- Creator-size words: "nano"=<10k (max 10000), "micro"=10k-100k, "mid"/"mid-tier"=100k-500k, "macro"=500k-1m, "mega"/"celebrity"=1m+ (min 1000000).
- Tier words map to: tier1=1m+, tier2=500k-1m, tier3=200k-500k, tier4=100k-200k, tier5=<100k.
- "youtubers"=>YouTube, "tiktokers"=>TikTok, "instagrammers"=>Instagram, "streamers"=>Twitch.
- Never invent filters that aren't implied by the query. Use null/empty when unsure."""


def _coerce_int(value) -> Optional[int]:
    try:
        if value is None:
            return None
        return max(0, int(value))
    except (TypeError, ValueError):
        return None


async def llm_parse_query(raw_query: str) -> Optional[ParsedDiscoveryQuery]:
    settings = get_settings()
    if settings.use_mock_llm or not raw_query.strip():
        return None
    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)
        resp = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": raw_query.strip()},
            ],
            response_format={"type": "json_object"},
            temperature=0,
        )
        data = json.loads(resp.choices[0].message.content or "{}")
    except Exception as exc:  # noqa: BLE001
        logger.warning("LLM query parse failed (%s); using regex fallback", exc)
        return None

    topic = (data.get("topic") or "").strip()
    location = (data.get("location") or "").strip() or None
    min_followers = _coerce_int(data.get("min_followers"))
    max_followers = _coerce_int(data.get("max_followers"))

    platforms = [
        p for p in (data.get("platforms") or []) if isinstance(p, str) and p in _VALID_PLATFORMS
    ] or None

    semantic_query = (data.get("semantic_query") or "").strip() or None

    # Backfill anything the LLM missed using the deterministic regex parser, so we
    # never regress on queries the rule-based parser already handled well.
    regex = parse_discovery_query(raw_query)
    if not topic:
        topic = regex.topic
    if location is None:
        location = regex.location
    if min_followers is None:
        min_followers = regex.min_followers
    if max_followers is None:
        max_followers = regex.max_followers

    return ParsedDiscoveryQuery(
        raw_query=raw_query,
        topic=topic,
        location=location,
        min_followers=min_followers,
        max_followers=max_followers,
        platforms=platforms,
        semantic_query=semantic_query,
    )
