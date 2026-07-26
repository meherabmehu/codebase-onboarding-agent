"""
Throwaway script to sanity-check ingestion + indexing + retrieval end-to-end.
Run with: python smoke_test.py
Delete this file once the pipeline is confirmed working.
"""
from app.ingestor.repo_ingestor import ingest_repo
from app.indexer.indexer import index_repo
from app.indexer.embeddings import embed_texts
from app.indexer.vector_store import query

TEST_REPO = "https://github.com/kennethreitz/setup.py"

if __name__ == "__main__":
    print(f"Ingesting {TEST_REPO} ...")
    result = ingest_repo(TEST_REPO, max_commits=50)
    print(f"chunks parsed: {len(result.chunks)}")

    print("\nIndexing (embedding + storing)...")
    count = index_repo(result)
    print(f"chunks indexed: {count}")

    print("\nTesting retrieval...")
    test_question = "how does this project handle uploading to PyPI"
    query_embedding = embed_texts([test_question], input_type="query")[0]
    hits = query(result.repo_id, query_embedding, top_k=3)

    print(f"\nQuery: '{test_question}'")
    for h in hits:
        print(f"\n  match: {h['symbol_name']} ({h['symbol_type']}) in {h['file_path']}")
        print(f"  distance: {h['distance']:.4f}")
        print(f"  linked commits: {h['linked_commit_shas'][:2]}")