"""Export influencers to data/influencers.json and frontend/public/influencers.json."""
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
    with Session(engine) as session:
        path = write_influencers_json(session, DATA_PATH, PUBLIC_PATH)
    print(f"Exported influencers snapshot to:")
    print(f"  {path}")
    print(f"  {PUBLIC_PATH}")


if __name__ == "__main__":
    main()
