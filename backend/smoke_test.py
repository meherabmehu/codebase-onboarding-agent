"""
Smoke test: ingest -> index -> architecture mapping.
Run with: python smoke_test.py
"""
from app.ingestor.repo_ingestor import ingest_repo
from app.agents.architecture_mapper import map_architecture

TEST_REPO = "https://github.com/kennethreitz/setup.py"

if __name__ == "__main__":
    print(f"Ingesting {TEST_REPO} ...")
    result = ingest_repo(TEST_REPO, max_commits=50)
    print(f"chunks parsed: {len(result.chunks)}")

    print("\nGenerating architecture overview (calling Claude)...")
    overview = map_architecture(result.repo_id, result.chunks)

    print("\n--- WRITTEN OVERVIEW ---")
    print(overview.written_overview)

    print("\n--- MODULES ---")
    for m in overview.modules:
        print(f"  {m.name} ({m.path}) -> depends on: {m.depends_on}")
        print(f"    {m.summary}")

    print("\n--- MERMAID DIAGRAM ---")
    print(overview.mermaid_diagram)