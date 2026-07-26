"""
Answers free-text questions about the codebase, retrieving relevant code
+ its linked commit/PR history, then generating an answer that clearly
distinguishes "this is stated in a commit/PR" from "this is my inference
from the code" - the core credibility guardrail for this whole project.
"""
from __future__ import annotations
import json
import re
from app.models import TutorAnswer, Citation
from app.indexer.embeddings import embed_texts
from app.indexer.vector_store import query as vector_query
from app.agents.claude_client import call_claude

SYSTEM_PROMPT = """You are a tutor helping a new engineer understand a codebase, \
answering "why was this built this way" questions. You will be given retrieved \
code chunks, each with linked commit SHAs and PR numbers (which may be empty).

CRITICAL RULE: You must clearly separate what is stated in the retrieved \
commit/PR data from what you are inferring purely from reading the code. \
If a chunk has no linked commits/PRs, or the linked history doesn't actually \
explain the "why", say so explicitly and mark it as inference - do not \
present a guess as if it were historical fact.

Respond ONLY with valid JSON in this exact shape, no markdown fences, no prose \
outside the JSON:
{
  "answer": "the answer text, written for a new engineer",
  "citations": [
    {"type": "commit", "ref": "sha or PR number", "excerpt": "short relevant excerpt or empty string"},
    {"type": "inference", "ref": "", "excerpt": ""}
  ],
  "grounded": true
}
"grounded" should be true only if at least one citation has type "commit" or "pr".
"""


def _extract_json(text: str) -> dict:
    cleaned = re.sub(r"^```json\s*|\s*```$", "", text.strip())
    return json.loads(cleaned)


def answer_question(repo_id: str, question: str, commit_lookup: dict[str, str] | None = None) -> TutorAnswer:
    """
    commit_lookup: optional {sha: commit_message} map so retrieved chunks'
    linked commits can be shown with their actual message text, not just SHAs.
    """
    commit_lookup = commit_lookup or {}

    query_embedding = embed_texts([question], input_type="query")[0]
    hits = vector_query(repo_id, query_embedding, top_k=5)

    context_blocks = []
    for h in hits:
        commit_msgs = [f"{sha}: {commit_lookup.get(sha, '(message unavailable)')}"
                       for sha in h["linked_commit_shas"][:3]]
        block = (
            f"File: {h['file_path']}\n"
            f"Symbol: {h['symbol_name']} ({h['symbol_type']})\n"
            f"Code:\n{h['source'][:1000]}\n"
            f"Linked commits: {commit_msgs if commit_msgs else 'NONE'}\n"
            f"Linked PRs: {h['linked_pr_numbers'] if h['linked_pr_numbers'] else 'NONE'}"
        )
        context_blocks.append(block)

    prompt = f"Question: {question}\n\nRetrieved context:\n\n" + "\n\n---\n\n".join(context_blocks)

    raw = call_claude(prompt, system=SYSTEM_PROMPT, max_tokens=1500)

    try:
        data = _extract_json(raw)
        citations = [Citation(**c) for c in data.get("citations", [])]
        return TutorAnswer(
            answer=data.get("answer", raw),
            citations=citations,
            grounded=data.get("grounded", False),
        )
    except (json.JSONDecodeError, TypeError):
        # Degrade gracefully: raw text, clearly marked as ungrounded
        return TutorAnswer(answer=raw, citations=[Citation(type="inference", ref="")], grounded=False)