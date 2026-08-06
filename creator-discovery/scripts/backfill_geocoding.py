"""Geocode accounts.location_text → latitude/longitude/geo_precision.

Uses the bundled gazetteer (app/data/place_coords.py) — offline, $0, deterministic.
Ensures the geo schema (cube+earthdistance+GiST index) first. Dry-run by default.

    python scripts/backfill_geocoding.py            # report only
    python scripts/backfill_geocoding.py --apply    # write coordinates
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from collections import Counter

from sqlmodel import Session, select

from app.data.place_coords import geocode_place
from app.db.session import _migrate_schema, engine
from app.models.account import Account
from app.utils.geo_search import ensure_geo_schema


def main() -> None:
    apply = "--apply" in sys.argv[1:]

    # Ensure the geo columns exist before we read/write them (idempotent nullable
    # ADD COLUMN IF NOT EXISTS). Safe even in dry-run — it adds empty columns,
    # not data. The GiST index/extensions only matter once we write, so gate that.
    _migrate_schema()

    with Session(engine) as session:
        if apply:
            ensure_geo_schema(session)

        accounts = session.exec(
            select(Account).where(Account.is_active == True)  # noqa: E712
        ).all()

        prec_counts: Counter[str] = Counter()
        geocoded = 0
        no_location = 0
        unresolved: Counter[str] = Counter()

        for acc in accounts:
            if not acc.location_text:
                no_location += 1
                continue
            hit = geocode_place(acc.location_text)
            if not hit:
                unresolved[acc.location_text.strip()] += 1
                continue
            geocoded += 1
            prec_counts[hit.precision] += 1
            if apply:
                acc.latitude = hit.lat
                acc.longitude = hit.lng
                acc.geo_precision = hit.precision
                acc.geocoded_at = datetime.now(timezone.utc)
                session.add(acc)

        if apply:
            session.commit()

    total = len(accounts)
    radius_ready = prec_counts.get("city", 0) + prec_counts.get("metro", 0)
    print(f"{'APPLIED' if apply else 'DRY RUN (use --apply to write)'}")
    print(f"  total active accounts:   {total}")
    print(f"  geocoded:                {geocoded}  ({geocoded/total:.0%})")
    print(f"    radius-ready (city+metro): {radius_ready}  ({radius_ready/total:.0%})")
    print(f"    by precision:          {dict(prec_counts)}")
    print(f"  no location_text:        {no_location}")
    print(f"  unresolved locations:    {sum(unresolved.values())} ({len(unresolved)} distinct)")
    for loc, n in unresolved.most_common(15):
        print(f"      {n:3d}  {loc!r}")


if __name__ == "__main__":
    main()
