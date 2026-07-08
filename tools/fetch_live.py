"""Tools: live Reddit lookups (fetch a thread, search Reddit) via the cookie-auth
old.reddit JSON listing."""

from __future__ import annotations

import re
from typing import Annotated
from urllib.parse import urlsplit

from fastmcp.exceptions import ToolError
from pydantic import Field
from typing_extensions import TypedDict

from lib.reddit import fetch_json

_THREAD_PATH_RE = re.compile(r"/r/([^/]+)/comments/([0-9a-z]+)")


class ThreadComment(TypedDict):
    """One top-level comment on a fetched thread."""

    id: str
    author: str
    body: str
    score: int
    created_utc: int


class Thread(TypedDict):
    """A fetched Reddit thread: the post plus its top-level comments."""

    id: str
    title: str
    subreddit: str
    url: str
    author: str
    score: int
    selftext: str
    created_utc: int
    comments: list[ThreadComment]


class SearchResult(TypedDict):
    """One submission returned by a live Reddit search."""

    id: str
    title: str
    subreddit: str
    url: str
    author: str
    score: int
    created_utc: int
    num_comments: int


def fetch_reddit_thread(
    url: Annotated[str, Field(description="A reddit.com or old.reddit.com thread URL")],
    comment_limit: Annotated[
        int, Field(ge=1, le=200, description="Max top-level comments to return")
    ] = 50,
) -> Thread:
    """Fetch a live Reddit thread by URL: the post body plus its top-level comments.

    Hits live Reddit directly (using the user's session cookie), not the local saved-items
    index — use this when the user provides or has found a specific thread link and wants
    its content. Only top-level comments are returned (no reply nesting). Raises ToolError
    if the URL isn't a Reddit thread link or the request fails.
    """
    match = _THREAD_PATH_RE.search(urlsplit(url).path)
    if not match:
        raise ToolError(f"fetch_reddit_thread: not a Reddit thread URL: {url}")
    subreddit, post_id = match.groups()

    try:
        response = fetch_json(
            f"/r/{subreddit}/comments/{post_id}.json",
            params={"limit": comment_limit},
        )
        post = response[0]["data"]["children"][0]["data"]
        children = response[1]["data"]["children"]

        comments: list[ThreadComment] = []
        for child in children:
            if child.get("kind") != "t1":
                continue
            data = child["data"]
            comments.append(
                ThreadComment(
                    id=data["name"],
                    author=data.get("author") or "[deleted]",
                    body=data.get("body", ""),
                    score=int(data.get("score", 0)),
                    created_utc=int(data["created_utc"]),
                )
            )

        return Thread(
            id=post["name"],
            title=post["title"],
            subreddit=post.get("subreddit") or "",
            url="https://reddit.com" + post["permalink"],
            author=post.get("author") or "[deleted]",
            score=int(post.get("score", 0)),
            selftext=post.get("selftext", ""),
            created_utc=int(post["created_utc"]),
            comments=comments[:comment_limit],
        )
    except RuntimeError as exc:
        raise ToolError(f"fetch_reddit_thread failed for {url}: {exc}") from exc
    except Exception as exc:
        raise ToolError(
            f"fetch_reddit_thread failed for {url}: "
            f"unexpected response shape ({type(exc).__name__}: {exc})"
        ) from exc


def search_reddit(
    query: Annotated[str, Field(description="Search terms, e.g. 'proxmox ghost node'")],
    subreddit: Annotated[
        str | None,
        Field(description="Restrict the search to this subreddit, if given"),
    ] = None,
    limit: Annotated[int, Field(ge=1, le=50, description="Max results to return")] = 10,
) -> list[SearchResult]:
    """Search live Reddit for submissions, optionally scoped to one subreddit.

    Hits live Reddit directly (using the user's session cookie) — use this for current or
    fresh content that wouldn't be in the local saved-items index yet. Results follow
    Reddit's relevance ranking, not semantic similarity. Raises ToolError if the request
    fails.
    """
    path = f"/r/{subreddit}/search.json" if subreddit else "/search.json"
    params = {"q": query, "limit": limit, "sort": "relevance", "type": "link"}
    if subreddit:
        params["restrict_sr"] = "1"

    try:
        response = fetch_json(path, params=params)
        children = response["data"]["children"]

        results: list[SearchResult] = []
        for child in children:
            if child.get("kind") != "t3":
                continue
            data = child["data"]
            results.append(
                SearchResult(
                    id=data["name"],
                    title=data["title"],
                    subreddit=data.get("subreddit") or "",
                    url="https://reddit.com" + data["permalink"],
                    author=data.get("author") or "[deleted]",
                    score=int(data.get("score", 0)),
                    created_utc=int(data["created_utc"]),
                    num_comments=int(data.get("num_comments", 0)),
                )
            )

        return results
    except RuntimeError as exc:
        raise ToolError(
            f"search_reddit failed (query={query!r}, subreddit={subreddit!r}): {exc}"
        ) from exc
    except Exception as exc:
        raise ToolError(
            f"search_reddit failed (query={query!r}, subreddit={subreddit!r}): "
            f"unexpected response shape ({type(exc).__name__}: {exc})"
        ) from exc
