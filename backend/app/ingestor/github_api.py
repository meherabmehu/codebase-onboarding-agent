"""
Pulls PR/issue discussion via the GitHub REST API (PyGithub).
This is the data that lets the Tutor answer "why" questions with real
review-comment context, not just commit messages.
"""
from __future__ import annotations
from github import Github, Auth
from app.config import settings
from app.models import PRInfo


def _client() -> Github:
    if settings.github_token:
        return Github(auth=Auth.Token(settings.github_token))
    # Unauthenticated: 60 req/hr, fine for small demo repos only
    return Github()


def fetch_pull_requests(owner: str, repo: str, limit: int = 200) -> list[PRInfo]:
    """
    Fetch merged PRs with their review comments and the files they touched.
    Capped at `limit` to keep ingestion time bounded for large repos.
    """
    gh = _client()
    repository = gh.get_repo(f"{owner}/{repo}")
    prs: list[PRInfo] = []

    for pr in repository.get_pulls(state="closed", sort="updated", direction="desc")[:limit]:
        if not pr.merged:
            continue
        try:
            comments = [c.body for c in pr.get_review_comments() if c.body]
            files = [f.filename for f in pr.get_files()]
        except Exception:
            # Rate limit or transient API error: skip enrichment, keep the PR shell
            comments, files = [], []

        prs.append(PRInfo(
            number=pr.number,
            title=pr.title or "",
            body=pr.body or "",
            merged=True,
            review_comments=comments[:20],   # cap noisy threads
            linked_files=files,
        ))
    return prs


def parse_owner_repo(repo_url: str) -> tuple[str, str]:
    """https://github.com/owner/repo(.git) -> ("owner", "repo")"""
    cleaned = repo_url.rstrip("/").removesuffix(".git")
    parts = cleaned.split("/")
    return parts[-2], parts[-1]