"""LLM explanation layer.

In 2019 the app returned the five nearest reviews and stopped there. The 2026
version always hands those candidates to an LLM that streams a short
sommelier-style note explaining *why* each wine matches the request.

Any OpenAI-compatible endpoint works (OpenAI, Together, Groq, a local Ollama /
vLLM server) via ``LLM_BASE_URL``.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

from openai import OpenAI

from .config import get_settings

_SYSTEM = (
    "You are a concise, friendly sommelier. Given a person's request and a list "
    "of candidate wines (each with a description and metadata), recommend the "
    "best matches. For each wine give one short sentence on why it fits. Be "
    "honest about trade-offs. Do not invent wines outside the candidate list."
)


def _client() -> OpenAI:
    settings = get_settings()
    kwargs: dict[str, str] = {}
    if settings.llm_api_key:
        kwargs["api_key"] = settings.llm_api_key
    if settings.llm_base_url:
        kwargs["base_url"] = settings.llm_base_url
    return OpenAI(**kwargs)


def is_configured() -> bool:
    settings = get_settings()
    return bool(settings.llm_api_key)


def _candidate_payload(wines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "title": w.get("title"),
            "variety": w.get("variety"),
            "country": w.get("country"),
            "price": w.get("price"),
            "points": w.get("points"),
            "description": w.get("description"),
        }
        for w in wines
    ]


def _messages(query: str, wines: list[dict[str, Any]]) -> list[dict[str, str]]:
    user = (
        f"Request: {query}\n\n"
        f"Candidate wines (JSON):\n{json.dumps(_candidate_payload(wines), ensure_ascii=False)}"
    )
    return [
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": user},
    ]


def explain(query: str, wines: list[dict[str, Any]]) -> str | None:
    """Return a short natural-language recommendation, or None if disabled."""
    if not is_configured():
        raise RuntimeError("LLM_API_KEY is required for recommendations")

    settings = get_settings()
    resp = _client().chat.completions.create(
        model=settings.llm_model,
        messages=_messages(query, wines),
        max_completion_tokens=400,
    )
    return resp.choices[0].message.content


def stream_explain(query: str, wines: list[dict[str, Any]]) -> Iterator[str]:
    """Yield a recommendation note incrementally from the OpenAI stream."""
    if not is_configured():
        raise RuntimeError("LLM_API_KEY is required for streaming recommendations")

    settings = get_settings()
    stream = _client().chat.completions.create(
        model=settings.llm_model,
        messages=_messages(query, wines),
        max_completion_tokens=400,
        stream=True,
    )
    for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta
