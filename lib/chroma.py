"""ChromaDB persistent collection access."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import chromadb


def get_collection() -> chromadb.Collection:
    """Open (or create) the persistent reddit-kb collection at CHROMA_PATH, cosine space,
    no embedding function attached."""
    chroma_path = os.environ.get("CHROMA_PATH", "./store/chroma")
    name = os.environ.get("COLLECTION_NAME", "reddit_saved")

    import chromadb

    client = chromadb.PersistentClient(path=chroma_path)
    return client.get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},
    )
