from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.core.deps import get_db
from app.models.creator import Creator
from app.schemas.account import AccountRead
from app.schemas.creator import CreatorListResponse, CreatorRead

router = APIRouter(prefix="/creators", tags=["creators"])


@router.get("", response_model=CreatorListResponse)
def list_creators(
    session: Session = Depends(get_db),
    q: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
):
    stmt = select(Creator)
    if q:
        pattern = f"%{q}%"
        from sqlalchemy import or_
        stmt = stmt.where(or_(
            Creator.canonical_name.ilike(pattern),
            Creator.home_region.ilike(pattern),
            Creator.overall_topics.ilike(pattern),
        ))
    total = len(session.exec(stmt).all())
    creators = session.exec(stmt.offset(offset).limit(limit)).all()
    result = []
    for c in creators:
        cr = CreatorRead.model_validate(c)
        cr.accounts = [AccountRead.model_validate(a) for a in c.accounts]
        result.append(cr)
    return CreatorListResponse(creators=result, total=total)


@router.get("/{creator_id}", response_model=CreatorRead)
def get_creator(creator_id: str, session: Session = Depends(get_db)):
    creator = session.get(Creator, creator_id)
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found")
    cr = CreatorRead.model_validate(creator)
    cr.accounts = [AccountRead.model_validate(a) for a in creator.accounts]
    return cr
