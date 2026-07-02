from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlmodel import Session

from app.core.auth import require_admin
from app.core.deps import get_db
from app.services.csv_io import export_csv
from app.services.export.influencers_json import export_influencers_snapshot

router = APIRouter(prefix="/exports", tags=["exports"])


@router.get("/json")
def export_json_endpoint(
    session: Session = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    snapshot = export_influencers_snapshot(session)
    return JSONResponse(
        content=snapshot,
        headers={"Content-Disposition": "attachment; filename=influencers.json"},
    )


@router.get("/csv", response_class=PlainTextResponse)
def export_csv_endpoint(
    session: Session = Depends(get_db),
    platform: Optional[str] = None,
    niche: Optional[str] = None,
    _admin: dict = Depends(require_admin),
):
    csv_content = export_csv(session, platform=platform, niche=niche)
    return PlainTextResponse(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=creators_export.csv"},
    )
