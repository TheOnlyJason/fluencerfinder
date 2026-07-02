"""Export influencers to data/influencers.json.

Deliberately does NOT write into frontend/public/: Vite copies public/ into the
built bundle, so a snapshot there (which can contain scraped contact emails)
would be published on the next deploy. Pass --include-public only if you
understand that and want a bundled snapshot anyway.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlmodel import Session

from app.db.session import engine
from app.services.export.influencers_json import write_influencers_json

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "influencers.json"
PUBLIC_PATH = ROOT / "frontend" / "public" / "influencers.json"


def main() -> None:
    paths = [DATA_PATH]
    if "--include-public" in sys.argv[1:]:
        paths.append(PUBLIC_PATH)
    with Session(engine) as session:
        write_influencers_json(session, *paths)
    print("Exported influencers snapshot to:")
    for p in paths:
        print(f"  {p}")


if __name__ == "__main__":
    main()
