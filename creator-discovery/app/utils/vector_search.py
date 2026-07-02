"""pgvector-backed semantic search helpers.

Vector search only runs on Postgres (Supabase). On SQLite it's a no-op and the
caller falls back to keyword/FTS search.
"""
import logging
from typing import List, Optional, Sequence, Tuple

from sqlalchemy import text
from sqlmodel import Session

from app.core.config import get_settings

logger = logging.getLogger(__name__)

EMBED_DIM = 1536


def vector_supported() -> bool:
    return not get_settings().is_sqlite


def to_vector_literal(vec: Sequence[float]) -> str:
    return "[" + ",".join(f"{x:.6f}" for x in vec) + "]"


def ensure_vector_schema(session: Session) -> bool:
    """Enable pgvector + add the embedding column and index. Postgres-only.

    Returns True if the schema is ready, False if vectors aren't supported.
    """
    if not vector_supported():
        return False
    session.exec(text("SET lock_timeout = '5s'"))
    session.exec(text("SET statement_timeout = '60s'"))
    session.exec(text("CREATE EXTENSION IF NOT EXISTS vector"))
    session.exec(
        text(f"ALTER TABLE accounts ADD COLUMN IF NOT EXISTS embedding vector({EMBED_DIM})")
    )
    # HNSW gives fast approximate nearest-neighbour search with cosine distance.
    session.exec(
        text(
            "CREATE INDEX IF NOT EXISTS accounts_embedding_hnsw "
            "ON accounts USING hnsw (embedding vector_cosine_ops)"
        )
    )
    session.commit()
    return True


def store_embedding(session: Session, account_id: str, embedding: Sequence[float]) -> None:
    if not vector_supported() or not embedding:
        return
    session.exec(
        text("UPDATE accounts SET embedding = CAST(:vec AS vector) WHERE account_id = :id").bindparams(
            vec=to_vector_literal(embedding), id=account_id
        )
    )


def store_embeddings_batch(session: Session, items: Sequence[Tuple[str, Sequence[float]]]) -> None:
    """Update many rows' embeddings in a single round-trip (psycopg2)."""
    if not vector_supported() or not items:
        return
    from psycopg2.extras import execute_values

    rows = [(aid, to_vector_literal(vec)) for aid, vec in items]
    raw = session.connection().connection  # underlying psycopg2 connection
    with raw.cursor() as cur:
        execute_values(
            cur,
            "UPDATE accounts SET embedding = data.vec::vector "
            "FROM (VALUES %s) AS data(id, vec) "
            "WHERE accounts.account_id = data.id",
            rows,
            template="(%s, %s)",
        )
    session.commit()


def semantic_search_accounts(
    session: Session,
    embedding: Optional[Sequence[float]],
    *,
    limit: int = 80,
) -> List[Tuple[str, float]]:
    """Return [(account_id, similarity)] ordered by cosine similarity desc."""
    if not vector_supported() or not embedding:
        return []
    qvec = to_vector_literal(embedding)
    try:
        rows = session.exec(
            text(
                """
                SELECT account_id, 1 - (embedding <=> CAST(:qvec AS vector)) AS score
                FROM accounts
                WHERE embedding IS NOT NULL AND is_active = true
                ORDER BY embedding <=> CAST(:qvec AS vector)
                LIMIT :limit
                """
            ).bindparams(qvec=qvec, limit=limit)
        ).all()
    except Exception as exc:  # noqa: BLE001
        # e.g. extension/column not yet created — fall back to keyword search.
        logger.warning("Semantic search unavailable: %s", exc)
        return []
    return [(row[0], float(row[1])) for row in rows]


def rrf_fuse(*ranked_lists: Sequence[str], k: int = 60) -> List[str]:
    """Reciprocal Rank Fusion of several ordered id lists into one ranking."""
    scores: dict[str, float] = {}
    for ranked in ranked_lists:
        for rank, item in enumerate(ranked):
            scores[item] = scores.get(item, 0.0) + 1.0 / (k + rank + 1)
    return [item for item, _ in sorted(scores.items(), key=lambda kv: kv[1], reverse=True)]
