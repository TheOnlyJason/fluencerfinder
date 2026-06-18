"""Follower-count tiers.

A creator's tier is derived purely from follower/subscriber count, so it never
needs to be stored — it stays correct as counts change. Bands match the common
influencer tiering used across the catalog.
"""
from typing import List, Optional, Tuple

# (tier number, label, lower bound inclusive, upper bound exclusive or None)
TIER_BANDS: List[Tuple[int, str, int, Optional[int]]] = [
    (1, "Tier 1 (1M+)", 1_000_000, None),
    (2, "Tier 2 (500K–1M)", 500_000, 1_000_000),
    (3, "Tier 3 (200K–500K)", 200_000, 500_000),
    (4, "Tier 4 (100K–200K)", 100_000, 200_000),
    (5, "Tier 5 (<100K)", 0, 100_000),
]

_LABELS = {tier: label for tier, label, _low, _high in TIER_BANDS}


def follower_tier(count: Optional[int]) -> Optional[int]:
    """Return the tier number (1-5) for a follower count, or None if unknown."""
    if count is None or count < 0:
        return None
    for tier, _label, low, high in TIER_BANDS:
        if count >= low and (high is None or count < high):
            return tier
    return None


def tier_label(tier: Optional[int]) -> Optional[str]:
    return _LABELS.get(tier) if tier is not None else None


def tier_bounds(tier: int) -> Tuple[Optional[int], Optional[int]]:
    """Return (min_followers, max_followers) for a tier, for inclusive filters."""
    for t, _label, low, high in TIER_BANDS:
        if t == tier:
            return low, (high - 1 if high is not None else None)
    return None, None


def tier_midpoint(tier: int) -> Optional[int]:
    """A representative follower count for a tier (used when only a band is known)."""
    for t, _label, low, high in TIER_BANDS:
        if t == tier:
            if high is None:
                # Open-ended top tier: use a reasonable representative value.
                return low
            return (low + high) // 2
    return None
