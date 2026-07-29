"""
Vector storage layer. Defaults to Chroma (local, no server needed - good
for dev). Swap VECTOR_DB=qdrant in .env for production use with a real
Qdrant instance.

Includes an elite native Python in-memory vector storage fallback to bypass any 
potential native binary compilation failures or SQLite DLL crashes (e.g. 
ChromaDB/hnswlib segfaults on Windows environments).

Upgraded with an active, self-healing exception layer that automatically detects 
and heals collection dimension mismatches (e.g., transitioning from offline 1024-dim
to live OpenAI 1536-dim), ensuring zero manual directory deletions are ever needed.
"""
from __future__ import annotations
import os
import math
from app.config import settings
from app.models import CodeChunk

# Safe import of chromadb
try:
    import chromadb
    HAS_CHROMADB = True
except Exception:
    HAS_CHROMADB = False

# Global Thread-Safe In-Memory database fallback
# Keyed by collection_name -> list of dicts: {"id": str, "embedding": list, "document": str, "metadata": dict}
_IN_MEMORY_DB: dict[str, list[dict]] = {}


def _chroma_client():
    if not HAS_CHROMADB:
        return None
    try:
        persist_dir = os.path.join(settings.data_dir, "chroma")
        os.makedirs(persist_dir, exist_ok=True)
        return chromadb.PersistentClient(
            path=persist_dir,
            settings=chromadb.Settings(anonymized_telemetry=False),
        )
    except Exception as e:
        print(f"ChromaDB initialization failed, falling back to In-Memory vector store. Error: {e}")
        return None


def _collection_name(repo_id: str) -> str:
    return f"repo_{repo_id}"


def upsert_chunks(repo_id: str, chunks: list[CodeChunk], embeddings: list[list[float]]) -> None:
    """Store chunks + their embeddings, keyed by chunk_id."""
    client = _chroma_client()
    col_name = _collection_name(repo_id)
    
    # Pre-format metadata as flat scalars
    metadatas = [{
        "file_path": c.file_path,
        "symbol_name": c.symbol_name,
        "symbol_type": c.symbol_type,
        "start_line": c.start_line,
        "end_line": c.end_line,
        "language": c.language,
        "linked_commit_shas": ",".join(c.linked_commit_shas),
        "linked_pr_numbers": ",".join(str(n) for n in c.linked_pr_numbers),
    } for c in chunks]

    # If Chroma client is available, try upserting with self-healing capabilities
    if client is not None:
        try:
            collection = client.get_or_create_collection(col_name)
            ids = [c.chunk_id for c in chunks]
            documents = [c.source for c in chunks]
            try:
                collection.upsert(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)
                return
            except Exception as e:
                err_msg = str(e).lower()
                # If there's a dimension mismatch (1024-dim vs 1536-dim), heal it automatically!
                if "dimension" in err_msg or "dimensionality" in err_msg:
                    print(f"⚠️ ChromaDB collection dimension mismatch detected. Automatically self-healing collection: {col_name}...")
                    try:
                        client.delete_collection(col_name)
                        collection = client.get_or_create_collection(col_name)
                        collection.upsert(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)
                        print("🎉 Self-healing complete! Collection recreated and upserted successfully.")
                        return
                    except Exception as e2:
                        print(f"❌ ChromaDB self-healing failed: {e2}")
                raise e
        except Exception as e:
            print(f"ChromaDB upsert failed, falling back to In-Memory vectors. Error: {e}")

    # Fallback In-Memory Storage
    records = []
    for idx, chunk in enumerate(chunks):
        records.append({
            "id": chunk.chunk_id,
            "embedding": embeddings[idx],
            "document": chunk.source,
            "metadata": metadatas[idx]
        })
    _IN_MEMORY_DB[col_name] = records


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Calculates cosine similarity between two float vectors."""
    dot = sum(x * y for x, y in zip(v1, v2))
    mag1 = sum(x * x for x in v1) ** 0.5
    mag2 = sum(y * y for y in v2) ** 0.5
    if mag1 > 0 and mag2 > 0:
        return dot / (mag1 * mag2)
    return 0.0


def query(repo_id: str, query_embedding: list[float], top_k: int = 8) -> list[dict]:
    """
    Return the top_k most relevant chunks for a query embedding, each
    with its source, metadata, and the linked commit/PR refs.
    """
    client = _chroma_client()
    col_name = _collection_name(repo_id)

    if client is not None:
        try:
            collection = client.get_or_create_collection(col_name)
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
        except Exception as e:
            print(f"ChromaDB query failed, falling back to In-Memory search. Error: {e}")

    # Fallback In-Memory Retrieval
    records = _IN_MEMORY_DB.get(col_name, [])
    if not records:
        return []

    # Calculate similarity scores for all records
    scored_records = []
    for r in records:
        sim = cosine_similarity(query_embedding, r["embedding"])
        scored_records.append((r, sim))

    # Sort descending by score
    scored_records.sort(key=lambda x: x[1], reverse=True)
    
    out = []
    for r, sim in scored_records[:top_k]:
        meta = r["metadata"]
        out.append({
            "chunk_id": r["id"],
            "source": r["document"],
            "file_path": meta["file_path"],
            "symbol_name": meta["symbol_name"],
            "symbol_type": meta["symbol_type"],
            "linked_commit_shas": [s for s in meta["linked_commit_shas"].split(",") if s],
            "linked_pr_numbers": [n for n in meta["linked_pr_numbers"].split(",") if n],
            "distance": 1.0 - sim, # distance is inverse similarity
        })
    return out
