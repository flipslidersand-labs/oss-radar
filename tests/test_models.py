"""models.Repo.embed_text() / to_payload() の分岐"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from models import Repo


def _repo(**kw) -> Repo:
    base = dict(full_name="org/repo", description="a lib", stars=7, lang="Go", topics=["cli", "tui"],
                license="MIT", source="github_search", fetched_at="2026-01-01T00:00:00+00:00")
    base.update(kw)
    return Repo(**base)


def test_embed_text_all_fields():
    assert _repo().embed_text() == "org/repo | a lib | cli tui | Go"


def test_embed_text_empty_description():
    assert _repo(description="").embed_text() == "org/repo | cli tui | Go"


def test_embed_text_empty_topics():
    assert _repo(topics=[]).embed_text() == "org/repo | a lib | Go"


def test_embed_text_lang_none():
    assert _repo(lang=None).embed_text() == "org/repo | a lib | cli tui"


def test_embed_text_name_only():
    assert _repo(description="", topics=[], lang=None).embed_text() == "org/repo"


def test_to_payload_all_fields():
    p = _repo().to_payload()
    assert p == {
        "full_name": "org/repo", "description": "a lib", "stars": 7, "lang": "Go",
        "topics": ["cli", "tui"], "license": "MIT", "source": "github_search",
        "fetched_at": "2026-01-01T00:00:00+00:00",
    }


def test_to_payload_keeps_none_lang_and_license():
    p = _repo(lang=None, license=None).to_payload()
    assert p["lang"] is None and p["license"] is None
