"""
Wraps Voyage AI's code-aware embedding model. Each CodeChunk gets embedded
together with its linked commit/PR text, so retrieval surfaces the
historical context alongside the code itself (not just code-to-code
similarity).
"""
from __future__ import annotations
import voyageai
from app.config import settings

_client = None


def _get_client() -> voyageai.Client:
    global _client
    if _client is None:
        _client = voyageai.Client(api_key=settings.voyage_api_key)
    return _client


def build_embedding_text(chunk_source: str, commit_messages: list[str], pr_titles: list[str]) -> str:
    """
    Concatenate code with its linked history so the embedding captures
    both *what* the code does and *why* it exists, per commit/PR context.
    """
    parts = [chunk_source]
    if commit_messages:
        parts.append("Related commits: " + " | ".join(commit_messages[:5]))
    if pr_titles:
        parts.append("Related PRs: " + " | ".join(pr_titles[:5]))
    return "\n\n".join(parts)


def embed_texts(texts: list[str], input_type: str = "document") -> list[list[float]]:
    """
    input_type: "document" when embedding chunks for storage,
                "query" when embedding a user's question at retrieval time.
    Batches in groups of 128 (Voyage's practical batch limit).
    """
    client = _get_client()
    all_embeddings: list[list[float]] = []

    for i in range(0, len(texts), 128):
        batch = texts[i:i + 128]
        result = client.embed(batch, model=settings.voyage_model, input_type=input_type)
        all_embeddings.extend(result.embeddings)

    return all_embeddings