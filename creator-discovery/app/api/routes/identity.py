from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.auth import require_admin
from app.core.deps import get_db
from app.schemas.identity import IdentityResolveRequest, IdentityResolveResponse
from app.services.identity.resolver import resolve_identity

router = APIRouter(prefix="/identity", tags=["identity"])


@router.post("/resolve", response_model=IdentityResolveResponse)
async def resolve(
    request: IdentityResolveRequest,
    session: Session = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    return await resolve_identity(
        session,
        account_id=request.account_id,
        platform=request.platform,
        handle=request.handle,
        display_name=request.display_name,
        bio_text=request.bio_text,
        profile_url=request.profile_url,
        external_links=request.external_links,
        location_text=request.location_text,
    )
