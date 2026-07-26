"""
Smoke test: full pipeline through the Tutor agent.
"""
from app.ingestor.repo_ingestor import ingest_repo
from app.indexer.indexer import index_repo
from app.agents.tutor import answer_question

TEST_REPO = "https://github.com/kennethreitz/setup.py"

if __name__ == "__main__":
    print(f"Ingesting {TEST_REPO} ...")
    result = ingest_repo(TEST_REPO, max_commits=50)
    print(f"chunks parsed: {len(result.chunks)}")

    print("\nIndexing...")
    index_repo(result)

    commit_lookup = {c.sha: c.message for c in result.commits}

    question = "Why does this project have a custom UploadCommand instead of just using twine directly?"
    print(f"\nAsking Tutor: '{question}'")
    answer = answer_question(result.repo_id, question, commit_lookup)

    print(f"\n--- ANSWER ---")
    print(answer.answer)
    print(f"\ngrounded: {answer.grounded}")
    print(f"\n--- CITATIONS ---")
    for c in answer.citations:
        print(f"  [{c.type}] ref={c.ref} excerpt={c.excerpt[:80]}")