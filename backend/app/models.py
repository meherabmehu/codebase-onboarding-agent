"""
Shared data contracts. Every agent and API route speaks in these types
so the pipeline stays composable (Phase 1 -> 2 -> 3 -> 4 all pass these
objects rather than raw dicts).
"""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field


# ---------- Ingestion ----------

class RepoRequest(BaseModel):
    repo_url: str = Field(..., description="Public GitHub repo URL, e.g. https://github.com/org/repo")
    max_commits: Optional[int] = None


class CommitInfo(BaseModel):
    sha: str
    message: str
    author: str
    date: str
    files_touched: list[str]


class PRInfo(BaseModel):
    number: int
    title: str
    body: str
    merged: bool
    review_comments: list[str] = []
    linked_files: list[str] = []


class CodeChunk(BaseModel):
    """The atomic indexable unit: one function or class."""
    chunk_id: str
    file_path: str
    symbol_name: str
    symbol_type: str          # "function" | "class" | "method"
    start_line: int
    end_line: int
    source: str
    language: str
    linked_commit_shas: list[str] = []
    linked_pr_numbers: list[int] = []


class IngestResult(BaseModel):
    repo_url: str
    repo_id: str
    local_path: str
    chunks: list[CodeChunk]
    commits: list[CommitInfo]
    prs: list[PRInfo]


# ---------- Architecture Mapper ----------

class ModuleNode(BaseModel):
    name: str
    path: str
    depends_on: list[str] = []
    summary: str = ""


class ArchitectureOverview(BaseModel):
    repo_id: str
    written_overview: str
    modules: list[ModuleNode]
    mermaid_diagram: str


# ---------- Curriculum Planner ----------

class LearningStep(BaseModel):
    step_number: int
    title: str
    file_paths: list[str]
    rationale: str
    concepts: list[str] = []


class Curriculum(BaseModel):
    repo_id: str
    steps: list[LearningStep]


# ---------- Tutor ----------

class TutorQuestion(BaseModel):
    repo_id: str
    question: str
    step_number: Optional[int] = None


class Citation(BaseModel):
    type: str          # "commit" | "pr" | "inference"
    ref: str
    excerpt: str = ""


class TutorAnswer(BaseModel):
    answer: str
    citations: list[Citation]
    grounded: bool


# ---------- Quiz ----------

class QuizQuestion(BaseModel):
    step_number: int
    question: str
    expected_points: list[str]


class QuizRequest(BaseModel):
    repo_id: str
    step_number: int
    chat_history: list[dict] = []


class QuizSubmission(BaseModel):
    repo_id: str
    step_number: int
    question: str
    user_answer: str


class QuizGrade(BaseModel):
    score: float
    feedback: str
    passed: bool
