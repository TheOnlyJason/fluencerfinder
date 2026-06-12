"""Tests for RightFluencer BSON import."""
from pathlib import Path

import pytest
from sqlmodel import Session, select

from app.models.account import Account
from app.models.creator import Creator
from app.models.enums import Platform
from app.services.importers.rightfluencer import (
    load_rightfluencer_records,
    read_bson_file,
)

DATA_DIR = (
    Path(__file__).resolve().parents[2]
    / "rightfluencer"
    / "mongo-data"
    / "influencers_db"
)


@pytest.mark.skipif(not DATA_DIR.exists(), reason="RightFluencer BSON dumps not present")
def test_read_bson_files():
    listing = read_bson_file(DATA_DIR / "influencers_list_collection.bson")
    combined = read_bson_file(DATA_DIR / "combined_collection.bson")
    assert len(listing) >= 80
    assert len(combined) >= 80


@pytest.mark.skipif(not DATA_DIR.exists(), reason="RightFluencer BSON dumps not present")
def test_merge_records():
    records = load_rightfluencer_records(DATA_DIR)
    assert len(records) >= 80
    assert "listing" in records[0]
    assert "combined" in records[0]


@pytest.mark.skipif(not DATA_DIR.exists(), reason="RightFluencer BSON dumps not present")
def test_import_rightfluencer(session: Session):
    from app.services.importers.rightfluencer import import_rightfluencer

    stats = import_rightfluencer(session, DATA_DIR, skip_existing=False)
    assert stats["accounts_created"] + stats["accounts_updated"] > 0

    creators = list(session.exec(select(Creator)).all())
    accounts = list(session.exec(select(Account)).all())
    assert len(creators) >= 50
    assert len(accounts) >= 100

    youtube = [a for a in accounts if a.platform == Platform.YOUTUBE]
    assert len(youtube) >= 30
