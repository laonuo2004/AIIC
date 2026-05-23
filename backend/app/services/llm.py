from collections.abc import Iterable

from litellm import completion

from app.core.config import get_settings


def _chunk_text(chunk: object) -> str:
    try:
        choice = chunk["choices"][0]
        return choice.get("delta", {}).get("content") or ""
    except (KeyError, IndexError, TypeError, AttributeError):
        return ""


def stream_llm_response(messages: list[dict[str, str]]) -> Iterable[str]:
    settings = get_settings()
    stream = completion(
        model=settings.litellm_model,
        messages=messages,
        temperature=settings.litellm_temperature,
        timeout=settings.litellm_timeout_seconds,
        stream=True,
    )
    for chunk in stream:
        text = _chunk_text(chunk)
        if text:
            yield text
