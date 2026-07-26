"""
Sequences a step-by-step learning path through the codebase: what to
read first, in what order, based on dependency structure and complexity.
Takes the Architecture Mapper's output as context so the path aligns
with the real module structure.
"""
from __future__ import annotations
import json
import re
from app.models import ArchitectureOverview, CodeChunk, Curriculum, LearningStep
from app.agents.claude_client import call_claude

SYSTEM_PROMPT = """You are an expert software mentor designing a guided learning \
path for a new engineer joining this codebase. Given the architecture overview \
and module list, produce an ordered sequence of 4-8 learning steps, starting \
from the most foundational/entry-point code and progressing toward more complex \
or peripheral logic. Each step should reference real file paths.

Respond ONLY with valid JSON in this exact shape, no markdown fences, no prose \
outside the JSON:
{
  "steps": [
    {
      "step_number": 1,
      "title": "...",
      "file_paths": ["..."],
      "rationale": "why this comes at this point in the path",
      "concepts": ["key concept 1", "key concept 2"]
    }
  ]
}
"""


def _extract_json(text: str) -> dict:
    cleaned = re.sub(r"^```json\s*|\s*```$", "", text.strip())
    return json.loads(cleaned)


def plan_curriculum(repo_id: str, overview: ArchitectureOverview, chunks: list[CodeChunk]) -> Curriculum:
    file_list = sorted({c.file_path for c in chunks})
    prompt = (
        f"Architecture overview:\n{overview.written_overview}\n\n"
        f"Modules:\n" + "\n".join(f"- {m.name} ({m.path}): {m.summary}" for m in overview.modules) + "\n\n"
        f"All files in repo:\n" + "\n".join(file_list[:80])
    )

    raw = call_claude(prompt, system=SYSTEM_PROMPT, max_tokens=2500)

    try:
        data = _extract_json(raw)
        steps = [LearningStep(**s) for s in data.get("steps", [])]
    except (json.JSONDecodeError, TypeError):
        # Degrade gracefully: one fallback step rather than crashing
        steps = [LearningStep(
            step_number=1,
            title="Explore the codebase",
            file_paths=file_list[:5],
            rationale="Automatic curriculum generation failed; start by browsing these files.",
            concepts=[],
        )]

    return Curriculum(repo_id=repo_id, steps=steps)