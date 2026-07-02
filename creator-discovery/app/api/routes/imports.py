from fastapi import APIRouter, Depends, File, UploadFile
from sqlmodel import Session

from app.core.auth import require_admin
from app.core.deps import get_db
from app.services.csv_io import import_csv

router = APIRouter(prefix="/imports", tags=["imports"])


@router.post("/csv")
async def import_csv_endpoint(
    session: Session = Depends(get_db),
    file: UploadFile = File(...),
    auto_classify: bool = True,
    auto_resolve_identity: bool = True,
    _admin: dict = Depends(require_admin),
):
    content = await file.read()
    return await import_csv(
        session, content,
        auto_classify=auto_classify,
        auto_resolve_identity=auto_resolve_identity,
    )
