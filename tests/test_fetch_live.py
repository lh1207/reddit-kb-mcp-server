"""Offline tests for tools/fetch_live.py. No network."""

from __future__ import annotations

import pytest
from fastmcp.exceptions import ToolError

from tools import fetch_live


@pytest.mark.parametrize(
    "url",
    [
        "https://www.reddit.com/r/AskReddit/comments/abc123/some_title/",
        "https://old.reddit.com/r/AskReddit/comments/abc123/some_title/",
        "https://reddit.com/r/AskReddit/comments/abc123/",
        "https://reddit.com/r/AskReddit/comments/abc123",
    ],
)
def test_thread_path_re_accepts_thread_urls(url):
    assert fetch_live._THREAD_PATH_RE.search(url) is not None


@pytest.mark.parametrize(
    "url",
    [
        "https://reddit.com/r/AskReddit/",
        "https://reddit.com/r/AskReddit/top/",
        "https://reddit.com/user/someone",
        "not a url at all",
    ],
)
def test_thread_path_re_rejects_non_thread_urls(url):
    assert fetch_live._THREAD_PATH_RE.search(url) is None


@pytest.mark.parametrize(
    "url",
    [
        "https://reddit.com/r/AskReddit/",
        "not a url at all",
    ],
)
def test_fetch_reddit_thread_rejects_non_thread_url(url):
    with pytest.raises(ToolError, match="not a Reddit thread URL"):
        fetch_live.fetch_reddit_thread(url)


def test_fetch_reddit_thread_shapes_response(monkeypatch):
    listing = [
        {
            "data": {
                "children": [
                    {
                        "data": {
                            "name": "t3_1",
                            "title": "Thread title",
                            "subreddit": "sub",
                            "permalink": "/r/sub/comments/1/thread_title/",
                            "author": "op",
                            "score": 42,
                            "selftext": "post body",
                            "created_utc": 1000,
                        }
                    }
                ]
            }
        },
        {
            "data": {
                "children": [
                    {
                        "kind": "t1",
                        "data": {
                            "name": "t1_1",
                            "author": None,
                            "body": "a comment",
                            "score": 3,
                            "created_utc": 1001,
                        },
                    },
                    {
                        "kind": "more",
                        "data": {"name": "more_1"},
                    },
                ]
            }
        },
    ]
    monkeypatch.setattr(fetch_live, "fetch_json", lambda path, params=None: listing)

    thread = fetch_live.fetch_reddit_thread("https://reddit.com/r/sub/comments/1/thread_title/")

    assert thread["id"] == "t3_1"
    assert thread["title"] == "Thread title"
    assert thread["url"] == "https://reddit.com/r/sub/comments/1/thread_title/"
    assert len(thread["comments"]) == 1
    assert thread["comments"][0]["author"] == "[deleted]"
    assert thread["comments"][0]["body"] == "a comment"


def test_fetch_reddit_thread_wraps_runtime_error(monkeypatch):
    def raise_runtime_error(path, params=None):
        raise RuntimeError("Reddit request failed (500) for /r/sub/comments/1.json")

    monkeypatch.setattr(fetch_live, "fetch_json", raise_runtime_error)

    with pytest.raises(ToolError, match="fetch_reddit_thread failed"):
        fetch_live.fetch_reddit_thread("https://reddit.com/r/sub/comments/1/thread_title/")


def test_search_reddit_builds_restrict_sr_params(monkeypatch):
    captured = {}

    def fake_fetch_json(path, params=None):
        captured["path"] = path
        captured["params"] = params
        return {"data": {"children": []}}

    monkeypatch.setattr(fetch_live, "fetch_json", fake_fetch_json)

    fetch_live.search_reddit("proxmox", subreddit="homelab", limit=5)

    assert captured["path"] == "/r/homelab/search.json"
    assert captured["params"]["restrict_sr"] == "1"
    assert captured["params"]["q"] == "proxmox"
    assert captured["params"]["limit"] == 5


def test_search_reddit_no_subreddit_omits_restrict_sr(monkeypatch):
    captured = {}

    def fake_fetch_json(path, params=None):
        captured["path"] = path
        captured["params"] = params
        return {"data": {"children": []}}

    monkeypatch.setattr(fetch_live, "fetch_json", fake_fetch_json)

    fetch_live.search_reddit("proxmox")

    assert captured["path"] == "/search.json"
    assert "restrict_sr" not in captured["params"]


def test_search_reddit_filters_non_t3(monkeypatch):
    response = {
        "data": {
            "children": [
                {
                    "kind": "t3",
                    "data": {
                        "name": "t3_1",
                        "title": "A submission",
                        "subreddit": "sub",
                        "permalink": "/r/sub/comments/1/a/",
                        "author": None,
                        "score": 7,
                        "created_utc": 500,
                        "num_comments": 2,
                    },
                },
                {"kind": "t1", "data": {"name": "t1_ignored"}},
            ]
        }
    }
    monkeypatch.setattr(fetch_live, "fetch_json", lambda path, params=None: response)

    results = fetch_live.search_reddit("query")

    assert len(results) == 1
    assert results[0]["id"] == "t3_1"
    assert results[0]["author"] == "[deleted]"
    assert results[0]["url"] == "https://reddit.com/r/sub/comments/1/a/"
