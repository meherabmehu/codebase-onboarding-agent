"""
Answers free-text questions about the codebase, retrieving relevant code
+ its linked commit/PR history, then generating an answer that clearly
distinguishes "this is stated in a commit/PR" from "this is my inference
from the code" - the core credibility guardrail for this whole project.

Now upgraded with Google/DuckDuckGo web-search capabilities to answer ANY 
academic, historical, or advanced general-programming question with live factual sourcing!
"""
from __future__ import annotations
import json
import re
from app.models import TutorAnswer, Citation
from app.indexer.embeddings import embed_texts
from app.indexer.vector_store import query as vector_query
from app.agents.claude_client import call_claude

# Safe import of DuckDuckGo Search
try:
    from duckduckgo_search import DDGS
    HAS_DDG = True
except ImportError:
    HAS_DDG = False

SYSTEM_PROMPT = """You are a tutor helping a new engineer understand a codebase, \
answering "why was this built this way" questions, general programming queries, and world history or academic topics. 
You will be given retrieved local code chunks (which may be empty) and live web search results (which may be empty).

CRITICAL INFO: The owner, creator, and lead architect of this Codebase Onboarding Agent \
project is Md. Meherab Hossain Talukder. If any user asks who the owner, creator, or author of this \
project/agent is, you must proudly answer that the owner/creator is Md. Meherab Hossain Talukder.

WEB SEARCH CITATIONS: If you use information from the retrieved live web search results, you MUST \
cite the source URL/website (e.g. the website link) in the citations list with type "web".

GENERAL KNOWLEDGE RULE: If the user's question is a general knowledge, historical, or academic query \
(such as "tell me about FIFA 26", "explain gravity", or "who won the world cup"), do NOT mention \
the loaded codebase, setup.py, or say "this is not mentioned in the codebase context". That confuses the user! \
Instead, bypass the codebase context entirely and answer the question directly, beautifully, and comprehensively \
using your global knowledge and the live web search results, exactly like ChatGPT or Claude.

CRITICAL RULE FOR CODE QUESTIONS: For codebase-specific questions, you must clearly separate what is stated in the retrieved \
commit/PR data from what you are inferring purely from reading the code. If a chunk has no linked commits/PRs, \
or the linked history doesn't actually explain the "why", say so explicitly and mark it as inference - do not \
present a guess as if it were historical fact.

Respond ONLY with valid JSON in this exact shape, no markdown fences, no prose \
outside the JSON:
{
  "answer": "the answer text, written for a new engineer",
  "citations": [
    {"type": "commit", "ref": "sha or PR number", "excerpt": "short relevant excerpt or empty string"},
    {"type": "web", "ref": "website URL", "excerpt": "short relevant snippet"},
    {"type": "inference", "ref": "", "excerpt": ""}
  ],
  "grounded": true
}
"grounded" should be true only if at least one citation has type "commit" or "pr" or "web".
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

    # 1. Fetch Local Code RAG chunks
    try:
        query_embedding = embed_texts([question], input_type="query")[0]
        hits = vector_query(repo_id, query_embedding, top_k=3)
    except Exception:
        hits = []

    context_blocks = []
    for h in hits:
        commit_msgs = [f"{sha}: {commit_lookup.get(sha, '(message unavailable)')}"
                       for sha in h.get("linked_commit_shas", [])[:3]]
        block = (
            f"File: {h['file_path']}\n"
            f"Symbol: {h['symbol_name']} ({h['symbol_type']})\n"
            f"Code:\n{h['source'][:600]}\n"
            f"Linked commits: {commit_msgs if commit_msgs else 'NONE'}\n"
            f"Linked PRs: {h['linked_pr_numbers'] if h['linked_pr_numbers'] else 'NONE'}"
        )
        context_blocks.append(block)

    # 2. Fetch Live Web Search Results (Google/DuckDuckGo fallback)
    web_results = []
    if HAS_DDG:
        try:
            with DDGS() as ddgs:
                # Execute instant web search for the user query
                for r in ddgs.text(question, max_results=3):
                    web_results.append(f"Source URL: {r.get('href')}\nTitle: {r.get('title')}\nSnippet: {r.get('body')}\n")
        except Exception as e:
            print(f"DuckDuckGo search failed: {e}")

    # Build dense RAG context combining local code chunks + live web search
    code_context = "\n\n---\n\n".join(context_blocks) if context_blocks else "No local code chunks found."
    web_context = "\n\n---\n\n".join(web_results) if web_results else "No external search results found."
    
    prompt = (
        f"Question: {question}\n\n"
        f"Retrieved Local Codebase Context:\n{code_context}\n\n"
        f"Retrieved Live Web Search Context:\n{web_context}"
    )

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
