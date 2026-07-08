"""Offline tests for tools/ingest.py. No network, no real Chroma/Ollama."""

from __future__ import annotations

import pytest
from fastmcp.exceptions import ToolError

from tools import ingest


class FakeCollection:
    """Minimal stand-in for a chromadb.Collection."""

    def __init__(self, existing_ids=None):
        self.existing_ids = set(existing_ids or [])
        self.added = []

    def get(self, ids):
        return {"ids": [i for i in ids if i in self.existing_ids]}

    def add(self, ids, embeddings, metadatas, documents):
        self.added.append(
            {"ids": ids, "embeddings": embeddings, "metadatas": metadatas, "documents": documents}
        )
        self.existing_ids.update(ids)


def test_normalize_t1_comment():
    data = {
        "name": "t1_abc",
        "link_title": "Original post title",
        "body": "This is the comment body",
        "permalink": "/r/foo/comments/x/y/t1_abc/",
        "subreddit": "foo",
        "author": "commenter",
        "created_utc": 100,
        "score": 5,
    }
    text, metadata = ingest._normalize("t1", data)
    assert text == "Original post title\n\nThis is the comment body"
    assert metadata["id"] == "t1_abc"
    assert metadata["type"] == "comment"
    assert metadata["title"] == "Original post title"
    assert metadata["subreddit"] == "foo"
    assert metadata["url"] == "https://reddit.com/r/foo/comments/x/y/t1_abc/"
    assert metadata["author"] == "commenter"
    assert metadata["created_utc"] == 100
    assert metadata["score"] == 5


def test_normalize_t3_submission():
    data = {
        "name": "t3_xyz",
        "title": "Submission title",
        "selftext": "Submission body",
        "permalink": "/r/bar/comments/z/w/",
        "subreddit": "bar",
        "author": "poster",
        "created_utc": 200,
        "score": 10,
    }
    text, metadata = ingest._normalize("t3", data)
    assert text == "Submission title\n\nSubmission body"
    assert metadata["type"] == "submission"
    assert metadata["title"] == "Submission title"


def test_normalize_unknown_kind_raises():
    with pytest.raises(ValueError, match="unsupported item kind"):
        ingest._normalize("t9", {})


def test_ingest_saved_counts_ingested_skipped_errors(monkeypatch):
    items = [
        # New submission -> ingested
        {
            "kind": "t3",
            "data": {
                "name": "t3_new",
                "title": "New title",
                "selftext": "New body",
                "permalink": "/p1",
                "subreddit": "sub",
                "author": "a",
                "created_utc": 1,
                "score": 1,
            },
        },
        # Already-ingested comment -> skipped (dedupe)
        {
            "kind": "t1",
            "data": {
                "name": "t1_dup",
                "link_title": "Dup title",
                "body": "Dup body",
                "permalink": "/p2",
                "subreddit": "sub",
                "author": "b",
                "created_utc": 2,
                "score": 2,
            },
        },
        # Unsupported kind -> errors
        {"kind": "t9", "data": {"name": "bad_item"}},
    ]

    fake_collection = FakeCollection(existing_ids={"t1_dup"})
    monkeypatch.setattr(ingest, "get_collection", lambda: fake_collection)
    monkeypatch.setattr(ingest, "get_saved_items", lambda limit: iter(items))
    monkeypatch.setattr(ingest, "embed", lambda text: [0.1, 0.2, 0.3])

    stats = ingest.ingest_saved()

    assert stats == {"ingested": 1, "skipped": 1, "errors": 1, "total_seen": 3}
    assert len(fake_collection.added) == 1
    assert fake_collection.added[0]["ids"] == ["t3_new"]


def test_ingest_saved_generator_runtime_error_becomes_tool_error(monkeypatch):
    fake_collection = FakeCollection()
    monkeypatch.setattr(ingest, "get_collection", lambda: fake_collection)

    def failing_saved_items(limit):
        raise RuntimeError("session cookie invalid or expired")
        yield  # pragma: no cover - unreachable, keeps this a generator function

    monkeypatch.setattr(ingest, "get_saved_items", failing_saved_items)
    monkeypatch.setattr(ingest, "embed", lambda text: [0.1])

    with pytest.raises(ToolError) as exc_info:
        ingest.ingest_saved()

    message = str(exc_info.value)
    assert "session cookie invalid or expired" in message
    assert "REDDIT_SESSION_COOKIE" in message


def test_ingest_saved_non_cookie_runtime_error_has_no_cookie_hint(monkeypatch):
    fake_collection = FakeCollection()
    monkeypatch.setattr(ingest, "get_collection", lambda: fake_collection)

    def failing_saved_items(limit):
        raise RuntimeError("Reddit request failed (503) for /user/x/saved.json")
        yield  # pragma: no cover - unreachable, keeps this a generator function

    monkeypatch.setattr(ingest, "get_saved_items", failing_saved_items)
    monkeypatch.setattr(ingest, "embed", lambda text: [0.1])

    with pytest.raises(ToolError) as exc_info:
        ingest.ingest_saved()

    message = str(exc_info.value)
    assert "Reddit request failed (503)" in message
    assert "REDDIT_SESSION_COOKIE" not in message
