from pathlib import Path

import pytest
from fastapi import HTTPException

from app.models.entities import Attachment
from app.services import interviews

PNG_1X1 = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _attachment(
    tmp_path: Path,
    *,
    name: str,
    content: bytes,
    kind: str,
    mime_type: str,
) -> Attachment:
    path = tmp_path / name
    path.write_bytes(content)
    return Attachment(
        id=1,
        user_id=1,
        original_name=name,
        stored_path=str(path),
        mime_type=mime_type,
        size_bytes=len(content),
        kind=kind,
    )


def test_first_question_prompt_wraps_text_attachment_as_xml(tmp_path, monkeypatch):
    attachment = _attachment(
        tmp_path,
        name="notes.md",
        content=b"# Project notes\nUse retrieval metrics.",
        kind="text",
        mime_type="text/markdown",
    )
    captured = {}

    def fake_complete(messages, *, model, api_key):
        captured["messages"] = messages
        captured["model"] = model
        return '{"question":"What metric best supports your retrieval claim?"}'

    monkeypatch.setattr(interviews, "complete_llm_response", fake_complete)

    result = interviews.generate_first_question(
        {"self_introduction": "I work on RAG."},
        attachments=[attachment],
    )

    assert result["question"] == "What metric best supports your retrieval claim?"
    assert captured["model"] == "openrouter/qwen/qwen3.6-plus"
    user_content = captured["messages"][1]["content"]
    assert "<candidate_attachment type=\"text\" filename=\"notes.md\">" in user_content
    assert "<![CDATA[# Project notes\nUse retrieval metrics.]]>" in user_content
    system_prompt = captured["messages"][0]["content"]
    assert "Prefer a single-sentence question." in system_prompt
    assert "Ask only one thing at a time." in system_prompt


def test_first_question_sends_image_attachment_as_multimodal_content(tmp_path, monkeypatch):
    attachment = _attachment(
        tmp_path,
        name="diagram.png",
        content=PNG_1X1,
        kind="image",
        mime_type="image/png",
    )
    captured = {}

    def fake_complete(messages, *, model, api_key):
        captured["messages"] = messages
        return '{"question":"Explain the system diagram."}'

    monkeypatch.setattr(interviews, "complete_llm_response", fake_complete)

    interviews.generate_first_question({"project_experience": "I built this system."}, [attachment])

    user_content = captured["messages"][1]["content"]
    assert user_content[0]["type"] == "text"
    assert 'type="image" filename="diagram.png"' in user_content[0]["text"]
    assert user_content[1]["type"] == "image_url"
    assert user_content[1]["image_url"]["url"].startswith("data:image/png;base64,")


def test_pdf_attachment_page_limit_returns_clear_error(tmp_path, monkeypatch):
    attachment = _attachment(
        tmp_path,
        name="paper.pdf",
        content=b"%PDF-1.4\n",
        kind="pdf",
        mime_type="application/pdf",
    )

    class FakeDocument:
        page_count = 13

        def close(self):
            return None

    monkeypatch.setattr(interviews, "PDF_PAGE_LIMIT", 12)
    monkeypatch.setattr(interviews.fitz, "open", lambda _: FakeDocument())

    with pytest.raises(HTTPException) as exc:
        interviews.build_interview_attachment_context([attachment])

    assert exc.value.status_code == 400
    assert "12 pages" in exc.value.detail


def test_answer_feedback_uses_feedback_model_and_repairs_invalid_json(monkeypatch):
    responses = iter(
        [
            "not json",
            '{"strengths":["Specific role"],"weaknesses":["Needs metrics"],'
            '"score":7,"advice":"Name the benchmark.",'
            '"follow_up_question":"Which benchmark did you use?"}',
        ]
    )
    captured_models = []

    def fake_complete(messages, *, model, api_key):
        captured_models.append(model)
        return next(responses)

    monkeypatch.setattr(interviews, "complete_llm_response", fake_complete)

    result = interviews.evaluate_answer_and_follow_up(
        profile={"target_direction": "AI research"},
        question="What did you build?",
        answer="I built the evaluator.",
        previous_turns=[],
        attachments=[],
    )

    assert captured_models == [
        "openrouter/qwen/qwen3.6-plus",
        "openrouter/qwen/qwen3.6-plus",
    ]
    assert result["feedback"]["score"] == 7
    assert result["follow_up_question"] == "Which benchmark did you use?"
    assert "raw_error" not in result["feedback"]


def test_answer_feedback_prompt_limits_follow_up_question_shape(monkeypatch):
    captured = {}

    def fake_complete(messages, *, model, api_key):
        captured["messages"] = messages
        return (
            '{"strengths":["Specific role"],"weaknesses":["Needs metrics"],'
            '"score":7,"advice":"Name the benchmark.",'
            '"follow_up_question":"Which benchmark did you use?"}'
        )

    monkeypatch.setattr(interviews, "complete_llm_response", fake_complete)

    interviews.evaluate_answer_and_follow_up(
        profile={"target_direction": "AI research"},
        question="What did you build?",
        answer="I built the evaluator.",
        previous_turns=[],
        attachments=[],
    )

    system_prompt = captured["messages"][0]["content"]
    assert "Prefer a single-sentence question." in system_prompt
    assert "Use at most two sentences." in system_prompt
    assert "Ask only one thing at a time." in system_prompt
