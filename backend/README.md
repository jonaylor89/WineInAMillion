# Wine in a Million — Backend (2026)

A FastAPI service that turns a free-text craving ("something bold and earthy to
go with steak") into wine recommendations, backed by a **LanceDB** table that
lives directly on **object storage** (MinIO locally, S3 / GCS in production).

## Why this design

The original 2019 project fit a scikit-learn `NearestNeighbors` model in memory
and shuttled CSV embeddings around S3 via SageMaker jobs. In 2026 we instead:

- store embeddings + metadata in a single **LanceDB** table,
- keep that table **in a cheap blob store** — no vector-DB server to operate,
- embed with a modern small retrieval model (`bge-small-en-v1.5`) pre-downloaded into the backend image,
- stream an **LLM** explanation of *why* each wine fits.

LanceDB runs the approximate-nearest-neighbour search directly against the
Lance columnar files in the bucket, so the only thing you pay for is object
storage.

## Quickstart (local, on-disk)

```bash
uv sync
cp .env.example .env                       # defaults to ./data/lancedb
# grab the dataset (Kaggle: zynicide/wine-reviews) -> data/winemag-data-130k-v2.csv
uv run python -m app.ingest --csv data/winemag-data-130k-v2.csv --limit 5000 --overwrite
uv run uvicorn app.main:app --reload
```

## Quickstart (MinIO / Docker dev)

From the repo root:

```bash
cp .env.example .env
make download
make local
```

`make local` starts MinIO, checks whether the LanceDB table exists, creates
embeddings only when needed, and runs the backend with `uvicorn --reload`.

To target real S3, drop `AWS_ENDPOINT`/`AWS_ALLOW_HTTP` and use IAM creds. For
GCS, set `LANCEDB_URI=gs://...` and `GOOGLE_SERVICE_ACCOUNT`.

## API

```bash
curl -s localhost:8000/health | jq

curl -N localhost:8000/search/stream -H 'content-type: application/json' \
  -d '{"query": "bold earthy red for steak night", "k": 5}'
```

`POST /search/stream` returns NDJSON events: status updates, ranked wines, and
streamed `recommendation_delta` chunks from OpenAI.

`LLM_API_KEY` is required; recommendations are not an optional mode.

Set locally:

```
LLM_API_KEY=sk-...
LLM_MODEL=gpt-4o-mini
# OpenAI default is https://api.openai.com/v1, so this can stay blank.
# LLM_BASE_URL=https://api.groq.com/openai/v1
```

## Tests

```bash
uv run --extra dev pytest
uv run --extra dev ruff check .
```
