"""Bulk-discover creators to build up the catalog.

Runs web discovery for each query and saves + classifies the new profiles it
finds. Long-running by nature (~1-2 min per query: web scrape + per-profile
classify/embed). Progress is durable — every profile is committed as it's
found, so Ctrl-C at any point keeps everything discovered so far.

Query sources (first one given wins):
  positional args      explicit queries        bulk_discover.py "ugc" "fitness LA"
  --queries-file FILE  one query per line
  --niches / --cities  a niche x city matrix   --niches ugc,beauty --cities "Los Angeles,Miami"
  (default)            a broad built-in niche list

Options:
  --max-new N     new profiles to save per query   (default 15)
  --limit N       result size per query            (default 30)
  --delay S       seconds between queries          (default 3)
  --max-queries N cap the number of queries run
  --dry-run       print the query plan and exit (no network, no writes)

Examples:
  python scripts/bulk_discover.py --dry-run
  python scripts/bulk_discover.py --niches ugc --cities "Los Angeles,New York,Miami"
  python scripts/bulk_discover.py --max-new 20 --max-queries 10
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# A broad default net — common influencer verticals. Expand with --cities.
DEFAULT_NICHES = [
    "ugc", "fitness", "beauty", "skincare", "fashion", "food", "cooking",
    "gaming", "travel", "lifestyle", "tech", "comedy", "music", "dance",
    "parenting", "pets", "home decor", "finance", "art", "photography",
    "fashion styling", "wellness", "outdoors", "automotive", "gardening",
]


def build_queries(args) -> list[str]:
    if args.queries:
        return args.queries
    if args.queries_file:
        lines = Path(args.queries_file).read_text(encoding="utf-8").splitlines()
        return [q.strip() for q in lines if q.strip() and not q.startswith("#")]

    niches = (
        [n.strip() for n in args.niches.split(",") if n.strip()]
        if args.niches
        else DEFAULT_NICHES
    )
    cities = [c.strip() for c in args.cities.split(",") if c.strip()] if args.cities else []
    if not cities:
        return list(niches)
    return [f"{niche} in {city}" for city in cities for niche in niches]


async def run(args) -> None:
    queries = build_queries(args)
    if args.max_queries:
        queries = queries[: args.max_queries]

    print(f"Planned {len(queries)} queries (~1-2 min each ≈ {len(queries) * 1.5:.0f} min).")
    if args.dry_run:
        for q in queries:
            print(f"  - {q}")
        print("\nDry run — nothing was searched or saved.")
        return

    # DISCOVER_MAX_NEW is read at import time, so set it before importing.
    os.environ["DISCOVER_MAX_NEW"] = str(args.max_new)

    from sqlmodel import Session, func, select

    from app.db.session import engine
    from app.models.account import Account
    from app.schemas.search import SearchRequest
    from app.services.discovery.service import search_creators

    def total_accounts() -> int:
        with Session(engine) as s:
            return s.exec(select(func.count()).select_from(Account)).one()

    start_total = total_accounts()
    saved = 0
    print(f"Starting. DB has {start_total} accounts. Ctrl-C to stop (progress is kept).\n")

    try:
        for i, query in enumerate(queries, 1):
            t = time.monotonic()
            try:
                # A new session per query so one failure can't poison the rest.
                with Session(engine) as session:
                    resp = await search_creators(
                        session,
                        SearchRequest(query=query, use_external_providers=True, limit=args.limit),
                    )
                new = resp.from_providers
            except Exception as exc:  # noqa: BLE001
                print(f"[{i}/{len(queries)}] {query!r} — ERROR: {exc}")
                continue
            saved += new
            print(
                f"[{i}/{len(queries)}] {query!r:38.38} +{new:2d} new "
                f"({time.monotonic() - t:.0f}s) — {saved} saved so far"
            )
            if i < len(queries) and args.delay:
                await asyncio.sleep(args.delay)
    except KeyboardInterrupt:
        print("\nInterrupted — keeping everything saved so far.")

    end_total = total_accounts()
    print(
        f"\nDone. {saved} new profiles reported; DB {start_total} -> {end_total} "
        f"(+{end_total - start_total} net rows)."
    )


def main() -> None:
    p = argparse.ArgumentParser(description="Bulk-discover creators to fill the catalog.")
    p.add_argument("queries", nargs="*", help="Explicit queries (overrides other sources)")
    p.add_argument("--queries-file", help="File with one query per line")
    p.add_argument("--niches", help="Comma-separated niches (default: a broad built-in list)")
    p.add_argument("--cities", help="Comma-separated cities; makes a niche x city matrix")
    p.add_argument("--max-new", type=int, default=15, help="New profiles per query (default 15)")
    p.add_argument("--limit", type=int, default=30, help="Result size per query (default 30)")
    p.add_argument("--delay", type=float, default=3.0, help="Seconds between queries (default 3)")
    p.add_argument("--max-queries", type=int, help="Cap the number of queries run")
    p.add_argument("--dry-run", action="store_true", help="Print the query plan and exit")
    args = p.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
