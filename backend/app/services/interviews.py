import json
import re
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.services.llm import complete_llm_response

PROMPT_DIR = Path(__file__).resolve().parents[1] / "prompts"


def _load_prompt(name: str) -> str:
    return (PROMPT_DIR / name).read_text(encoding="utf-8")


def _json_from_text(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if not match:
            raise
        value = json.loads(match.group(0))
    if not isinstance(value, dict):
        raise ValueError("LLM output must be a JSON object")
    return value


def _complete_json(
    prompt_name: str,
    payload: dict[str, Any],
    *,
    model: str,
) -> tuple[dict[str, Any], str]:
    settings = get_settings()
    raw_text = complete_llm_response(
        [
            {"role": "system", "content": _load_prompt(prompt_name)},
            {
                "role": "user",
                "content": json.dumps(payload, ensure_ascii=False, indent=2),
            },
        ],
        model=model,
        api_key=settings.openrouter_api_key,
    )
    return _json_from_text(raw_text), raw_text


def _safe_score(value: object) -> int:
    if isinstance(value, int | float):
        return max(1, min(10, int(value)))
    return 5


def _safe_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def generate_first_question(profile: dict[str, Any]) -> dict[str, Any]:
    settings = get_settings()
    model = settings.interview_deep_model
    try:
        parsed, raw_text = _complete_json(
            "interview_first_question.md",
            {"profile": profile},
            model=model,
        )
        question = str(parsed.get("question") or "").strip()
        if not question:
            raise ValueError("Missing question")
        return {"question": question, "model_used": model, "raw_text": raw_text}
    except Exception:
        return {
            "question": (
                "Start with your most relevant research or project experience. What problem did "
                "you work on, what was your personal contribution, and how did you evaluate it?"
            ),
            "model_used": model,
            "raw_text": None,
        }


def evaluate_answer_and_follow_up(
    *,
    profile: dict[str, Any],
    question: str,
    answer: str,
    previous_turns: list[dict[str, Any]],
) -> dict[str, Any]:
    settings = get_settings()
    model = settings.interview_fast_model
    fallback_question = "Can you make your contribution more concrete with one metric or example?"
    try:
        parsed, raw_text = _complete_json(
            "interview_answer_feedback.md",
            {
                "profile": profile,
                "question": question,
                "answer": answer,
                "previous_turns": previous_turns,
            },
            model=model,
        )
        feedback = {
            "strengths": _safe_string_list(parsed.get("strengths")),
            "weaknesses": _safe_string_list(parsed.get("weaknesses")),
            "score": _safe_score(parsed.get("score")),
            "advice": str(parsed.get("advice") or "").strip()
            or "Make the answer more specific and evidence-backed.",
        }
        follow_up = str(parsed.get("follow_up_question") or "").strip() or fallback_question
        return {
            "feedback": feedback,
            "follow_up_question": follow_up,
            "model_used": model,
            "raw_text": raw_text,
        }
    except Exception as exc:
        return {
            "feedback": {
                "strengths": ["You provided enough context to continue the interview."],
                "weaknesses": ["The automated evaluator could not parse structured feedback."],
                "score": 5,
                "advice": "Retry with a concise answer that states your role, method, and result.",
                "raw_error": str(exc),
            },
            "follow_up_question": fallback_question,
            "model_used": model,
            "raw_text": None,
        }


def generate_final_report(
    *,
    profile: dict[str, Any],
    turns: list[dict[str, Any]],
) -> dict[str, Any]:
    settings = get_settings()
    model = settings.interview_deep_model
    try:
        parsed, raw_text = _complete_json(
            "interview_final_report.md",
            {"profile": profile, "turns": turns},
            model=model,
        )
        report = (
            parsed.get("final_report")
            if isinstance(parsed.get("final_report"), dict)
            else parsed
        )
        return {"report": report, "model_used": model, "raw_text": raw_text}
    except Exception as exc:
        return {
            "report": {
                "overall_score": 5,
                "summary": "The final report generator could not parse the provider response.",
                "weaknesses": ["Try finishing again after adding at least one answered turn."],
                "next_steps": ["Review each turn feedback and rerun the final report."],
                "raw_error": str(exc),
            },
            "model_used": model,
            "raw_text": None,
        }
