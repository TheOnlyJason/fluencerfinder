"""Vercel serverless entrypoint for the FastAPI backend."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "creator-discovery"
sys.path.insert(0, str(ROOT))

from app.main import app  # noqa: E402
