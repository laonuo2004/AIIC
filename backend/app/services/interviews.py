import base64
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from app.core.config import get_settings
from app.models.entities import Attachment
from app.services.llm import complete_llm_response

try:
    import fitz
except ImportError:  # pragma: no cover - exercised only when optional package is absent
    class _MissingFitz:
        def open(self, *_: object, **__: object) -> object:
            raise RuntimeError("PDF processing is not installed.")

    fitz = _MissingFitz()

PROMPT_DIR = Path(__file__).resolve().parents[1] / "prompts"
PDF_PAGE_LIMIT: int | None = None


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


def _cdata(text: str) -> str:
    return text.replace("]]>", "]]]]><![CDATA[>")


def _image_content(mime_type: str, content: bytes) -> dict[str, object]:
    encoded = base64.b64encode(content).decode("ascii")
    return {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{encoded}"}}


def _ocr_png(png_bytes: bytes) -> str:
    try:
        result = subprocess.run(
            ["tesseract", "stdin", "stdout", "-l", "eng+chi_sim"],
            input=png_bytes,
            capture_output=True,
            check=False,
            timeout=15,
        )
        if result.returncode != 0:
            return ""
        return result.stdout.decode("utf-8", errors="ignore").strip()
    except HTTPException:
        raise
    except Exception:
        return ""


def build_interview_attachment_context(
    attachments: list[Attachment] | None,
) -> tuple[str, list[dict[str, object]]]:
    if not attachments:
        return "", []

    text_blocks: list[str] = []
    images: list[dict[str, object]] = []
    page_limit = PDF_PAGE_LIMIT or get_settings().max_pdf_pages_per_attachment

    for attachment in attachments:
        path = Path(attachment.stored_path)
        if attachment.kind == "text":
            text = path.read_text(encoding="utf-8")
            text_blocks.append(
                "\n".join(
                    [
                        f'<candidate_attachment type="text" filename="{attachment.original_name}">',
                        f"  <![CDATA[{_cdata(text)}]]>",
                        "</candidate_attachment>",
                    ]
                )
            )
        elif attachment.kind == "image":
            text_blocks.append(
                f'<candidate_attachment type="image" filename="{attachment.original_name}" '
                f'mime="{attachment.mime_type}">attached as image input</candidate_attachment>'
            )
            images.append(_image_content(attachment.mime_type, path.read_bytes()))
        elif attachment.kind == "pdf":
            document = fitz.open(str(path))
            try:
                page_count = int(document.page_count)
                if page_count > page_limit:
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"PDF attachments are limited to {page_limit} pages. "
                            "Please split the file or upload the key pages."
                        ),
                    )
                page_blocks = [
                    f'<candidate_attachment type="pdf" filename="{attachment.original_name}">'
                ]
                for index in range(page_count):
                    page = document.load_page(index)
                    page_text = page.get_text("text").strip()
                    pixmap = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
                    png_bytes = pixmap.tobytes("png")
                    if len(page_text) < 40:
                        page_text = _ocr_png(png_bytes) or page_text
                    images.append(_image_content("image/png", png_bytes))
                    page_blocks.extend(
                        [
                            f'  <page number="{index + 1}">',
                            f"    <ocr_text><![CDATA[{_cdata(page_text)}]]></ocr_text>",
                            (
                                "    <page_image>attached as image input: "
                                f"{attachment.original_name} page {index + 1}</page_image>"
                            ),
                            "  </page>",
                        ]
                    )
                page_blocks.append("</candidate_attachment>")
                text_blocks.append("\n".join(page_blocks))
            finally:
                document.close()

    return "\n\n".join(text_blocks), images


def _payload_text(payload: dict[str, Any], attachment_xml: str) -> str:
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if attachment_xml:
        text += "\n\n<candidate_attachments>\n" + attachment_xml + "\n</candidate_attachments>"
    return text


def _user_content(payload: dict[str, Any], attachments: list[Attachment] | None) -> object:
    attachment_xml, image_parts = build_interview_attachment_context(attachments)
    text = _payload_text(payload, attachment_xml)
    if not image_parts:
        return text
    return [{"type": "text", "text": text}, *image_parts]


def _repair_json(raw_text: str, *, model: str, schema_hint: str) -> dict[str, Any]:
    settings = get_settings()
    repaired = complete_llm_response(
        [
            {
                "role": "system",
                "content": (
                    "Repair the user's text into valid JSON only. Preserve the intended values. "
                    f"Use this schema: {schema_hint}"
                ),
            },
            {"role": "user", "content": raw_text},
        ],
        model=model,
        api_key=settings.openrouter_api_key,
    )
    return _json_from_text(repaired)


def _complete_json(
    prompt_name: str,
    payload: dict[str, Any],
    *,
    model: str,
    attachments: list[Attachment] | None = None,
    repair_schema: str = "JSON object",
) -> tuple[dict[str, Any], str]:
    settings = get_settings()
    raw_text = complete_llm_response(
        [
            {"role": "system", "content": _load_prompt(prompt_name)},
            {
                "role": "user",
                "content": _user_content(payload, attachments),
            },
        ],
        model=model,
        api_key=settings.openrouter_api_key,
    )
    try:
        return _json_from_text(raw_text), raw_text
    except HTTPException:
        raise
    except Exception:
        return _repair_json(raw_text, model=model, schema_hint=repair_schema), raw_text


def _safe_score(value: object) -> int:
    if isinstance(value, int | float):
        return max(1, min(10, int(value)))
    return 5


def _safe_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def generate_first_question(
    profile: dict[str, Any],
    attachments: list[Attachment] | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    model = settings.interview_deep_model
    try:
        parsed, raw_text = _complete_json(
            "interview_first_question.md",
            {"profile": profile},
            model=model,
            attachments=attachments,
            repair_schema='{"question":"one interview question"}',
        )
        question = str(parsed.get("question") or "").strip()
        if not question:
            raise ValueError("Missing question")
        return {"question": question, "model_used": model, "raw_text": raw_text}
    except HTTPException:
        raise
    except Exception:
        return {
            "question": "What was your personal contribution to your most relevant project?",
            "model_used": model,
            "raw_text": None,
        }


def evaluate_answer_and_follow_up(
    *,
    profile: dict[str, Any],
    question: str,
    answer: str,
    previous_turns: list[dict[str, Any]],
    attachments: list[Attachment] | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    model = settings.interview_feedback_model
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
            attachments=attachments,
            repair_schema=(
                '{"strengths":["specific strength"],"weaknesses":["specific weakness"],'
                '"score":1,"advice":"actionable advice",'
                '"follow_up_question":"one adaptive follow-up question"}'
            ),
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
    except Exception:
        return {
            "feedback": {
                "strengths": ["You provided enough context to continue the interview."],
                "weaknesses": ["The answer needs clearer evidence, contribution, or metrics."],
                "score": 5,
                "advice": "Retry with a concise answer that states your role, method, and result.",
            },
            "follow_up_question": fallback_question,
            "model_used": model,
            "raw_text": None,
        }


def generate_final_report(
    *,
    profile: dict[str, Any],
    turns: list[dict[str, Any]],
    attachments: list[Attachment] | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    model = settings.interview_deep_model
    try:
        parsed, raw_text = _complete_json(
            "interview_final_report.md",
            {"profile": profile, "turns": turns},
            model=model,
            attachments=attachments,
            repair_schema=(
                '{"final_report":{"overall_score":1,"summary":"summary",'
                '"strengths":["what worked"],"weaknesses":["what to fix"],'
                '"next_steps":["practice action"]}}'
            ),
        )
        report = (
            parsed.get("final_report")
            if isinstance(parsed.get("final_report"), dict)
            else parsed
        )
        return {"report": report, "model_used": model, "raw_text": raw_text}
    except Exception:
        return {
            "report": {
                "overall_score": 5,
                "summary": (
                    "The final report is temporarily unavailable, "
                    "but the turn feedback remains available."
                ),
                "weaknesses": ["Try finishing again after adding at least one answered turn."],
                "next_steps": ["Review each turn feedback and rerun the final report."],
            },
            "model_used": model,
            "raw_text": None,
        }
