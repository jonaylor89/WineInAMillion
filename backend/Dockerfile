# syntax=docker/dockerfile:1.7
# Multi-stage build using uv for fast, reproducible installs.
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS base

ARG EMBEDDING_MODEL_SOURCE=BAAI/bge-small-en-v1.5

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/models/hf-cache \
    SENTENCE_TRANSFORMERS_HOME=/models/sentence-transformers \
    EMBEDDING_MODEL=/models/embedding

WORKDIR /app

# Install dependencies first for better layer caching.
COPY pyproject.toml ./
RUN uv sync --no-dev --no-install-project

# Download and save the embedding model into the image. This removes runtime
# Hugging Face downloads from Cloud Run cold starts and ingestion jobs.
# If HUGGINGFACE_TOKEN is provided to docker build as a BuildKit secret, it is
# used for auth/rate limits without being baked into the image layers.
RUN --mount=type=secret,id=hf_token,required=false \
    if [ -f /run/secrets/hf_token ]; then export HF_TOKEN="$(cat /run/secrets/hf_token)"; fi && \
    uv run python - <<PY
from sentence_transformers import SentenceTransformer
model_name = "${EMBEDDING_MODEL_SOURCE}"
out = "/models/embedding"
print(f"Downloading embedding model {model_name} -> {out}")
SentenceTransformer(model_name).save(out)
PY

COPY app ./app

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
