"""
LLM client wrapper shared by all four agents. Backed by Groq's free API
(fast open models like Llama 3.3), since it's genuinely accessible
without billing setup. Function name `call_claude` is kept as the
stable interface so agents don't need to change if you swap providers.
"""
from __future__ import annotations
from groq import Groq
from tenacity import retry, stop_after_attempt, wait_exponential
from app.config import settings

_client: Groq | None = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=settings.groq_api_key)
    return _client


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def call_claude(prompt: str, system: str = "", model: str | None = None, max_tokens: int = 2000) -> str:
    """Single-turn completion via Groq."""
    client = _get_client()
    model = model or settings.groq_model

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content