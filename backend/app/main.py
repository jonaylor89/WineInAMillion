"""FastAPI application exposing the wine recommender."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
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
    explain: bool = Field(default=True, description="Ask the LLM for a recommendation note")


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


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "version": __version__,
        "table_ready": store.table_exists(),
        "llm_enabled": llm.is_enabled(),
        "embedding_model": settings.embedding_model,
    }


@app.post("/search", response_model=SearchResponse)
def search(req: SearchRequest) -> SearchResponse:
    if not store.table_exists():
        raise HTTPException(
            status_code=503,
            detail="Vector table not found. Run the ingest job first (python -m app.ingest).",
        )

    vector = embeddings.embed_query(req.query)
    wines = store.search(vector, k=req.k)

    recommendation = None
    if req.explain:
        try:
            recommendation = llm.explain(req.query, wines)
        except Exception:  # noqa: BLE001 - LLM is best-effort, never fail search
            recommendation = None

    return SearchResponse(
        query=req.query,
        wines=[Wine(**w) for w in wines],
        recommendation=recommendation,
    )
