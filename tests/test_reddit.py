"""Offline tests for lib/reddit.py. No network. Cookie value must never leak into errors."""

from __future__ import annotations

import requests

from lib import reddit


def _set_required_env(monkeypatch, cookie="fake-session-cookie-value"):
    monkeypatch.setenv("REDDIT_USERNAME", "testuser")
    monkeypatch.setenv("REDDIT_SESSION_COOKIE", cookie)
    monkeypatch.setenv("REDDIT_USER_AGENT", "reddit-kb-tests/0.1")


def test_fetch_json_missing_env_vars_lists_names(monkeypatch):
    monkeypatch.delenv("REDDIT_USERNAME", raising=False)
    monkeypatch.delenv("REDDIT_SESSION_COOKIE", raising=False)
    monkeypatch.delenv("REDDIT_USER_AGENT", raising=False)

    try:
        reddit.fetch_json("/foo")
        raised = None
    except RuntimeError as exc:
        raised = exc

    assert raised is not None
    message = str(raised)
    assert "REDDIT_USERNAME" in message
    assert "REDDIT_SESSION_COOKIE" in message
    assert "REDDIT_USER_AGENT" in message


def test_fetch_json_cookie_never_leaks_on_network_error(monkeypatch):
    secret = "SUPER-SECRET-COOKIE-DO-NOT-LEAK"
    _set_required_env(monkeypatch, cookie=secret)
    monkeypatch.setattr(reddit.time, "sleep", lambda seconds: None)

    def fake_get(url, params=None, headers=None, timeout=None):
        # A RequestException repr can embed the request (headers, cookie); simulate the
        # worst case by putting the cookie header into the exception message directly,
        # then assert fetch_json still doesn't propagate it.
        raise requests.RequestException(f"connection failed for {url} headers={headers}")

    monkeypatch.setattr(requests, "get", fake_get)

    try:
        reddit.fetch_json("/user/testuser/saved.json")
        raised = None
    except RuntimeError as exc:
        raised = exc

    assert raised is not None
    assert secret not in str(raised)
    assert secret not in repr(raised)


def test_get_saved_items_paginates_via_after_cursor(monkeypatch):
    _set_required_env(monkeypatch)
    monkeypatch.setattr(reddit.time, "sleep", lambda seconds: None)

    page1 = {
        "kind": "Listing",
        "data": {
            "children": [{"data": {"name": "t3_1"}}, {"data": {"name": "t3_2"}}],
            "after": "t3_2",
        },
    }
    page2 = {
        "kind": "Listing",
        "data": {
            "children": [{"data": {"name": "t3_3"}}],
            "after": None,
        },
    }
    calls = []

    def fake_fetch_json(path, params=None):
        calls.append(dict(params or {}))
        if "after" not in (params or {}):
            return page1
        assert params["after"] == "t3_2"
        return page2

    monkeypatch.setattr(reddit, "fetch_json", fake_fetch_json)

    items = list(reddit.get_saved_items())

    assert [item["data"]["name"] for item in items] == ["t3_1", "t3_2", "t3_3"]
    assert len(calls) == 2


def test_get_saved_items_limit_stops_early(monkeypatch):
    _set_required_env(monkeypatch)
    monkeypatch.setattr(reddit.time, "sleep", lambda seconds: None)

    page1 = {
        "kind": "Listing",
        "data": {
            "children": [
                {"data": {"name": "t3_1"}},
                {"data": {"name": "t3_2"}},
                {"data": {"name": "t3_3"}},
            ],
            "after": "t3_3",
        },
    }
    calls = []

    def fake_fetch_json(path, params=None):
        calls.append(dict(params or {}))
        return page1

    monkeypatch.setattr(reddit, "fetch_json", fake_fetch_json)

    items = list(reddit.get_saved_items(limit=2))

    assert [item["data"]["name"] for item in items] == ["t3_1", "t3_2"]
    # Only the first page should have been fetched: the limit is hit mid-page.
    assert len(calls) == 1


def test_get_saved_items_non_listing_raises(monkeypatch):
    _set_required_env(monkeypatch)
    monkeypatch.setattr(reddit.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(reddit, "fetch_json", lambda path, params=None: {"error": 403})

    try:
        list(reddit.get_saved_items())
        raised = None
    except RuntimeError as exc:
        raised = exc

    assert raised is not None
    assert "session cookie invalid or expired" in str(raised)
