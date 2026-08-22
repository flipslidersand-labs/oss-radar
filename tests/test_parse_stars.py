"""collectors.gh_trending._parse_stars() のユニットテスト"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from collectors.gh_trending import _parse_stars


def test_plain_integer():
    assert _parse_stars("1234") == 1234


def test_comma_separated():
    assert _parse_stars("1,234") == 1234


def test_k_suffix_integer():
    assert _parse_stars("2k") == 2000


def test_k_suffix_fractional():
    assert _parse_stars("1.5k") == 1500


def test_k_suffix_large():
    assert _parse_stars("12.3k") == 12300


def test_whitespace_stripped():
    assert _parse_stars("  500  ") == 500


def test_empty_string_returns_zero():
    assert _parse_stars("") == 0


def test_non_numeric_returns_zero():
    assert _parse_stars("★") == 0


def test_k_non_numeric_returns_zero():
    assert _parse_stars("xk") == 0


def test_uppercase_k():
    assert _parse_stars("3K") == 3000


def test_zero():
    assert _parse_stars("0") == 0
