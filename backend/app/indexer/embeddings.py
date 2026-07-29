"""
Wraps Voyage AI's code-aware embedding model. Each CodeChunk gets embedded
together with its linked commit/PR text, so retrieval surfaces the
historical context alongside the code itself (not just code-to-code
similarity).

Includes an elite offline fallback mode that generates deterministic,
normalized mock vectors in the absence of a valid VOYAGE_API_KEY, 
featuring safety catch-blocks that gracefully fall back if the live API call fails.
"""
from __future__ import annotations
import hashlib
import voyageai
from app.config import settings

_client = None


def is_valid_key(key: str) -> bool:
    """Checks if a loaded API key is a valid key and not a dummy placeholder or empty quotes."""
    if not key:
        return False
    cleaned = key.strip().strip("'\"").strip()
    if not cleaned or len(cleaned) < 10 or "your-" in cleaned or "placeholder" in cleaned:
        return False
    return True


def _get_client() -> voyageai.Client | None:
    global _client
    if not is_valid_key(settings.voyage_api_key):
        return None
    if _client is None:
        # Strip any accidental outer quotes from environment loading
        api_key = settings.voyage_api_key.strip().strip("'\"")
        _client = voyageai.Client(api_key=api_key)
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


def deterministic_mock_vector(text: str, dim: int = 1024) -> list[float]:
    """Generates a normalized, deterministic 1024-dimension float vector."""
    vector = []
    # Use deterministic pseudo-random floats based on text hash
    for i in range(dim):
        h = hashlib.sha256(f"{text}_{i}".encode()).hexdigest()
        val = int(h[:8], 16) / 4294967295.0 * 2.0 - 1.0
        vector.append(val)
    # Normalize vector
    mag = sum(x*x for x in vector) ** 0.5
    if mag > 0:
        return [x / mag for x in vector]
    return [0.0] * dim


def embed_texts(texts: list[str], input_type: str = "document") -> list[list[float]]:
    """
    input_type: "document" when embedding chunks for storage,
                "query" when embedding a user's question at retrieval time.
    """
    client = _get_client()
    if client is None:
        # Offline/Heuristic mode: return deterministic mock vectors
        return [deterministic_mock_vector(t) for t in texts]

    try:
        all_embeddings: list[list[float]] = []
        for i in range(0, len(texts), 128):
            batch = texts[i:i + 128]
            result = client.embed(batch, model=settings.voyage_model, input_type=input_type)
            all_embeddings.extend(result.embeddings)
        return all_embeddings
    except Exception as e:
        print(f"⚠️ Voyage AI embedding call failed (Error: {e}). Automatically falling back to deterministic mock vectors.")
        return [deterministic_mock_vector(t) for t in texts]
