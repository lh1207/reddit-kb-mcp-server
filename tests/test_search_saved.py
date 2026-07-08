"""Offline tests for tools/search_saved.py. No network, no real Chroma/Ollama."""

from __future__ import annotations

from tools import search_saved


class FakeEmptyCollection:
    def count(self):
        return 0


class FakeCollection:
    def __init__(self, response):
        self._response = response

    def count(self):
        return 3

    def query(self, query_embeddings, n_results, include):
        return self._response


def test_search_saved_empty_collection_returns_empty_without_embedding(monkeypatch):
    monkeypatch.setattr(search_saved, "get_collection", lambda: FakeEmptyCollection())

    def fail_embed(text):
        raise AssertionError("embed should not be called for an empty collection")

    monkeypatch.setattr(search_saved, "embed", fail_embed)

    assert search_saved.search_saved("anything") == []


def test_search_saved_shapes_and_orders_results(monkeypatch):
    response = {
        "metadatas": [
            [
                {
                    "id": "t3_1",
                    "type": "submission",
                    "title": "First",
                    "subreddit": "sub",
                    "url": "https://reddit.com/r/sub/1",
                    "author": "alice",
                    "score": 10,
                    "created_utc": 100,
                },
                {
                    "id": "t1_2",
                    "type": "comment",
                    "title": "Second",
                    "subreddit": "sub2",
                    "url": "https://reddit.com/r/sub2/2",
                    "author": "bob",
                    "score": 5,
                    "created_utc": 200,
                },
            ]
        ],
        "documents": [["first doc text", "second doc text"]],
        "distances": [[0.1, 0.4]],
    }
    monkeypatch.setattr(search_saved, "get_collection", lambda: FakeCollection(response))
    monkeypatch.setattr(search_saved, "embed", lambda text: [0.0, 0.0])

    results = search_saved.search_saved("query", limit=2)

    assert len(results) == 2
    assert results[0]["id"] == "t3_1"
    assert results[0]["distance"] == 0.1
    assert results[0]["text"] == "first doc text"
    assert results[1]["id"] == "t1_2"
    assert results[1]["distance"] == 0.4
