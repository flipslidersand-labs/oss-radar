"""oss_radar.env_check.insecure_embed_url_warning() のユニットテスト"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from oss_radar.env_check import insecure_embed_url_warning


@pytest.mark.parametrize("url", [
    "http://your-embed-svc:9092/embed/batch",
    "http://192.168.1.10:9092/embed/batch",
])
def test_warns_on_remote_http_with_key(url):
    assert insecure_embed_url_warning(url, "secret") is not None


@pytest.mark.parametrize("url", [
    "http://localhost:9092/embed/batch",
    "http://127.0.0.1:9092/embed/batch",
    "http://[::1]:9092/embed/batch",
    "https://embed.example.com/embed/batch",
])
def test_no_warning_for_local_or_https(url):
    assert insecure_embed_url_warning(url, "secret") is None


def test_no_warning_without_api_key():
    assert insecure_embed_url_warning("http://your-embed-svc:9092/embed/batch", "") is None
