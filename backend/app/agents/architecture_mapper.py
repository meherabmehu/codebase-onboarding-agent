"""
Analyzes module/file relationships across the ingested repo and produces
a high-level written overview plus a Mermaid diagram of the structure.
Uses the strong Claude model since this requires genuine synthesis
across many files, not just retrieval.
"""
from __future__ import annotations
import json
import re
from collections import defaultdict
from app.models import CodeChunk, ArchitectureOverview, ModuleNode
from app.agents.claude_client import call_claude

SYSTEM_PROMPT = """You are an expert software architect helping a new engineer \
understand an unfamiliar codebase. You will be given a list of files and the \
functions/classes each one contains. Produce:
1. A written architecture overview (3-5 paragraphs) explaining the system's \
   major components and how they fit together.
2. A list of top-level modules (group related files together sensibly), each \
   with a short summary and which other modules it depends on.
3. A Mermaid flowchart (graph TD syntax) showing module-level dependencies.

Respond ONLY with valid JSON in this exact shape, no markdown fences, no prose \
outside the JSON:
{
  "written_overview": "...",
  "modules": [
    {"name": "...", "path": "...", "depends_on": ["..."], "summary": "..."}
  ],
  "mermaid_diagram": "graph TD\\n  A[...] --> B[...]"
}
"""


def _summarize_structure(chunks: list[CodeChunk], max_files: int = 60) -> str:
    """
    Build a compact file->symbols listing to keep the prompt bounded even
    for large repos. Caps at max_files to control token usage/cost.
    """
    by_file: dict[str, list[str]] = defaultdict(list)
    for chunk in chunks:
        by_file[chunk.file_path].append(f"{chunk.symbol_type}:{chunk.symbol_name}")

    lines = []
    for path, symbols in list(by_file.items())[:max_files]:
        lines.append(f"{path}: {', '.join(symbols[:15])}")
    return "\n".join(lines)


def _extract_json(text: str) -> dict:
    """Claude sometimes wraps JSON in fences despite instructions; strip if present."""
    cleaned = re.sub(r"^```json\s*|\s*```$", "", text.strip())
    return json.loads(cleaned)


def map_architecture(repo_id: str, chunks: list[CodeChunk]) -> ArchitectureOverview:
    structure = _summarize_structure(chunks)
    prompt = f"Codebase structure (file: symbols):\n\n{structure}"

    raw = call_claude(prompt, system=SYSTEM_PROMPT, max_tokens=3000)

    try:
        data = _extract_json(raw)
    except json.JSONDecodeError:
        # Degrade gracefully: return the raw text as the overview rather than crashing
        return ArchitectureOverview(
            repo_id=repo_id,
            written_overview=raw,
            modules=[],
            mermaid_diagram="graph TD\n  A[Parsing failed]",
        )

    modules = [ModuleNode(**m) for m in data.get("modules", [])]
    return ArchitectureOverview(
        repo_id=repo_id,
        written_overview=data.get("written_overview", ""),
        modules=modules,
        mermaid_diagram=data.get("mermaid_diagram", ""),
    )