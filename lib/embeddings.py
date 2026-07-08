"""Text embeddings via the Ollama API (nomic-embed-text)."""

from __future__ import annotations

import os


def embed(text: str) -> list[float]:
    """Embed a single text with EMBED_MODEL via OLLAMA_BASE_URL and return its vector."""
    return embed_batch([text])[0]


def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts with EMBED_MODEL via OLLAMA_BASE_URL and return their vectors,
    one per input, order preserved."""
    if not texts:
        return []

    base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.environ.get("EMBED_MODEL", "nomic-embed-text")

    import ollama

    client = ollama.Client(host=base_url)

    try:
        if hasattr(client, "embed"):
            response = client.embed(model=model, input=texts)
            vectors = [list(v) for v in response.embeddings]
        else:
            vectors = [
                list(client.embeddings(model=model, prompt=text)["embedding"]) for text in texts
            ]
    except ollama.ResponseError as exc:
        if exc.status_code == 404:
            raise RuntimeError(
                f"Embedding model {model!r} not found on Ollama at {base_url}"
                f" — run `ollama pull {model}`"
            ) from exc
        raise RuntimeError(
            f"Ollama embedding request failed for model {model!r}: {exc.error}"
        ) from exc

    if len(vectors) != len(texts) or any(not v for v in vectors):
        raise RuntimeError(
            f"Ollama returned {len(vectors)} embedding(s) for {len(texts)}"
            f" input(s) with model {model!r}; response was empty or incomplete"
        )

    return vectors
