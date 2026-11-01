"""環境変数の既定値は oss_radar/defaults.py だけに書く(#147)"""

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from oss_radar import defaults

ROOT = Path(__file__).parent.parent
LITERALS = [
    defaults.DEFAULT_QDRANT_URL,
    defaults.DEFAULT_EMBED_URL,
    defaults.DEFAULT_EMBED_COLLECTION,
    defaults.DEFAULT_COLLECTION,
    defaults.DEFAULT_COMMUNITY_COLLECTION,
]


def _source_files():
    for p in ROOT.rglob("*.py"):
        rel = p.relative_to(ROOT).parts
        if rel[0] in {"tests", ".venv", ".claude", "errors"} or p.name == "defaults.py":
            continue
        yield p


def _string_constants(path: Path) -> set[str]:
    """docstring を除く文字列リテラル(コードとして書かれた値)の集合"""
    tree = ast.parse(path.read_text())
    docstrings = {
        id(n.body[0].value)
        for n in ast.walk(tree)
        if isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef))
        and n.body
        and isinstance(n.body[0], ast.Expr)
        and isinstance(n.body[0].value, ast.Constant)
    }
    return {
        n.value
        for n in ast.walk(tree)
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docstrings
    }


def test_default_literals_not_duplicated_outside_defaults():
    offenders = [
        f"{p.relative_to(ROOT)}: {lit}" for p in _source_files() for lit in LITERALS if lit in _string_constants(p)
    ]
    assert offenders == []


def test_entrypoints_use_the_shared_defaults(monkeypatch):
    for name in ("QDRANT_URL", "EMBED_URL", "EMBED_COLLECTION", "COLLECTION", "COMMUNITY_COLLECTION"):
        monkeypatch.delenv(name, raising=False)
    import importlib

    import main
    import mcp_server
    import search

    # dotenv の .env があっても環境変数を空に戻して再読込する
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: False)
    for mod in (main, search, mcp_server):
        importlib.reload(mod)
        assert mod.QDRANT_URL == defaults.DEFAULT_QDRANT_URL
        assert mod.EMBED_URL == defaults.DEFAULT_EMBED_URL
        assert mod.EMBED_COLLECTION == defaults.DEFAULT_EMBED_COLLECTION
        assert mod.COLLECTION == defaults.DEFAULT_COLLECTION
