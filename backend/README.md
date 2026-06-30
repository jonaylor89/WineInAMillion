# Wine in a Million — Backend (2026)

A FastAPI service that turns a free-text craving ("something bold and earthy to
go with steak") into wine recommendations, backed by a **LanceDB** table that
lives directly on **object storage** (MinIO locally, S3 / GCS in production).

## Why this design

The original 2019 project fit a scikit-learn `NearestNeighbors` model in memory
and shuttled CSV embeddings around S3 via SageMaker jobs. In 2026 we instead:

- store embeddings + metadata in a single **LanceDB** table,
- keep that table **in a cheap blob store** — no vector-DB server to operate,
- embed with a modern small retrieval model (`bge-small-en-v1.5`),
- optionally let an **LLM** explain *why* each wine fits.

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

## Quickstart (MinIO / S3)

```bash
# from the repo root: docker compose up -d minio createbuckets
cp .env.example .env
# in .env set:
#   LANCEDB_URI=s3://wine/lancedb
#   AWS_ENDPOINT=http://localhost:9000
#   AWS_ACCESS_KEY_ID=minioadmin
#   AWS_SECRET_ACCESS_KEY=minioadmin
#   AWS_ALLOW_HTTP=true
uv run python -m app.ingest --csv data/winemag-data-130k-v2.csv --overwrite
uv run uvicorn app.main:app --reload
```

To target real S3, drop `AWS_ENDPOINT`/`AWS_ALLOW_HTTP` and use IAM creds. For
GCS, set `LANCEDB_URI=gs://...` and `GOOGLE_SERVICE_ACCOUNT`.

## API

```bash
curl -s localhost:8000/health | jq

curl -s localhost:8000/search -H 'content-type: application/json' \
  -d '{"query": "bold earthy red for steak night", "k": 5}' | jq
```

`POST /search` → `{ query, wines: [{title, variety, price, points, similarity, ...}], recommendation }`

The `recommendation` field is populated only when `LLM_ENABLED=true` and an
`LLM_API_KEY` is set; otherwise you still get the ranked wines.

## Enabling the LLM layer

Set in `.env`:

```
LLM_ENABLED=true
LLM_API_KEY=sk-...
LLM_MODEL=gpt-4o-mini
# any OpenAI-compatible endpoint also works:
# LLM_BASE_URL=https://api.groq.com/openai/v1
```

## Tests

```bash
uv run --extra dev pytest
uv run --extra dev ruff check .
```
