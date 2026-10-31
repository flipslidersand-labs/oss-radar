"""oss_radar.collections.ensure_collection"""
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.models import Distance, VectorParams

sys.path.insert(0, str(Path(__file__).parent.parent))

from oss_radar.collections import ensure_collection

CFG = VectorParams(size=3, distance=Distance.COSINE)


def _client(existing=()):
    c = MagicMock()
    cols = []
    for n in existing:
        m = MagicMock()
        m.name = n
        cols.append(m)
    c.get_collections.return_value.collections = cols
    return c


def test_creates_when_missing_with_given_config():
    c = _client()
    ensure_collection(c, "x", CFG)
    c.create_collection.assert_called_once_with(collection_name="x", vectors_config=CFG)


def test_skips_when_exists():
    c = _client(["x"])
    ensure_collection(c, "x", CFG)
    c.create_collection.assert_not_called()


def test_409_is_success():
    c = _client()
    c.create_collection.side_effect = UnexpectedResponse(409, "x", b"exists", {})
    ensure_collection(c, "x", CFG)


def test_non_409_reraises():
    c = _client()
    c.create_collection.side_effect = UnexpectedResponse(500, "x", b"boom", {})
    with pytest.raises(UnexpectedResponse):
        ensure_collection(c, "x", CFG)
