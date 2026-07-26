"""
Orchestrates indexing: for each code chunk, build embedding text that
combines the code with its linked commit/PR context, embed it, and
store it in the vector DB. This is what makes retrieval return both
the relevant code AND its historical "why" in one shot.
"""
from __future__ import annotations
from app.models import IngestResult
from app.indexer.embeddings import build_embedding_text, embed_texts
from app.indexer.vector_store import upsert_chunks


def index_repo(ingest_result: IngestResult) -> int:
    """
    Embeds and stores all chunks from an IngestResult.
    Returns the number of chunks indexed.
    """
    chunks = ingest_result.chunks
    if not chunks:
        return 0

    # look up commit messages / PR titles by sha/number for context-building
    commit_by_sha = {c.sha: c.message for c in ingest_result.commits}
    pr_by_number = {p.number: p.title for p in ingest_result.prs}

    texts = []
    for chunk in chunks:
        commit_msgs = [commit_by_sha[sha] for sha in chunk.linked_commit_shas if sha in commit_by_sha]
        pr_titles = [pr_by_number[n] for n in chunk.linked_pr_numbers if n in pr_by_number]
        texts.append(build_embedding_text(chunk.source, commit_msgs, pr_titles))

    embeddings = embed_texts(texts, input_type="document")
    upsert_chunks(ingest_result.repo_id, chunks, embeddings)

    return len(chunks)