from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.auth import search_guard
from app.core.deps import get_db
from app.schemas.search import SearchRequest, SearchResponse
from app.services.discovery.service import search_creators

router = APIRouter(tags=["search"])


@router.post("/search", response_model=SearchResponse)
async def search(
    request: SearchRequest,
    session: Session = Depends(get_db),
    _user: dict = Depends(search_guard),
):
    # Every search makes a billed LLM call; gated behind sign-in + rate limit.
    return await search_creators(session, request)
