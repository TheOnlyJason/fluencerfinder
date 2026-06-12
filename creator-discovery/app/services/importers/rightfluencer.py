"""Import influencers from archived RightFluencer MongoDB BSON dumps."""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import bson
from sqlmodel import Session, select

from app.models.account import Account
from app.models.creator import Creator
from app.models.enums import Platform
from app.utils.fts import sync_account_fts
from app.utils.handles import build_profile_url, normalize_handle, parse_profile_url
from app.utils.location import infer_location, sanitize_location

_CATEGORY_TO_NICHE = {
    "food": "food",
    "technology": "tech",
    "tech": "tech",
    "fashion": "fashion",
    "travel": "travel",
    "fitness": "fitness",
    "beauty": "beauty",
    "gaming": "gaming",
    "game": "gaming",
    "home": "lifestyle",
    "lifestyle": "lifestyle",
    "health": "fitness",
    "music": "music",
    "comedy": "comedy",
    "sports": "fitness",
    "business": "tech",
    "design": "fashion",
}


def read_bson_file(path: Path) -> List[Dict[str, Any]]:
    data = path.read_bytes()
    docs: List[Dict[str, Any]] = []
    offset = 0
    while offset < len(data):
        doc_len = int.from_bytes(data[offset : offset + 4], "little")
        docs.append(bson.decode(data[offset : offset + doc_len]))
        offset += doc_len
    return docs


def _parse_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        cleaned = re.sub(r"[^\d]", "", str(value))
        return int(cleaned) if cleaned else None
    except (TypeError, ValueError):
        return None


def _map_niche(category: Optional[str]) -> Optional[str]:
    if not category:
        return None
    key = category.strip().lower()
    return _CATEGORY_TO_NICHE.get(key, key if len(key) >= 3 else None)


def _build_location(combined: Dict[str, Any]) -> Optional[str]:
    tw_loc = (combined.get("tw_location") or "").strip()
    if tw_loc:
        loc = sanitize_location(infer_location(tw_loc) or tw_loc)
        if loc:
            return loc
    city = (combined.get("fb_city") or "").strip()
    state = (combined.get("fb_state") or "").strip()
    country = (combined.get("fb_country") or "").strip()
    parts = [p for p in (city, state, country) if p]
    if parts:
        loc = sanitize_location(infer_location(", ".join(parts)) or ", ".join(parts))
        if loc:
            return loc
    return None


def _youtube_handle(
    combined: Dict[str, Any],
    listing: Dict[str, Any],
) -> Tuple[Optional[str], Optional[str]]:
    from app.utils.youtube import is_youtube_channel_id

    channel_id = (combined.get("yt_channel_id") or "").strip()
    url = (combined.get("yt_url") or combined.get("youtube_url") or listing.get("youtube_url") or "").strip()

    handle: Optional[str] = None
    if url:
        _, parsed = parse_profile_url(url.split("\n")[0])
        if parsed and not is_youtube_channel_id(parsed):
            handle = parsed

    if not handle:
        tw = _x_handle(combined, listing)
        if tw:
            handle = tw

    if not handle:
        name = (listing.get("name") or combined.get("tw_name") or "").strip()
        if name:
            handle = normalize_handle(re.sub(r"[^a-zA-Z0-9._]", "", name))

    return handle, channel_id or None


def _instagram_handle(combined: Dict[str, Any], listing: Dict[str, Any]) -> Optional[str]:
    ig = (combined.get("ig_handle") or "").strip()
    if ig:
        return normalize_handle(ig)
    url = (listing.get("instagram_url") or "").strip()
    if url:
        _, handle = parse_profile_url(url.split("\n")[0])
        return handle
    return None


def _x_handle(combined: Dict[str, Any], listing: Dict[str, Any]) -> Optional[str]:
    tw = (combined.get("tw_handle") or listing.get("tw_handle") or "").strip()
    return normalize_handle(tw) if tw else None


def _external_links(
    listing: Dict[str, Any],
    combined: Dict[str, Any],
    youtube_channel_id: Optional[str],
) -> Optional[str]:
    parts = []
    if youtube_channel_id:
        parts.append(f"youtube_channel_id={youtube_channel_id}")
    for key in ("facebook_url", "youtube_url", "instagram_url", "twitter_url"):
        val = (listing.get(key) or combined.get(key) or "").strip().split("\n")[0]
        if val:
            parts.append(val)
    parts.append("source=rightfluencer")
    return "; ".join(parts) if parts else "source=rightfluencer"


def load_rightfluencer_records(data_dir: Path) -> List[Dict[str, Any]]:
    """Merge influencers_list + combined collections by Twitter handle."""
    listing = read_bson_file(data_dir / "influencers_list_collection.bson")
    combined_docs = read_bson_file(data_dir / "combined_collection.bson")
    combined_by_tw = {
        (d.get("tw_handle") or "").lower(): d
        for d in combined_docs
        if d.get("tw_handle")
    }

    records: List[Dict[str, Any]] = []
    for row in listing:
        tw_handle = (row.get("tw_handle") or "").lower()
        combined = combined_by_tw.get(tw_handle, {})
        records.append({"listing": row, "combined": combined})
    return records


def import_rightfluencer(
    session: Session,
    data_dir: Path,
    *,
    skip_existing: bool = True,
) -> Dict[str, int]:
    """Import RightFluencer MongoDB BSON dumps into accounts + creators."""
    stats = {
        "creators": 0,
        "accounts_created": 0,
        "accounts_updated": 0,
        "accounts_skipped": 0,
    }

    for record in load_rightfluencer_records(data_dir):
        listing = record["listing"]
        combined = record["combined"]
        name = (listing.get("name") or combined.get("tw_name") or combined.get("fb_name") or "").strip()
        if not name:
            continue

        category = listing.get("category") or combined.get("fb_category")
        niche = _map_niche(category)
        location = _build_location(combined)
        bio = (combined.get("tw_description") or combined.get("fb_about") or "").strip() or None
        yt_handle, yt_channel_id = _youtube_handle(combined, listing)
        if not yt_handle and listing.get("youtube_url"):
            _, yt_handle = parse_profile_url(str(listing["youtube_url"]).split("\n")[0])

        creator = session.exec(
            select(Creator).where(Creator.canonical_name == name)
        ).first()
        if not creator:
            creator = Creator(
                canonical_name=name,
                home_region=location,
                overall_topics=category,
                identity_confidence=0.9,
            )
            session.add(creator)
            session.commit()
            session.refresh(creator)
            stats["creators"] += 1

        platform_specs: List[Tuple[Platform, Optional[str], Optional[int]]] = [
            (Platform.X, _x_handle(combined, listing), _parse_int(combined.get("tw_followers_count"))),
            # Instagram counts in RightFluencer dumps are ~2017-era and often wrong — enrich later.
            (Platform.INSTAGRAM, _instagram_handle(combined, listing), None),
            (Platform.YOUTUBE, yt_handle, _parse_int(combined.get("yt_subscriber_count"))),
        ]

        for platform, handle, followers in platform_specs:
            if not handle:
                continue
            handle = normalize_handle(handle)
            existing = session.exec(
                select(Account).where(
                    Account.platform == platform,
                    Account.handle == handle,
                )
            ).first()

            if existing and skip_existing:
                stats["accounts_skipped"] += 1
                if not existing.creator_id:
                    existing.creator_id = creator.creator_id
                    session.add(existing)
                continue

            profile_url = build_profile_url(platform, handle, external_links=_external_links(listing, combined, yt_channel_id))
            if platform == Platform.YOUTUBE and yt_channel_id and "youtube.com" not in profile_url:
                profile_url = f"https://www.youtube.com/channel/{yt_channel_id}"

            account_data = {
                "display_name": name,
                "profile_url": profile_url,
                "bio_text": bio,
                "niche": niche or (existing.niche if existing else None),
                "location_text": location or (existing.location_text if existing else None),
                "follower_count": followers or (existing.follower_count if existing else None),
                "external_links": _external_links(listing, combined, yt_channel_id),
                "creator_id": creator.creator_id,
                "is_active": True,
                "last_seen_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }

            if existing:
                for key, val in account_data.items():
                    if val is not None:
                        setattr(existing, key, val)
                session.add(existing)
                sync_account_fts(session, existing)
                stats["accounts_updated"] += 1
            else:
                account = Account(platform=platform, handle=handle, **account_data)
                session.add(account)
                session.commit()
                session.refresh(account)
                sync_account_fts(session, account)
                stats["accounts_created"] += 1

    session.commit()
    return stats
