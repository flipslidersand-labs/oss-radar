"""collectors.gh_trending.collect() — HTML パースとフォールバック"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from collectors.gh_trending import collect


def _article(href="/org/repo", desc="a lib", lang="Python", stars="1,234"):
    parts = ['<article class="Box-row">']
    if href is not None:
        parts.append(f'<h2><a href="{href}">x</a></h2>')
    if desc is not None:
        parts.append(f"<p>{desc}</p>")
    if lang is not None:
        parts.append(f'<span itemprop="programmingLanguage">{lang}</span>')
    if stars is not None:
        parts.append(f'<a href="{href or "/o/r"}/stargazers">{stars}</a>')
    parts.append("</article>")
    return "".join(parts)


def _collect(*articles, status_error=False):
    resp = MagicMock()
    resp.text = "<html>" + "".join(articles) + "</html>"
    if status_error:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError("503", request=MagicMock(), response=resp)
    client = MagicMock()
    client.__enter__.return_value.get.return_value = resp
    with patch("collectors.gh_trending.httpx.Client", return_value=client):
        return collect("weekly")


def test_normal_conversion():
    (r,) = _collect(_article())
    got = (r.full_name, r.description, r.lang, r.stars, r.source)
    assert got == ("org/repo", "a lib", "Python", 1234, "gh_trending")


def test_missing_optional_tags_use_defaults():
    (r,) = _collect(_article(desc=None, lang=None, stars=None))
    assert (r.description, r.lang, r.stars) == ("", None, 0)


def test_article_without_name_tag_is_skipped():
    assert _collect(_article(href=None)) == []


def test_href_without_slash_is_skipped():
    assert _collect(_article(href="/justone")) == []


def test_skipped_articles_do_not_drop_valid_ones():
    repos = _collect(_article(href="/justone"), _article(href="/a/b"))
    assert [r.full_name for r in repos] == ["a/b"]


def test_zero_repos_warns_on_stderr(capsys):
    assert _collect() == []
    assert "0 repos scraped" in capsys.readouterr().err


def test_http_error_propagates():
    with pytest.raises(httpx.HTTPStatusError):
        _collect(status_error=True)
