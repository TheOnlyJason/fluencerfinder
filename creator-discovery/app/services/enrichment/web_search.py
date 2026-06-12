import asyncio
import logging
import re
from typing import List

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


async def search_web(query: str, max_results: int = 6) -> List[dict]:
    settings = get_settings()
    if settings.tavily_api_key:
        try:
            async with httpx.AsyncClient(timeout=25.0) as client:
                resp = await client.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": settings.tavily_api_key,
                        "query": query,
                        "search_depth": "basic",
                        "max_results": max_results,
                    },
                )
                resp.raise_for_status()
                return [
                    {
                        "title": r.get("title") or "",
                        "snippet": r.get("content") or "",
                    }
                    for r in resp.json().get("results", [])
                ]
        except Exception as exc:
            logger.warning("Tavily search failed: %s", exc)

    def _sync_ddg() -> List[dict]:
        try:
            try:
                from ddgs import DDGS
            except ImportError:
                from duckduckgo_search import DDGS

            with DDGS() as ddgs:
                raw = list(ddgs.text(query, max_results=max_results))
            return [
                {
                    "title": r.get("title") or "",
                    "snippet": r.get("body") or r.get("snippet") or "",
                }
                for r in raw
            ]
        except Exception as exc:
            logger.debug("DDG search failed for %r: %s", query, exc)
            return []

    return await asyncio.to_thread(_sync_ddg)


async def search_delay(seconds: float = 0.3) -> None:
    await asyncio.sleep(seconds)
