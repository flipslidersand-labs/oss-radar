"""search.search() の出力: 0件メッセージ・テーブル・description 切り詰め・lang 未指定"""
from types import SimpleNamespace
from unittest.mock import patch

from click.testing import CliRunner

import search


def _hit(score=0.9, **payload):
    return SimpleNamespace(score=score, payload=payload)


def _invoke(hits, args=("q",)):
    with patch.object(search, "SearchClient") as client:
        client.return_value.search.return_value = hits
        result = CliRunner().invoke(search.search, list(args))
        return result, client.return_value.search


def test_empty_results_prints_hint():
    result, _ = _invoke([])
    assert result.exit_code == 0
    assert "結果なし" in result.output
    assert "Score" not in result.output


def test_table_row_format():
    result, _ = _invoke([_hit(0.8751, stars=1234, lang="Go", full_name="org/repo", description="a lib")])
    assert "Score" in result.output
    assert " 0.875" in result.output
    assert "  1234" in result.output
    assert "Go" in result.output
    assert "org/repo" in result.output
    assert "a lib" in result.output


def test_description_truncated_to_60_chars():
    result, _ = _invoke([_hit(stars=1, lang="Go", full_name="o/r", description="x" * 61)])
    assert "x" * 60 in result.output
    assert "x" * 61 not in result.output


def test_lang_none_shows_dash():
    result, _ = _invoke([_hit(stars=1, lang=None, full_name="o/r", description="d")])
    row = result.output.strip().splitlines()[-1]
    assert row.split()[2] == "-"


def test_filters_forwarded_to_client():
    _, search_mock = _invoke([], ("q", "--lang", "Go", "--stars-min", "500", "--limit", "3"))
    kwargs = search_mock.call_args.kwargs
    assert kwargs["lang"] == "Go"
    assert kwargs["stars_min"] == 500
    assert kwargs["limit"] == 3
