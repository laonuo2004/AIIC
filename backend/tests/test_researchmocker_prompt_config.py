from pathlib import Path

from app.core.config import Settings

ROOT = Path(__file__).resolve().parents[2]
PROMPTS = ROOT / "backend" / "app" / "prompts"
PLUS_MODEL = "openrouter/qwen/qwen3.6-plus"


def _prompt(name: str) -> str:
    return (PROMPTS / name).read_text(encoding="utf-8")


def test_interview_prompts_encode_reviewer_style_pressure_contracts():
    first_question = _prompt("interview_first_question.md")
    answer_feedback = _prompt("interview_answer_feedback.md")
    final_report = _prompt("interview_final_report.md")

    assert "reviewer-style" in first_question
    assert "Ask exactly one question." in first_question
    assert "Prefer a single-sentence question." in first_question

    assert "missing evidence" in answer_feedback
    assert "directly reuse" in answer_feedback
    assert "personal contribution" in answer_feedback
    assert "follow_up_question" in answer_feedback

    assert "pass-risk" in final_report
    assert "24-hour training plan" in final_report
    assert "borderline" in final_report
    assert "high risk" in final_report


def test_default_interview_models_are_unified_on_plus():
    settings = Settings(_env_file=None)

    assert settings.interview_deep_model == PLUS_MODEL
    assert settings.interview_fast_model == PLUS_MODEL
    assert settings.interview_feedback_model == PLUS_MODEL


def test_env_example_keeps_interview_model_defaults_in_sync_with_config():
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")

    assert f"INTERVIEW_DEEP_MODEL={PLUS_MODEL}" in env_example
    assert f"INTERVIEW_FAST_MODEL={PLUS_MODEL}" in env_example
    assert f"INTERVIEW_FEEDBACK_MODEL={PLUS_MODEL}" in env_example
