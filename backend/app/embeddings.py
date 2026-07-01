"""Embedding model wrapper.

We swap the 2019 ``all-MiniLM-L6-v2`` for a modern small retrieval model
(``bge-small-en-v1.5`` by default). It is still tiny and CPU-friendly, but
ranks far higher on MTEB. The model is loaded lazily and cached for reuse.
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer

from .config import get_settings


@lru_cache
def get_model() -> SentenceTransformer:
    settings = get_settings()
    token = settings.huggingface_token or settings.hf_token
    kwargs = {"token": token} if token and not settings.embedding_model.startswith("/") else {}
    return SentenceTransformer(settings.embedding_model, **kwargs)


def embed_documents(texts: list[str], batch_size: int = 64) -> np.ndarray:
    """Embed wine descriptions for storage. Returns L2-normalized vectors."""
    model = get_model()
    return model.encode(
        texts,
        batch_size=batch_size,
        normalize_embeddings=True,
        show_progress_bar=False,
    )


def embed_query(text: str) -> list[float]:
    """Embed a user query with the retrieval instruction prefix."""
    settings = get_settings()
    model = get_model()
    vector = model.encode(
        settings.query_instruction + text,
        normalize_embeddings=True,
    )
    return vector.tolist()
