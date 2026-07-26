"""
Vector storage layer. Defaults to Chroma (local, no server needed - good
for dev). Swap VECTOR_DB=qdrant in .env for production use with a real
Qdrant instance.

Each repo gets its own collection (namespaced by repo_id) so multiple
ingested repos don't mix results.
"""
from __future__ import annotations
import os
import chromadb
from app.config import settings
from app.models import CodeChunk


def _chroma_client():
    persist_dir = os.path.join(settings.data_dir, "chroma")
    os.makedirs(persist_dir, exist_ok=True)
    return chromadb.PersistentClient(
        path=persist_dir,
        settings=chromadb.Settings(anonymized_telemetry=False),
    )


def _collection_name(repo_id: str) -> str:
    return f"repo_{repo_id}"


def upsert_chunks(repo_id: str, chunks: list[CodeChunk], embeddings: list[list[float]]) -> None:
    """Store chunks + their embeddings, keyed by chunk_id."""
    client = _chroma_client()
    collection = client.get_or_create_collection(_collection_name(repo_id))

    ids = [c.chunk_id for c in chunks]
    documents = [c.source for c in chunks]
    metadatas = [{
        "file_path": c.file_path,
        "symbol_name": c.symbol_name,
        "symbol_type": c.symbol_type,
        "start_line": c.start_line,
        "end_line": c.end_line,
        "language": c.language,
        # Chroma metadata must be flat scalars, so join lists to strings
        "linked_commit_shas": ",".join(c.linked_commit_shas),
        "linked_pr_numbers": ",".join(str(n) for n in c.linked_pr_numbers),
    } for c in chunks]

    collection.upsert(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)


def query(repo_id: str, query_embedding: list[float], top_k: int = 8) -> list[dict]:
    """
    Return the top_k most relevant chunks for a query embedding, each
    with its source, metadata, and the linked commit/PR refs needed
    for the Tutor to cite real history.
    """
    client = _chroma_client()
    collection = client.get_or_create_collection(_collection_name(repo_id))

    results = collection.query(query_embeddings=[query_embedding], n_results=top_k)

    out = []
    for i in range(len(results["ids"][0])):
        meta = results["metadatas"][0][i]
        out.append({
            "chunk_id": results["ids"][0][i],
            "source": results["documents"][0][i],
            "file_path": meta["file_path"],
            "symbol_name": meta["symbol_name"],
            "symbol_type": meta["symbol_type"],
            "linked_commit_shas": [s for s in meta["linked_commit_shas"].split(",") if s],
            "linked_pr_numbers": [n for n in meta["linked_pr_numbers"].split(",") if n],
            "distance": results["distances"][0][i],
        })
    return out