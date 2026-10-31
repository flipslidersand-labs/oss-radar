"""search.py が API キー平文送信の警告を stderr に出すこと"""

from unittest.mock import patch

from click.testing import CliRunner

import search


def _run(embed_url: str, api_key: str):
    with (
        patch.object(search, "EMBED_URL", embed_url),
        patch.object(search, "EMBED_API_KEY", api_key),
        patch.object(search, "SearchClient") as client,
    ):
        client.return_value.search.return_value = []
        return CliRunner().invoke(search.search, ["q"])


def test_warns_on_remote_http_with_key():
    r = _run("http://embed.example.com/embed/batch", "secret")
    assert "[WARN]" in r.stderr
    assert "secret" not in r.stderr


def test_no_warning_for_https_or_localhost_or_no_key():
    for url, key in [
        ("https://embed.example.com/e", "k"),
        ("http://localhost:9092/e", "k"),
        ("http://embed.example.com/e", ""),
    ]:
        assert "[WARN]" not in _run(url, key).stderr
