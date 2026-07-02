"""Set up pgvector and backfill semantic-search embeddings for all accounts.

Usage:
    python scripts/embed_accounts.py            # embed accounts missing a vector
    python scripts/embed_accounts.py --all      # re-embed every account

Requires OPENAI_API_KEY and a Postgres (Supabase) database. Safe to re-run: it
commits per batch and only embeds rows still missing a vector, so it resumes
after an interruption.
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlmodel import Session, select

from app.db.session import engine
from app.models.account import Account
from app.services.embeddings.embedder import build_profile_text, embed_texts_sync
from app.utils.vector_search import (
    ensure_vector_schema,
    store_embeddings_batch,
    vector_supported,
)

BATCH = 200
MAX_RETRIES = 4


def _write_batch(items) -> None:
    """Persist a batch with retry/reconnect on transient connection drops."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with Session(engine) as session:
                store_embeddings_batch(session, items)
            return
        except OperationalError as exc:
            engine.dispose()
            if attempt == MAX_RETRIES:
                raise
            wait = 2 * attempt
            print(f"    connection dropped ({exc.orig}); retrying in {wait}s…")
            time.sleep(wait)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true", help="re-embed every account")
    args = parser.parse_args()

    if not vector_supported():
        print("Vector search needs Postgres/Supabase. Current DB is SQLite — aborting.")
        return

    with Session(engine) as session:
        print("Ensuring pgvector extension, column, and HNSW index…")
        ensure_vector_schema(session)
        if args.all:
            target_ids = [a for (a,) in session.exec(select(Account.account_id)).all()]
        else:
            rows = session.exec(
                text("SELECT account_id FROM accounts WHERE embedding IS NULL")
            ).all()
            target_ids = [r[0] for r in rows]

    total = len(target_ids)
    print(f"Embedding {total} account(s)…")
    if total == 0:
        return

    done = 0
    started = time.monotonic()
    for i in range(0, total, BATCH):
        chunk = target_ids[i : i + BATCH]
        with Session(engine) as session:
            accounts = [session.get(Account, aid) for aid in chunk]
            accounts = [a for a in accounts if a is not None]
            texts = [build_profile_text(a) for a in accounts]
            ids = [a.account_id for a in accounts]

        vectors = embed_texts_sync(texts)
        if not vectors:
            print("No embeddings returned (is OPENAI_API_KEY set?) — aborting.")
            return

        _write_batch(list(zip(ids, vectors)))
        done += len(ids)
        elapsed = time.monotonic() - started
        rate = done / elapsed if elapsed else 0
        print(f"  {done}/{total}  ({rate:.0f}/s)")

    print(f"Done. Embedded {done} accounts in {time.monotonic() - started:.0f}s.")


if __name__ == "__main__":
    main()
