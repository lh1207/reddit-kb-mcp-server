"""Tool: ingest the user's saved Reddit items into the ChromaDB knowledge base."""

from __future__ import annotations

import sys

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


def ingest_saved(limit: int | None = None) -> dict:
    """Fetch the user's saved posts/comments, embed new ones, add them to ChromaDB, and
    return ingest stats."""
    collection = get_collection()

    ingested = skipped = errors = total_seen = 0

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

    return {
        "ingested": ingested,
        "skipped": skipped,
        "errors": errors,
        "total_seen": total_seen,
    }
