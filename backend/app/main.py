"""FastAPI application exposing the wine recommender."""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from . import __version__, embeddings, llm, store
from .config import get_settings

settings = get_settings()

app = FastAPI(
    title="Wine in a Million",
    version=__version__,
    description="Semantic + LLM-powered wine recommender backed by LanceDB.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list(),
    allow_methods=["*"],
    allow_headers=["*"],
)


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Free-text description of the wine you want")
    k: int = Field(default=settings.default_k, ge=1, le=25)


class Wine(BaseModel):
    title: str | None = None
    variety: str | None = None
    winery: str | None = None
    country: str | None = None
    province: str | None = None
    price: float | None = None
    points: int | None = None
    description: str | None = None
    similarity: float | None = None


class SearchResponse(BaseModel):
    query: str
    wines: list[Wine]
    recommendation: str | None = None


def _event(event_type: str, **payload: Any) -> str:
    return json.dumps({"type": event_type, **payload}, ensure_ascii=False) + "\n"


@app.get("/health")
def health(warm: bool = False) -> dict[str, Any]:
    model_ready = False
    if warm:
        # Intentionally do a tiny embedding so Cloud Run cold starts pay the
        # model-load cost before the user submits their first real query.
        embeddings.embed_query("warm up semantic wine search")
        model_ready = True

    return {
        "status": "ok",
        "version": __version__,
        "table_ready": store.table_exists(),
        "model_ready": model_ready,
        "llm_configured": llm.is_configured(),
        "embedding_model": settings.embedding_model,
    }


def _ensure_table() -> None:
    if not store.table_exists():
        raise HTTPException(
            status_code=503,
            detail="Vector table not found. Run the ingest job first (python -m app.ingest).",
        )


@app.post("/search", response_model=SearchResponse)
def search(req: SearchRequest) -> SearchResponse:
    _ensure_table()

    vector = embeddings.embed_query(req.query)
    wines = store.search(vector, k=req.k)

    if not llm.is_configured():
        raise HTTPException(status_code=500, detail="LLM_API_KEY is required")
    recommendation = llm.explain(req.query, wines)

    return SearchResponse(
        query=req.query,
        wines=[Wine(**w) for w in wines],
        recommendation=recommendation,
    )


def _search_stream(req: SearchRequest) -> Iterator[str]:
    yield _event("status", message="Embedding your request…")
    vector = embeddings.embed_query(req.query)

    yield _event("status", message="Searching the LanceDB wine index…")
    wines = store.search(vector, k=req.k)
    yield _event("wines", wines=wines)

    yield _event("status", message="Writing the sommelier note…")
    try:
        for delta in llm.stream_explain(req.query, wines):
            yield _event("recommendation_delta", delta=delta)
        yield _event("recommendation_done")
    except Exception as exc:  # noqa: BLE001 - stream structured errors, don't crash nginx
        yield _event("recommendation_error", message=str(exc))
    yield _event("done")


@app.post("/search/stream")
def search_stream(req: SearchRequest) -> StreamingResponse:
    _ensure_table()
    if not llm.is_configured():
        raise HTTPException(status_code=500, detail="LLM_API_KEY is required")
    return StreamingResponse(_search_stream(req), media_type="application/x-ndjson")
