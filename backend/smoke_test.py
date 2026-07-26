"""
Throwaway script to sanity-check the ingestor end-to-end.
Run with: python smoke_test.py
Delete this file once ingestion is confirmed working.
"""
from app.ingestor.repo_ingestor import ingest_repo

# small, well-known repo -> fast to clone, good for a first test
TEST_REPO = "https://github.com/kennethreitz/setup.py"

if __name__ == "__main__":
    print(f"Ingesting {TEST_REPO} ...")
    result = ingest_repo(TEST_REPO, max_commits=50)

    print(f"\nrepo_id: {result.repo_id}")
    print(f"local_path: {result.local_path}")
    print(f"commits pulled: {len(result.commits)}")
    print(f"PRs pulled: {len(result.prs)}")
    print(f"code chunks parsed: {len(result.chunks)}")

    if result.chunks:
        sample = result.chunks[0]
        print(f"\nsample chunk:")
        print(f"  file: {sample.file_path}")
        print(f"  symbol: {sample.symbol_name} ({sample.symbol_type})")
        print(f"  linked commits: {sample.linked_commit_shas[:3]}")
        print(f"  linked PRs: {sample.linked_pr_numbers[:3]}")