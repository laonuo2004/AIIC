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

    assert "全部使用中文" in first_question
    assert "审稿人式" in first_question
    assert "只问一个问题" in first_question
    assert "优先用一句话" in first_question

    assert "全部使用中文" in answer_feedback
    assert "缺少证据" in answer_feedback
    assert "老师视角" in answer_feedback
    assert "节奏" in answer_feedback
    assert "可以直接复述" in answer_feedback
    assert "实现细节" in answer_feedback
    assert "模块设计理由" in answer_feedback
    assert "实验证据" in answer_feedback
    assert "相关方法对比" in answer_feedback
    assert "失败案例" in answer_feedback
    assert "个人贡献边界" in answer_feedback
    assert "只追问一个问题" in answer_feedback
    assert "follow_up_question" in answer_feedback

    assert "全部使用中文" in final_report
    assert "通过风险" in final_report
    assert "24 小时训练计划" in final_report
    assert "大概率通过 / 边缘 / 高风险" in final_report
    assert "脆弱追问点" in final_report
    assert "边缘" in final_report
    assert "高风险" in final_report


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
