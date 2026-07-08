"""Tools: live Reddit lookups (fetch a thread, search Reddit) via the cookie-auth
old.reddit JSON listing."""

from __future__ import annotations

import re
from urllib.parse import urlsplit

from lib.reddit import fetch_json

_THREAD_PATH_RE = re.compile(r"/r/([^/]+)/comments/([0-9a-z]+)")


def fetch_reddit_thread(url: str, comment_limit: int = 50) -> dict:
    """Fetch a live Reddit thread by URL and return its post body plus top-level comments."""
    match = _THREAD_PATH_RE.search(urlsplit(url).path)
    if not match:
        raise RuntimeError(f"fetch_reddit_thread: not a Reddit thread URL: {url}")
    subreddit, post_id = match.groups()

    try:
        response = fetch_json(
            f"/r/{subreddit}/comments/{post_id}.json",
            params={"limit": comment_limit},
        )
        post = response[0]["data"]["children"][0]["data"]
        children = response[1]["data"]["children"]

        comments = []
        for child in children:
            if child.get("kind") != "t1":
                continue
            data = child["data"]
            comments.append(
                {
                    "id": data["name"],
                    "author": data.get("author") or "[deleted]",
                    "body": data.get("body", ""),
                    "score": int(data.get("score", 0)),
                    "created_utc": int(data["created_utc"]),
                }
            )

        return {
            "id": post["name"],
            "title": post["title"],
            "subreddit": post.get("subreddit") or "",
            "url": "https://reddit.com" + post["permalink"],
            "author": post.get("author") or "[deleted]",
            "score": int(post.get("score", 0)),
            "selftext": post.get("selftext", ""),
            "created_utc": int(post["created_utc"]),
            "comments": comments[:comment_limit],
        }
    except RuntimeError as exc:
        raise RuntimeError(f"fetch_reddit_thread failed for {url}: {exc}") from exc
    except Exception as exc:
        raise RuntimeError(
            f"fetch_reddit_thread failed for {url}: "
            f"unexpected response shape ({type(exc).__name__}: {exc})"
        ) from exc


def search_reddit(query: str, subreddit: str | None = None, limit: int = 10) -> list[dict]:
    """Search Reddit live (optionally scoped to a subreddit) and return matching submissions."""
    path = f"/r/{subreddit}/search.json" if subreddit else "/search.json"
    params = {"q": query, "limit": limit, "sort": "relevance", "type": "link"}
    if subreddit:
        params["restrict_sr"] = "1"

    try:
        response = fetch_json(path, params=params)
        children = response["data"]["children"]

        results = []
        for child in children:
            if child.get("kind") != "t3":
                continue
            data = child["data"]
            results.append(
                {
                    "id": data["name"],
                    "title": data["title"],
                    "subreddit": data.get("subreddit") or "",
                    "url": "https://reddit.com" + data["permalink"],
                    "author": data.get("author") or "[deleted]",
                    "score": int(data.get("score", 0)),
                    "created_utc": int(data["created_utc"]),
                    "num_comments": int(data.get("num_comments", 0)),
                }
            )

        return results
    except RuntimeError as exc:
        raise RuntimeError(
            f"search_reddit failed (query={query!r}, subreddit={subreddit!r}): {exc}"
        ) from exc
    except Exception as exc:
        raise RuntimeError(
            f"search_reddit failed (query={query!r}, subreddit={subreddit!r}): "
            f"unexpected response shape ({type(exc).__name__}: {exc})"
        ) from exc
