"""Tool: ingest the user's saved Reddit items into the ChromaDB knowledge base."""

from __future__ import annotations

import sys
from typing import Annotated

from fastmcp.exceptions import ToolError
from pydantic import Field
from typing_extensions import TypedDict

from lib.chroma import get_collection
from lib.embeddings import embed
from lib.reddit import get_saved_items


def _normalize(kind: str, data: dict) -> tuple[str, dict]:
    """Build the embeddable text and Chroma metadata for one saved child."""
    if kind == "t1":
        title = data.get("link_title", "")
        text = f"{title}\n\n{data['body']}"
        item_type = "comment"
    elif kind == "t3":
        title = data["title"]
        text = f"{title}\n\n{data.get('selftext', '')}"
        item_type = "submission"
    else:
        raise ValueError(f"unsupported item kind {kind!r}")

    metadata = {
        "id": data["name"],
        "type": item_type,
        "title": title or "",
        "subreddit": data.get("subreddit") or "",
        "url": "https://reddit.com" + data["permalink"],
        "author": data.get("author") or "[deleted]",
        "created_utc": int(data["created_utc"]),
        "score": int(data.get("score", 0)),
    }
    return text, metadata


class IngestStats(TypedDict):
    """Counts from one ingest_saved run."""

    ingested: int
    skipped: int
    errors: int
    total_seen: int


def ingest_saved(
    limit: Annotated[
        int | None,
        Field(ge=1, description="Max saved items to pull, newest first; omit for all"),
    ] = None,
) -> IngestStats:
    """Pull the user's saved posts/comments from Reddit and embed the new ones into ChromaDB.

    Fetches the saved listing newest-first (Reddit caps it at roughly the most recent
    ~1000 items), skips items already in the index (deduped by id), and embeds and stores
    the rest. Safe to re-run at any time — call this to refresh the local index before
    search_saved if it looks empty or stale. Returns counts of ingested/skipped/errored
    items. Raises ToolError if the saved listing can't be fetched (e.g. an expired
    session cookie, or a network/HTTP failure).
    """
    collection = get_collection()

    ingested = skipped = errors = total_seen = 0

    try:
        for child in get_saved_items(limit):
            total_seen += 1
            try:
                data = child["data"]
                fullname = data["name"]

                if collection.get(ids=[fullname])["ids"]:
                    skipped += 1
                    continue

                text, metadata = _normalize(child.get("kind", ""), data)
                vector = embed(text)
                collection.add(
                    ids=[fullname],
                    embeddings=[vector],
                    metadatas=[metadata],
                    documents=[text],
                )
                ingested += 1
            except Exception as exc:
                item_id = child.get("data", {}).get("name", "<unknown>")
                print(
                    f"ingest_saved: error on item {item_id}: {type(exc).__name__}: {exc}",
                    file=sys.stderr,
                )
                errors += 1
    except RuntimeError as exc:
        # Only hint at the cookie for cookie-related failures; fetch_json raises
        # RuntimeError for network/HTTP/config problems too, where the hint misleads.
        hint = " — refresh REDDIT_SESSION_COOKIE in .env" if "cookie" in str(exc).lower() else ""
        raise ToolError(f"ingest_saved failed: {exc}{hint}") from exc

    return IngestStats(
        ingested=ingested,
        skipped=skipped,
        errors=errors,
        total_seen=total_seen,
    )
