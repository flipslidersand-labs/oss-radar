"""collectors.bestofjs — レスポンス欠落キーへの耐性"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "collectors"))

from bestofjs import _fetch_lang


def _resp(body: dict):
    r = MagicMock()
    r.raise_for_status.return_value = None
    r.json.return_value = body
    return r


def test_fetch_lang_skips_items_missing_full_name_and_defaults_stars():
    body = {
        "items": [
            {"stargazers_count": 10},  # full_name 欠落 → スキップ
            {"full_name": "org/ok"},  # stargazers_count 欠落 → 0
            {"full_name": "org/full", "stargazers_count": 99},
        ]
    }
    with patch("bestofjs.httpx.get", return_value=_resp(body)):
        repos = _fetch_lang("JavaScript", {}, "2026-10-01", 50, "now")
    assert [(r.full_name, r.stars) for r in repos] == [("org/ok", 0), ("org/full", 99)]
