"""Optional LLM explanation layer.

In 2019 the app returned the five nearest reviews and stopped there. The 2026
version can hand those candidates to an LLM that writes a short sommelier-style
note explaining *why* each wine matches the request. It is fully optional: if
``LLM_ENABLED`` is false (or no API key is set) the API still returns ranked
wines, just without the prose.

Any OpenAI-compatible endpoint works (OpenAI, Together, Groq, a local Ollama /
vLLM server) via ``LLM_BASE_URL``.
"""

from __future__ import annotations

import json
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
    return OpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)


def is_enabled() -> bool:
    settings = get_settings()
    return settings.llm_enabled and bool(settings.llm_api_key)


def explain(query: str, wines: list[dict[str, Any]]) -> str | None:
    """Return a short natural-language recommendation, or None if disabled."""
    if not is_enabled():
        return None

    settings = get_settings()
    candidates = [
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
    user = (
        f"Request: {query}\n\n"
        f"Candidate wines (JSON):\n{json.dumps(candidates, ensure_ascii=False)}"
    )
    resp = _client().chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": user},
        ],
        temperature=0.4,
        max_tokens=400,
    )
    return resp.choices[0].message.content
