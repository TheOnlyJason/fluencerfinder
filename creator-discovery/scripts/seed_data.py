#!/usr/bin/env python3
"""Seed the database with sample creator data."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlmodel import Session

from app.db.session import create_db_and_tables, engine
from app.services.csv_io import import_csv
from app.utils.fts import rebuild_all_fts


async def main():
    create_db_and_tables()
    csv_path = Path(__file__).resolve().parents[1] / "data" / "sample_creators.csv"
    with open(csv_path, "rb") as f:
        content = f.read()
    with Session(engine) as session:
        result = await import_csv(session, content)
        rebuild_all_fts(session)
        print(f"Seeded {result['ingested']} new accounts, updated {result['updated']}")


if __name__ == "__main__":
    asyncio.run(main())
