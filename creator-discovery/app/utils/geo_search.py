"""Radius ("within N miles") search over geocoded creators.

Postgres-only, using the built-in cube + earthdistance extensions. A GiST index
on ll_to_earth(lat,lng) makes the bounding-box prefilter (earth_box @>) fast; an
exact earth_distance recheck removes the box corners. On SQLite this is a no-op
and callers fall back to non-geo search.
"""
import logging
from typing import List, Optional, Sequence, Tuple

from sqlalchemy import text
from sqlmodel import Session

from app.core.config import get_settings

logger = logging.getLogger(__name__)

METERS_PER_MILE = 1609.344
# Only these precisions are specific enough to place on a radius (see place_coords).
RADIUS_PRECISIONS: tuple[str, ...] = ("city", "metro")


def geo_supported() -> bool:
    return not get_settings().is_sqlite


def ensure_geo_schema(session: Session) -> bool:
    """Enable cube+earthdistance and index geocoded coordinates. Postgres-only."""
    if not geo_supported():
        return False
    session.exec(text("SET lock_timeout = '5s'"))
    session.exec(text("SET statement_timeout = '60s'"))
    session.exec(text("CREATE EXTENSION IF NOT EXISTS cube"))
    session.exec(text("CREATE EXTENSION IF NOT EXISTS earthdistance"))
    # GiST index on the earth point for fast earth_box containment.
    session.exec(
        text(
            "CREATE INDEX IF NOT EXISTS accounts_earth_gist "
            "ON accounts USING gist (ll_to_earth(latitude, longitude)) "
            "WHERE latitude IS NOT NULL AND longitude IS NOT NULL"
        )
    )
    session.commit()
    return True


def geo_search_accounts(
    session: Session,
    lat: float,
    lng: float,
    radius_miles: float,
    *,
    precisions: Sequence[str] = RADIUS_PRECISIONS,
    limit: int = 500,
) -> List[Tuple[str, float]]:
    """Return [(account_id, distance_miles)] within radius, nearest first.

    Empty list on SQLite or if the earthdistance extension isn't available
    (caller then behaves as if no geo filter was applied).
    """
    if not geo_supported():
        return []
    radius_m = radius_miles * METERS_PER_MILE
    prec = tuple(precisions)
    try:
        rows = session.exec(
            text(
                """
                SELECT account_id,
                       earth_distance(ll_to_earth(latitude, longitude),
                                      ll_to_earth(:lat, :lng)) / :mpm AS miles
                FROM accounts
                WHERE latitude IS NOT NULL AND longitude IS NOT NULL
                  AND is_active = true
                  AND geo_precision = ANY(:precisions)
                  AND earth_box(ll_to_earth(:lat, :lng), :radius_m)
                      @> ll_to_earth(latitude, longitude)
                  AND earth_distance(ll_to_earth(latitude, longitude),
                                     ll_to_earth(:lat, :lng)) <= :radius_m
                ORDER BY miles ASC
                LIMIT :limit
                """
            ).bindparams(
                lat=lat, lng=lng, mpm=METERS_PER_MILE,
                radius_m=radius_m, precisions=list(prec), limit=limit,
            )
        ).all()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Geo search unavailable (%s); ignoring radius filter", exc)
        return []
    return [(r[0], float(r[1])) for r in rows]


def count_approximate_nearby(
    session: Session, lat: float, lng: float, radius_miles: float
) -> int:
    """Count region-precision creators whose coarse centroid falls in the radius.

    Region-level locations (e.g. "Southern California") are too coarse to place
    exactly, so they're excluded from the precise radius result — but the UI can
    surface them as "N more have approximate locations". Distance-scoped (not a
    global count) so it actually reflects the searched area. Country precision is
    excluded — a country centroid near a city is meaningless.
    """
    if not geo_supported():
        return 0
    radius_m = radius_miles * METERS_PER_MILE
    try:
        row = session.exec(
            text(
                """
                SELECT count(*) FROM accounts
                WHERE is_active = true
                  AND latitude IS NOT NULL AND longitude IS NOT NULL
                  AND geo_precision = 'region'
                  AND earth_box(ll_to_earth(:lat, :lng), :radius_m)
                      @> ll_to_earth(latitude, longitude)
                  AND earth_distance(ll_to_earth(latitude, longitude),
                                     ll_to_earth(:lat, :lng)) <= :radius_m
                """
            ).bindparams(lat=lat, lng=lng, radius_m=radius_m)
        ).one()
        return int(row[0])
    except Exception:  # noqa: BLE001
        return 0
