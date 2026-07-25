"""
Orchestrates ingestion: clone -> walk commit history -> parse structure
-> pull PR data -> link commits/PRs to the code chunks they touched.

This linking step is the most important piece of the whole system: it's
what lets the Tutor answer "why" questions by retrieving the actual
commit/PR that shaped a given function, instead of guessing from the
code alone.
"""
from __future__ import annotations
import os
import re
import hashlib
import shutil
from git import Repo
from app.config import settings
from app.models import CommitInfo, IngestResult
from app.ingestor.parser import parse_repo
from app.ingestor.github_api import fetch_pull_requests, parse_owner_repo


def _repo_id(repo_url: str) -> str:
    return hashlib.sha1(repo_url.encode()).hexdigest()[:12]


def _clone_repo(repo_url: str, repo_id: str) -> str:
    local_path = os.path.join(settings.data_dir, "repos", repo_id)
    if os.path.exists(local_path):
        shutil.rmtree(local_path)
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    Repo.clone_from(repo_url, local_path, depth=500)  # shallow clone: bound ingestion time
    return local_path


def _walk_commits(local_path: str, max_commits: int) -> list[CommitInfo]:
    repo = Repo(local_path)
    commits: list[CommitInfo] = []
    for commit in repo.iter_commits(max_count=max_commits):
        try:
            files = list(commit.stats.files.keys())
        except Exception:
            files = []
        commits.append(CommitInfo(
            sha=commit.hexsha,
            message=commit.message.strip(),
            author=str(commit.author),
            date=commit.committed_datetime.isoformat(),
            files_touched=files,
        ))
    return commits


def _link_chunks_to_history(chunks, commits, prs):
    """
    For each code chunk, find commits that touched its file (most recent
    first) and PRs that reference its file. This is the cross-reference
    the Tutor later retrieves alongside the code itself.
    """
    # file_path -> list of commit shas that touched it, most recent first
    file_to_commits: dict[str, list[str]] = {}
    for commit in commits:
        for f in commit.files_touched:
            file_to_commits.setdefault(f, []).append(commit.sha)

    file_to_prs: dict[str, list[int]] = {}
    for pr in prs:
        for f in pr.linked_files:
            file_to_prs.setdefault(f, []).append(pr.number)

    for chunk in chunks:
        chunk.linked_commit_shas = file_to_commits.get(chunk.file_path, [])[:10]
        chunk.linked_pr_numbers = file_to_prs.get(chunk.file_path, [])[:10]

    return chunks


def ingest_repo(repo_url: str, max_commits: int | None = None) -> IngestResult:
    max_commits = max_commits or settings.max_commits_to_index
    repo_id = _repo_id(repo_url)

    local_path = _clone_repo(repo_url, repo_id)
    commits = _walk_commits(local_path, max_commits)
    chunks = parse_repo(local_path)

    owner, name = parse_owner_repo(repo_url)
    try:
        prs = fetch_pull_requests(owner, name)
    except Exception:
        # GitHub API can fail (rate limit, private repo, etc.) - degrade
        # gracefully rather than blocking ingestion entirely.
        prs = []

    chunks = _link_chunks_to_history(chunks, commits, prs)

    return IngestResult(
        repo_url=repo_url,
        repo_id=repo_id,
        local_path=local_path,
        chunks=chunks,
        commits=commits,
        prs=prs,
    )