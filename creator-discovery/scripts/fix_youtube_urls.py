"""Repair YouTube profile_url values to use /user/ or /channel/ links."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlmodel import Session, select

from app.db.session import engine
from app.models.account import Account
from app.models.enums import Platform
from app.utils.youtube import build_youtube_profile_url, parse_youtube_channel_id


def fix_youtube_profile_urls(session: Session) -> int:
    updated = 0
    accounts = list(session.exec(select(Account).where(Account.platform == Platform.YOUTUBE)).all())
    for account in accounts:
        channel_id = parse_youtube_channel_id(account.external_links)
        new_url = build_youtube_profile_url(
            account.handle,
            channel_id=channel_id,
            external_links=account.external_links,
        )
        if account.profile_url != new_url:
            account.profile_url = new_url
            session.add(account)
            updated += 1
    session.commit()
    return updated


def main() -> None:
    with Session(engine) as session:
        count = fix_youtube_profile_urls(session)
    print(f"Updated {count} YouTube profile URLs")


if __name__ == "__main__":
    main()
