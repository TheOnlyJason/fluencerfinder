"""Clear stale RightFluencer Instagram follower counts so enrichment can refresh them."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlmodel import Session, select

from app.db.session import engine
from app.models.account import Account
from app.models.enums import Platform


def clear_stale_instagram_followers(session: Session) -> int:
    cleared = 0
    accounts = list(
        session.exec(
            select(Account).where(
                Account.platform == Platform.INSTAGRAM,
                Account.is_active == True,  # noqa: E712
            )
        ).all()
    )
    for account in accounts:
        links = account.external_links or ""
        if "source=rightfluencer" not in links:
            continue
        if account.follower_count is not None and account.follower_count < 1_000:
            account.follower_count = None
            session.add(account)
            cleared += 1
    session.commit()
    return cleared


def main() -> None:
    with Session(engine) as session:
        cleared = clear_stale_instagram_followers(session)
    print(f"Cleared {cleared} stale Instagram follower counts")


if __name__ == "__main__":
    main()
