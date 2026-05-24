from collections.abc import Iterable
from typing import Any

from litellm import completion

from app.core.config import get_settings


def _chunk_text(chunk: object) -> str:
    try:
        choice = chunk["choices"][0]
        return choice.get("delta", {}).get("content") or ""
    except (KeyError, IndexError, TypeError, AttributeError):
        return ""


def stream_llm_response(
    messages: list[dict[str, Any]],
    *,
    model: str | None = None,
    api_key: str | None = None,
) -> Iterable[str]:
    settings = get_settings()
    stream = completion(
        model=model or settings.litellm_model,
        messages=messages,
        api_key=api_key,
        temperature=settings.litellm_temperature,
        timeout=settings.litellm_timeout_seconds,
        stream=True,
    )
    for chunk in stream:
        text = _chunk_text(chunk)
        if text:
            yield text


def complete_llm_response(
    messages: list[dict[str, Any]],
    *,
    model: str | None = None,
    api_key: str | None = None,
) -> str:
    settings = get_settings()
    response = completion(
        model=model or settings.litellm_model,
        messages=messages,
        api_key=api_key,
        temperature=settings.litellm_temperature,
        timeout=settings.litellm_timeout_seconds,
        stream=False,
    )
    try:
        return response["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError):
        return ""
