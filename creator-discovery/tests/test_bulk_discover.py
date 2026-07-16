"""Query-plan building for the bulk discovery script (no network)."""
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from bulk_discover import DEFAULT_NICHES, build_queries


def _args(**kw):
    base = dict(queries=[], queries_file=None, niches=None, cities=None)
    base.update(kw)
    return SimpleNamespace(**base)


def test_explicit_queries_win():
    assert build_queries(_args(queries=["ugc", "beauty LA"])) == ["ugc", "beauty LA"]


def test_default_is_the_broad_niche_list():
    assert build_queries(_args()) == DEFAULT_NICHES


def test_niche_city_matrix():
    q = build_queries(_args(niches="ugc,beauty", cities="Los Angeles,Miami"))
    assert q == [
        "ugc in Los Angeles",
        "beauty in Los Angeles",
        "ugc in Miami",
        "beauty in Miami",
    ]


def test_niches_only_when_no_cities():
    assert build_queries(_args(niches="ugc, fitness")) == ["ugc", "fitness"]
