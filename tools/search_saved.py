"""Tool: semantic search over the user's ingested saved Reddit content."""

from __future__ import annotations

from lib.chroma import get_collection
from lib.embeddings import embed


def search_saved(query: str, limit: int = 10) -> list[dict]:
    """Embed the query and return the top matching saved posts/comments from ChromaDB,
    closest first."""
    collection = get_collection()

    n_results = min(limit, collection.count())
    if n_results < 1:
        return []

    try:
        query_vector = embed(query)
    except Exception as exc:
        raise RuntimeError(f"embedding failed: {exc}") from exc

    response = collection.query(
        query_embeddings=[query_vector],
        n_results=n_results,
        include=["metadatas", "documents", "distances"],
    )

    results = []
    for metadata, document, distance in zip(
        response["metadatas"][0],
        response["documents"][0],
        response["distances"][0],
        strict=False,
    ):
        results.append(
            {
                "id": str(metadata["id"]),
                "type": str(metadata["type"]),
                "title": str(metadata.get("title", "")),
                "subreddit": str(metadata.get("subreddit", "")),
                "url": str(metadata.get("url", "")),
                "author": str(metadata.get("author", "")),
                "score": int(metadata.get("score", 0)),
                "created_utc": int(metadata["created_utc"]),
                "text": document,
                "distance": float(distance),
            }
        )

    return results
