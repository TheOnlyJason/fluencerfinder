"""Export influencers catalog to JSON for fast frontend loading."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from sqlmodel import Session, select

from app.models.account import Account
from app.models.creator import Creator
from app.schemas.account import AccountRead


def export_influencers_snapshot(session: Session) -> Dict[str, Any]:
    accounts = list(
        session.exec(select(Account).where(Account.is_active == True)).all()  # noqa: E712
    )
    creator_ids = {a.creator_id for a in accounts if a.creator_id}
    creators_by_id: Dict[str, Creator] = {}
    if creator_ids:
        creators = session.exec(select(Creator).where(Creator.creator_id.in_(creator_ids))).all()
        creators_by_id = {c.creator_id: c for c in creators}

    account_rows: List[Dict[str, Any]] = []
    for account in accounts:
        row = AccountRead.model_validate(account).model_dump(mode="json")
        creator = creators_by_id.get(account.creator_id) if account.creator_id else None
        if creator:
            row["creator_name"] = creator.canonical_name
        account_rows.append(row)

    creator_rows = [
        {
            "creator_id": c.creator_id,
            "canonical_name": c.canonical_name,
            "home_region": c.home_region,
            "overall_topics": c.overall_topics,
            "identity_confidence": c.identity_confidence,
        }
        for c in creators_by_id.values()
    ]

    return {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "total": len(account_rows),
        "creators": creator_rows,
        "accounts": account_rows,
    }


def write_influencers_json(session: Session, *paths: Path) -> Path:
    snapshot = export_influencers_snapshot(session)
    primary = paths[0]
    primary.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(snapshot, indent=2, ensure_ascii=False)
    primary.write_text(text, encoding="utf-8")
    for extra in paths[1:]:
        extra.parent.mkdir(parents=True, exist_ok=True)
        extra.write_text(text, encoding="utf-8")
    return primary
