from typing import Optional

from app.models.account import Account
from app.services.providers.base import DiscoveredAccount
from app.utils.followers import parse_follower_count


def resolve_follower_count(
    discovered: DiscoveredAccount,
    existing: Optional[Account] = None,
) -> Optional[int]:
    """Pick the best follower/subscriber count from discovery data."""
    from_bio = parse_follower_count(
        discovered.bio_text,
        discovered.display_name,
    )
    candidates = [c for c in (discovered.follower_count, from_bio) if c]
    best = max(candidates) if candidates else None
    if existing and existing.follower_count:
        if best is None:
            return existing.follower_count
        return max(existing.follower_count, best)
    return best


def apply_follower_count(account: Account, discovered: DiscoveredAccount) -> None:
    count = resolve_follower_count(discovered, account)
    if count is not None:
        account.follower_count = count
