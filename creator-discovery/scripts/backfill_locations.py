"""Clean and canonicalize accounts.location_text in place.

- Canonicalizes variants ("Los Angeles" → "Los Angeles, CA", "US" → "United States")
- Junk that isn't a place (link services, platform names, URLs): tries to
  re-infer a real location from the bio/handle; clears the field otherwise
- Leaves unknown-but-plausible values (small towns we don't know) untouched —
  the facet layer already hides uncorroborated one-offs from the dropdown

Dry-run by default; pass --apply to write.

    python scripts/backfill_locations.py            # report only
    python scripts/backfill_locations.py --apply    # write changes
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlmodel import Session, select

from app.db.session import engine
from app.models.account import Account
from app.utils.location import infer_location, is_junk_location, sanitize_location


def plan_change(account: Account) -> tuple[str, str | None] | None:
    """Return (reason, new_value) if this account's location should change.

    Order matters: only WHOLE-value junk ("Linktree", URLs) may be replaced or
    cleared. A value sanitize doesn't recognize but that isn't junk (a small
    town, "Brecon Beacons") is kept verbatim — never overwritten by a guess
    inferred from the bio.
    """
    raw = (account.location_text or "").strip()
    if not raw:
        return None

    canonical = sanitize_location(raw)
    if canonical and canonical != raw:
        return ("canonicalize", canonical)
    if canonical:
        return None  # already clean

    if is_junk_location(raw):
        # Definitely not a place — try the bio/handle for a real one.
        inferred = infer_location(account.bio_text, handle=account.handle)
        if inferred:
            return ("re-infer", inferred)
        return ("clear-junk", None)

    # Plausible-looking but unknown: keep the data.
    return None


def main() -> None:
    apply = "--apply" in sys.argv[1:]
    changes: list[tuple[str, str, str, str | None]] = []

    with Session(engine) as session:
        accounts = session.exec(
            select(Account).where(Account.is_active == True)  # noqa: E712
        ).all()
        for account in accounts:
            planned = plan_change(account)
            if not planned:
                continue
            reason, new_value = planned
            changes.append((reason, account.handle, account.location_text, new_value))
            if apply:
                account.location_text = new_value
                session.add(account)
        if apply:
            session.commit()

    by_reason: dict[str, int] = {}
    for reason, handle, old, new in changes:
        by_reason[reason] = by_reason.get(reason, 0) + 1
        print(f"  [{reason:12}] @{handle:24.24} {old!r} -> {new!r}")
    print()
    mode = "APPLIED" if apply else "DRY RUN (pass --apply to write)"
    print(f"{mode}: {len(changes)} of {len(accounts)} accounts — {by_reason}")


if __name__ == "__main__":
    main()
