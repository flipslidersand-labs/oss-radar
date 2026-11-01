"""main._check_env() の警告分岐"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import main


def _run(monkeypatch, capsys, *, dry_run, api_key, url, env_url=None):
    monkeypatch.setattr(main, "EMBED_API_KEY", api_key)
    monkeypatch.setattr(main, "EMBED_URL", url)
    if env_url is None:
        monkeypatch.delenv("EMBED_URL", raising=False)
    else:
        monkeypatch.setenv("EMBED_URL", env_url)
    main._check_env(dry_run)
    return capsys.readouterr().err


def test_warns_when_api_key_missing(monkeypatch, capsys):
    err = _run(monkeypatch, capsys, dry_run=False, api_key="", url="http://localhost:9092/embed/batch")
    assert "EMBED_API_KEY が未設定" in err


def test_no_warning_when_dry_run(monkeypatch, capsys):
    err = _run(monkeypatch, capsys, dry_run=True, api_key="", url="http://example.com/embed")
    assert err == ""


def test_no_warning_when_configured_https(monkeypatch, capsys):
    err = _run(
        monkeypatch,
        capsys,
        dry_run=False,
        api_key="k",
        url="https://example.com/embed",
        env_url="https://example.com/embed",
    )
    assert err == ""


def test_warns_on_insecure_http_remote(monkeypatch, capsys):
    err = _run(monkeypatch, capsys, dry_run=False, api_key="k", url="http://embed.internal:9092/embed/batch")
    assert "平文で送信" in err


def test_default_url_branch_never_fires(monkeypatch, capsys):
    """EMBED_URL はモジュール読み込み時にデフォルト値が入るため「デフォルトのまま」警告は発火しない(現状の挙動を固定)。
    発火させるなら条件を `not os.getenv("EMBED_URL")` に直す必要がある(別途判断)。"""
    err = _run(monkeypatch, capsys, dry_run=False, api_key="k", url="http://localhost:9092/embed/batch", env_url=None)
    assert "デフォルト値" not in err
