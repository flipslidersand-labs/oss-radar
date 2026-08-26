"""oss_radar.query.build_filter() のユニットテスト"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from oss_radar.query import build_filter


def test_no_filters_returns_none():
    assert build_filter(None, None, 0) is None


def test_lang_filter():
    f = build_filter("Go", None, 0)
    assert f is not None
    assert len(f.must) == 1
    assert f.must[0].key == "lang"
    assert f.must[0].match.value == "Go"


def test_license_filter():
    f = build_filter(None, "MIT", 0)
    assert f is not None
    assert len(f.must) == 1
    assert f.must[0].key == "license"
    assert f.must[0].match.value == "MIT"


def test_stars_min_filter():
    f = build_filter(None, None, 500)
    assert f is not None
    assert len(f.must) == 1
    assert f.must[0].key == "stars"
    assert f.must[0].range.gte == 500


def test_stars_min_zero_excluded():
    assert build_filter(None, None, 0) is None


def test_all_filters_combined():
    f = build_filter("Rust", "Apache-2.0", 100)
    assert f is not None
    assert len(f.must) == 3
    keys = {c.key for c in f.must}
    assert keys == {"lang", "license", "stars"}


def test_empty_string_lang_excluded():
    assert build_filter("", None, 0) is None


def test_empty_string_license_excluded():
    assert build_filter(None, "", 0) is None


def test_source_filter():
    f = build_filter(None, None, 0, source="ossinsight")
    assert f is not None
    assert len(f.must) == 1
    assert f.must[0].key == "source"
    assert f.must[0].match.value == "ossinsight"


def test_since_filter():
    from datetime import datetime
    f = build_filter(None, None, 0, since="2026-08-20")
    assert f is not None
    assert len(f.must) == 1
    assert f.must[0].key == "fetched_at"
    assert f.must[0].range.gte == datetime(2026, 8, 20)


def test_source_and_since_combined():
    f = build_filter(None, None, 0, source="github-trending", since="2026-08-01")
    assert f is not None
    assert len(f.must) == 2
    keys = {c.key for c in f.must}
    assert keys == {"source", "fetched_at"}


def test_all_five_filters():
    f = build_filter("Go", "MIT", 100, source="ossinsight", since="2026-08-20")
    assert f is not None
    assert len(f.must) == 5
    keys = {c.key for c in f.must}
    assert keys == {"lang", "license", "stars", "source", "fetched_at"}
