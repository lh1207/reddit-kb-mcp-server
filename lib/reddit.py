"""Reddit access via the logged-in old.reddit JSON listing (session cookie auth)."""

from __future__ import annotations

import os
import time
from collections.abc import Iterator

_REQUIRED_VARS = (
    "REDDIT_USERNAME",
    "REDDIT_SESSION_COOKIE",
    "REDDIT_USER_AGENT",
)

_BASE_URL = "https://old.reddit.com"
_TIMEOUT = 30
_RETRY_DELAY = 5
_PAGE_SIZE = 100
_MAX_PAGES = 50


def fetch_json(path: str, params: dict | None = None) -> dict:
    """GET https://old.reddit.com{path} as the logged-in user and return parsed JSON.
    Authenticates with the reddit_session cookie from REDDIT_SESSION_COOKIE; retries once
    on failure."""
    from dotenv import load_dotenv

    load_dotenv()

    missing = [var for var in _REQUIRED_VARS if not os.environ.get(var)]
    if missing:
        raise RuntimeError("Missing required environment variables: " + ", ".join(missing))

    import requests

    url = _BASE_URL + path
    merged_params = {**(params or {}), "raw_json": 1}
    headers = {
        "Cookie": f"reddit_session={os.environ['REDDIT_SESSION_COOKIE']}",
        "User-Agent": os.environ["REDDIT_USER_AGENT"],
    }

    status: int | str = "network error"
    for attempt in range(2):
        if attempt:
            time.sleep(_RETRY_DELAY)
        try:
            response = requests.get(url, params=merged_params, headers=headers, timeout=_TIMEOUT)
        except requests.RequestException:
            # Deliberately not chained/interpolated: the request (and any
            # exception repr) carries the session cookie.
            status = "network error"
            continue
        if response.status_code == 200:
            return response.json()
        status = response.status_code

    raise RuntimeError(f"Reddit request failed ({status}) for {path}")


def get_saved_items(limit: int | None = None) -> Iterator[dict]:
    """Yield the user's saved items (raw {"kind", "data"} children) from
    /user/<REDDIT_USERNAME>/saved.json, newest first, paging until exhausted or `limit`
    items."""
    from dotenv import load_dotenv

    load_dotenv()

    # Empty username falls through to fetch_json's missing-vars error.
    username = os.environ.get("REDDIT_USERNAME", "")
    yielded = 0
    after: str | None = None

    for page in range(_MAX_PAGES):
        if page:
            time.sleep(1)

        params: dict = {"limit": _PAGE_SIZE}
        if after:
            params["after"] = after

        listing = fetch_json(f"/user/{username}/saved.json", params)

        children = listing.get("data", {}).get("children")
        if listing.get("kind") != "Listing" or children is None:
            raise RuntimeError("session cookie invalid or expired")

        for child in children:
            yield child
            yielded += 1
            if limit is not None and yielded >= limit:
                return

        after = listing["data"].get("after")
        if not after:
            return
