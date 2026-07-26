"""
FastAPI application entrypoint. Wires together ingestion, indexing, and
all four agents into a real HTTP API.

Run with: uvicorn app.main:app --reload --port 8000
"""
from __future__ import annotations
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.models import (
    RepoRequest, IngestResult, ArchitectureOverview, Curriculum,
    TutorQuestion, TutorAnswer, QuizQuestion, QuizSubmission, QuizGrade,
    LearningStep,
)
from app.ingestor.repo_ingestor import ingest_repo
from app.indexer.indexer import index_repo
from app.agents.architecture_mapper import map_architecture
from app.agents.curriculum_planner import plan_curriculum
from app.agents.tutor import answer_question
from app.agents.quiz_generator import generate_quiz_question, grade_answer

app = FastAPI(title="Codebase Onboarding Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this to your frontend's origin before production
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory cache of ingested repos, keyed by repo_id.
# Fine for a single-instance dev/demo deployment; swap for Redis/DB if you
# need this to survive restarts or scale across multiple server instances.
_REPO_CACHE: dict[str, dict] = {}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ingest", response_model=dict)
def ingest(req: RepoRequest):
    """Clone, parse, and index a repo. Returns repo_id for use in later calls."""
    try:
        result = ingest_repo(req.repo_url, req.max_commits)
        index_repo(result)

        _REPO_CACHE[result.repo_id] = {
            "ingest_result": result,
            "commit_lookup": {c.sha: c.message for c in result.commits},
            "quiz_questions": {}, # step_number -> QuizQuestion
        }

        return {
            "repo_id": result.repo_id,
            "chunks_indexed": len(result.chunks),
            "commits_pulled": len(result.commits),
            "prs_pulled": len(result.prs),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {e}")


def _get_cached_repo(repo_id: str) -> dict:
    if repo_id not in _REPO_CACHE:
        raise HTTPException(status_code=404, detail="repo_id not found - call /ingest first")
    return _REPO_CACHE[repo_id]


@app.get("/architecture/{repo_id}", response_model=ArchitectureOverview)
def get_architecture(repo_id: str):
    cached = _get_cached_repo(repo_id)
    result = cached["ingest_result"]
    overview = map_architecture(repo_id, result.chunks)
    cached["architecture"] = overview
    return overview


@app.get("/curriculum/{repo_id}", response_model=Curriculum)
def get_curriculum(repo_id: str):
    cached = _get_cached_repo(repo_id)
    overview = cached.get("architecture")
    if overview is None:
        # Curriculum needs the architecture overview as context; generate if missing
        overview = map_architecture(repo_id, cached["ingest_result"].chunks)
        cached["architecture"] = overview

    curriculum = plan_curriculum(repo_id, overview, cached["ingest_result"].chunks)
    cached["curriculum"] = curriculum
    return curriculum


@app.post("/ask", response_model=TutorAnswer)
def ask_tutor(req: TutorQuestion):
    cached = _get_cached_repo(req.repo_id)
    return answer_question(req.repo_id, req.question, cached["commit_lookup"])


@app.get("/quiz/{repo_id}/{step_number}", response_model=QuizQuestion)
def get_quiz_question(repo_id: str, step_number: int):
    cached = _get_cached_repo(repo_id)
    curriculum = cached.get("curriculum")
    if curriculum is None:
        raise HTTPException(status_code=400, detail="call /curriculum first")

    step = next((s for s in curriculum.steps if s.step_number == step_number), None)
    if step is None:
        raise HTTPException(status_code=404, detail=f"step {step_number} not found")

    # Generate and cache question so we can grade against its expected_points
    question_obj = generate_quiz_question(step)
    if "quiz_questions" not in cached:
        cached["quiz_questions"] = {}
    cached["quiz_questions"][step_number] = question_obj
    return question_obj


@app.post("/quiz/submit", response_model=QuizGrade)
def submit_quiz_answer(sub: QuizSubmission):
    cached = _get_cached_repo(sub.repo_id)  # validates repo exists
    
    # Try retrieving the expected points for the cached question
    expected_points = []
    if "quiz_questions" in cached and sub.step_number in cached["quiz_questions"]:
        expected_points = cached["quiz_questions"][sub.step_number].expected_points
        
    return grade_answer(sub.question, expected_points, sub.user_answer)