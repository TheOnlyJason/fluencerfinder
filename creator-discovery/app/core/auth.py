"""Backend authentication & abuse guards.

Read-only catalog endpoints (GET /accounts, /creators, /health) stay public so
anyone can browse. Write/paid endpoints require a valid Supabase session token;
a subset (bulk data mutation, exports) additionally require the caller's email
to be in ADMIN_EMAILS — because anyone can self-sign-up, "logged in" alone must
not authorize operations that spend money or rewrite the production dataset.

Tokens are validated against Supabase's own ``/auth/v1/user`` endpoint (no JWT
secret to manage) and cached briefly to avoid a round-trip on every request.
When Supabase isn't configured (local SQLite dev / tests) auth is a no-op.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Deque, Dict, Optional, Tuple

import httpx
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import Settings, get_settings

_bearer = HTTPBearer(auto_error=False)

# token -> (user, expiry epoch). Short TTL keeps a stolen/expired token from
# lingering while avoiding a Supabase round-trip on every request.
_token_cache: Dict[str, Tuple[dict, float]] = {}
_CACHE_TTL = 60.0

# identity -> recent request timestamps, for the in-memory /search rate limiter.
_rate_hits: Dict[str, Deque[float]] = defaultdict(deque)


async def _validate_token(token: str, settings: Settings) -> Optional[dict]:
    now = time.time()
    cached = _token_cache.get(token)
    if cached and cached[1] > now:
        return cached[0]
    url = settings.supabase_url.rstrip("/") + "/auth/v1/user"
    headers = {"Authorization": f"Bearer {token}", "apikey": settings.supabase_anon_key}
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(url, headers=headers)
    except httpx.HTTPError:
        return None
    if resp.status_code != 200:
        return None
    user = resp.json()
    _token_cache[token] = (user, now + _CACHE_TTL)
    return user


async def require_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Require a valid Supabase session. No-op when auth is disabled (dev/tests)."""
    if not settings.auth_enabled:
        return {"id": "dev", "email": "dev@local", "dev": True}
    if creds is None or not creds.credentials:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sign in required")
    user = await _validate_token(creds.credentials, settings)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired session")
    return user


def is_admin(email: Optional[str], settings: Settings) -> bool:
    """Pure allowlist check (unit-testable)."""
    return bool(email) and email.lower() in settings.admin_email_list


async def require_admin(
    user: dict = Depends(require_user),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Require an allowlisted admin. No-op when auth is disabled (dev/tests)."""
    if not settings.auth_enabled:
        return user
    if not settings.admin_email_list:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Admin access is not configured. Set ADMIN_EMAILS to enable admin endpoints.",
        )
    if not is_admin(user.get("email"), settings):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin access required")
    return user


def _check_rate(key: str, max_calls: int, window_s: float = 60.0) -> None:
    now = time.time()
    hits = _rate_hits[key]
    while hits and hits[0] <= now - window_s:
        hits.popleft()
    if len(hits) >= max_calls:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Rate limit exceeded — slow down and try again in a moment.",
        )
    hits.append(now)


async def search_guard(
    request: Request,
    user: dict = Depends(require_user),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Require a signed-in user AND enforce a per-user/IP rate limit on /search."""
    if settings.auth_enabled:
        key = user.get("id") or (request.client.host if request.client else "anon")
        _check_rate(f"search:{key}", settings.search_rate_limit_per_min)
    return user
