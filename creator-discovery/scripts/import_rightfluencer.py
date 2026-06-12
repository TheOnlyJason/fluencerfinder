"""Import RightFluencer MongoDB BSON dumps into Supabase."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlmodel import Session

from app.db.session import engine
from app.services.importers.rightfluencer import import_rightfluencer

DEFAULT_DATA_DIR = (
    Path(__file__).resolve().parents[2] / "rightfluencer" / "mongo-data" / "influencers_db"
)


def main() -> None:
    data_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DATA_DIR
    if not data_dir.exists():
        print(f"Data directory not found: {data_dir}")
        print("Clone https://github.com/manojkarthick/rightfluencer or pass a path.")
        sys.exit(1)

    with Session(engine) as session:
        stats = import_rightfluencer(session, data_dir, skip_existing=True)

    print("RightFluencer import complete:")
    for key, val in stats.items():
        print(f"  {key}: {val}")


if __name__ == "__main__":
    main()
