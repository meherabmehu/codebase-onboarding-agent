"""
Creates short comprehension-check questions for a learning-path step,
and grades the user's free-text answers against expected key points.
Uses the fast model config since grading is a lighter-weight task than
architecture mapping or tutoring (though Groq's llama model is used for
both currently - see claude_client.py).

Features an advanced, adaptive dynamic quiz generator that constructs
lesson-check questions based on the student's actual active chat conversation topics.
"""
from __future__ import annotations
import json
import re
from app.models import LearningStep, QuizQuestion, QuizGrade
from app.agents.claude_client import call_claude

GENERATE_SYSTEM_PROMPT = """You are creating a short comprehension check for a \
learning-path step in a codebase tutorial. Given the step's title, files, and \
key concepts, write ONE open-ended question that tests whether the learner \
understood the *purpose* of this code, not just trivia about syntax.

ADAPTIVE RULE: If a recent conversation log is provided, you must formulate a \
comprehension question that is directly based on the technical topics and design \
decisions they just discussed in their chat! This helps reinforce what they just learned.

Respond ONLY with valid JSON in this exact shape, no markdown fences, no prose \
outside the JSON:
{
  "question": "...",
  "expected_points": ["key point 1 a correct answer should mention", "key point 2"]
}
"""

GRADE_SYSTEM_PROMPT = """You are grading a learner's free-text answer to a \
comprehension question about a codebase. Compare their answer against the \
expected key points. Be encouraging but honest - partial credit is fine.

Respond ONLY with valid JSON in this exact shape, no markdown fences, no prose \
outside the JSON:
{
  "score": 0.75,
  "feedback": "specific, constructive feedback for the learner",
  "passed": true
}
"score" is 0.0-1.0. "passed" should be true if score >= 0.6.
"""


def _extract_json(text: str) -> dict:
    cleaned = re.sub(r"^```json\s*|\s*```$", "", text.strip())
    return json.loads(cleaned)


def generate_quiz_question(step: LearningStep, chat_history: list[dict] | None = None) -> QuizQuestion:
    prompt = (
        f"Step: {step.title}\n"
        f"Files: {', '.join(step.file_paths)}\n"
        f"Concepts: {', '.join(step.concepts)}\n"
        f"Rationale: {step.rationale}"
    )

    # If active chat history is present, inject it to create a personalized question!
    if chat_history:
        chat_context = "\n".join([f"- {msg['role'].upper()}: {msg['content']}" for msg in chat_history[-6:]])
        prompt += f"\n\nRecent student conversation history:\n{chat_context}\n\nTask: Design a question testing their grasp of these discussed topics."

    raw = call_claude(prompt, system=GENERATE_SYSTEM_PROMPT, max_tokens=500)

    try:
        data = _extract_json(raw)
        return QuizQuestion(
            step_number=step.step_number,
            question=data.get("question", raw),
            expected_points=data.get("expected_points", []),
        )
    except (json.JSONDecodeError, TypeError):
        # Fallback question based on conversation themes if present
        if chat_history and len(chat_history) > 0:
            last_msg = chat_history[-1]["content"]
            return QuizQuestion(
                step_number=step.step_number,
                question=f"Explain what we just learned about this topic: '{last_msg[:60]}...' and how it connects to {', '.join(step.file_paths)}.",
                expected_points=step.concepts,
            )
            
        return QuizQuestion(
            step_number=step.step_number,
            question=f"In your own words, explain the purpose of {', '.join(step.file_paths)}.",
            expected_points=step.concepts,
        )


def grade_answer(question: str, expected_points: list[str], user_answer: str) -> QuizGrade:
    prompt = (
        f"Question: {question}\n"
        f"Expected key points: {', '.join(expected_points)}\n"
        f"Learner's answer: {user_answer}"
    )

    raw = call_claude(prompt, system=GRADE_SYSTEM_PROMPT, max_tokens=500)

    try:
        data = _extract_json(raw)
        score = float(data.get("score", 0.0))
        return QuizGrade(
            score=score,
            feedback=data.get("feedback", raw),
            passed=data.get("passed", score >= 0.6),
        )
    except (json.JSONDecodeError, TypeError, ValueError):
        return QuizGrade(score=0.0, feedback="Grading failed - please try rephrasing your answer.", passed=False)
