"""Tool: semantic search over the user's ingested saved Reddit content."""

from __future__ import annotations

from typing import Annotated

from fastmcp.exceptions import ToolError
from pydantic import Field
from typing_extensions import TypedDict

from lib.chroma import get_collection
from lib.embeddings import embed


class SavedResult(TypedDict):
    """One saved post/comment matched against a search_saved query."""

    id: str
    type: str
    title: str
    subreddit: str
    url: str
    author: str
    score: int
    created_utc: int
    text: str
    distance: float


def search_saved(
    query: Annotated[
        str,
        Field(description="Natural-language query, e.g. 'proxmox ghost node fix'"),
    ],
    limit: Annotated[int, Field(ge=1, le=50, description="Max results to return")] = 10,
) -> list[SavedResult]:
    """Semantic search over the user's already-ingested saved Reddit posts/comments.

    This is a local index lookup — it never calls live Reddit. Use it first whenever the
    user references something they saved, bookmarked, or half-remember ("that thread about
    X"). Results are ordered closest match first; `distance` is a cosine distance where
    lower means more similar. Returns `[]` if nothing has been ingested yet — if that
    happens, suggest running `ingest_saved` first.
    """
    collection = get_collection()

    n_results = min(limit, collection.count())
    if n_results < 1:
        return []

    try:
        query_vector = embed(query)
    except Exception as exc:
        raise ToolError(f"embedding failed: {exc}") from exc

    response = collection.query(
        query_embeddings=[query_vector],
        n_results=n_results,
        include=["metadatas", "documents", "distances"],
    )

    results: list[SavedResult] = []
    for metadata, document, distance in zip(
        response["metadatas"][0],
        response["documents"][0],
        response["distances"][0],
        strict=False,
    ):
        results.append(
            SavedResult(
                id=str(metadata["id"]),
                type=str(metadata["type"]),
                title=str(metadata.get("title", "")),
                subreddit=str(metadata.get("subreddit", "")),
                url=str(metadata.get("url", "")),
                author=str(metadata.get("author", "")),
                score=int(metadata.get("score", 0)),
                created_utc=int(metadata["created_utc"]),
                text=document,
                distance=float(distance),
            )
        )

    return results
