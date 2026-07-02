"""Auth & abuse-guard behavior for the backend."""
import pytest
from fastapi import HTTPException

from app.core.auth import is_admin, require_admin, require_user
from app.core.config import Settings

AUTH_ON = dict(supabase_url="https://x.supabase.co", supabase_anon_key="anon", database_url="sqlite://")
AUTH_OFF = dict(supabase_url="", supabase_anon_key="", database_url="sqlite://")


def test_is_admin_allowlist():
    s = Settings(admin_emails="Me@Example.com, other@x.com", **AUTH_ON)
    assert is_admin("me@example.com", s) is True   # case-insensitive
    assert is_admin("stranger@x.com", s) is False
    assert is_admin(None, s) is False


@pytest.mark.asyncio
async def test_auth_disabled_is_noop():
    s = Settings(admin_emails="", **AUTH_OFF)
    user = await require_user(creds=None, settings=s)
    assert user["dev"] is True
    # admin also passes through when auth is disabled (local dev / tests)
    assert await require_admin(user=user, settings=s) is user


@pytest.mark.asyncio
async def test_require_user_needs_token_when_enabled():
    s = Settings(**AUTH_ON)
    with pytest.raises(HTTPException) as exc:
        await require_user(creds=None, settings=s)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_require_admin_rejects_non_admins_and_unconfigured():
    # allowlist empty -> nobody is admin (safe default), even a valid user
    s_empty = Settings(admin_emails="", **AUTH_ON)
    with pytest.raises(HTTPException) as exc:
        await require_admin(user={"email": "me@example.com"}, settings=s_empty)
    assert exc.value.status_code == 403

    # allowlisted email passes; a stranger is rejected
    s = Settings(admin_emails="me@example.com", **AUTH_ON)
    allowed = await require_admin(user={"email": "me@example.com"}, settings=s)
    assert allowed["email"] == "me@example.com"
    with pytest.raises(HTTPException) as exc:
        await require_admin(user={"email": "stranger@x.com"}, settings=s)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_classify_rejects_bulk_and_oversized(session):
    from app.api.routes.accounts import classify
    from app.schemas.account import AccountClassifyRequest

    admin = {"email": "me@example.com"}
    # empty account_ids must be rejected (no classify-all fan-out via the API)
    with pytest.raises(HTTPException) as exc:
        await classify(AccountClassifyRequest(account_ids=[]), session=session, _admin=admin)
    assert exc.value.status_code == 400

    # oversized batch rejected
    with pytest.raises(HTTPException) as exc:
        await classify(AccountClassifyRequest(account_ids=[str(i) for i in range(51)]), session=session, _admin=admin)
    assert exc.value.status_code == 400
