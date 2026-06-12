"""Fix YouTube accounts stored with channel IDs as handles."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlmodel import Session, select

from app.db.session import engine
from app.models.account import Account
from app.models.enums import Platform
from app.utils.fts import sync_account_fts
from app.utils.handles import normalize_handle
from app.utils.youtube import build_youtube_profile_url, is_youtube_channel_id, slugify_youtube_handle


def _resolve_handle(account: Account, siblings: list[Account]) -> str | None:
    for sibling in siblings:
        if sibling.platform == Platform.X and sibling.handle:
            return sibling.handle
    slug = slugify_youtube_handle(account.display_name)
    if slug and not is_youtube_channel_id(slug):
        return slug
    return None


def fix_youtube_handles(session: Session) -> dict[str, int]:
    stats = {"fixed": 0, "deduped_channel_type": 0, "skipped": 0}
    accounts = list(session.exec(select(Account).where(Account.platform == Platform.YOUTUBE)).all())
    by_creator: dict[str | None, list[Account]] = {}
    for account in accounts:
        by_creator.setdefault(account.creator_id, []).append(account)

    for account in accounts:
        if not is_youtube_channel_id(account.handle):
            if (
                account.channel_type
                and account.niche
                and account.channel_type.lower() == account.niche.lower()
            ):
                account.channel_type = None
                stats["deduped_channel_type"] += 1
                session.add(account)
            continue

        new_handle = _resolve_handle(account, by_creator.get(account.creator_id, []))
        if not new_handle:
            stats["skipped"] += 1
            continue

        new_handle = normalize_handle(new_handle)
        existing = session.exec(
            select(Account).where(
                Account.platform == Platform.YOUTUBE,
                Account.handle == new_handle,
                Account.account_id != account.account_id,
            )
        ).first()
        if existing:
            stats["skipped"] += 1
            continue

        channel_id = account.handle
        links = account.external_links or ""
        if "youtube_channel_id=" not in links:
            account.external_links = f"youtube_channel_id={channel_id}; {links}".strip("; ")

        account.handle = new_handle
        account.profile_url = build_youtube_profile_url(
            new_handle,
            channel_id=channel_id,
            external_links=account.external_links,
        )
        if account.channel_type and account.niche and account.channel_type.lower() == account.niche.lower():
            account.channel_type = None
            stats["deduped_channel_type"] += 1

        session.add(account)
        sync_account_fts(session, account)
        stats["fixed"] += 1
        print(f"  {channel_id} -> @{format_display_handle(Platform.YOUTUBE, new_handle, account.display_name)}")

    session.commit()
    return stats


def main() -> None:
    with Session(engine) as session:
        stats = fix_youtube_handles(session)
    print("YouTube handle fix complete:")
    for key, val in stats.items():
        print(f"  {key}: {val}")


if __name__ == "__main__":
    main()
