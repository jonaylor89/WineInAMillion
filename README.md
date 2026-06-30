# Wine in a Million

A natural-language wine recommender: describe what you want ("bold and earthy
for steak night") and get the closest matches from 130k wine reviews — with an
optional LLM "sommelier's note" explaining *why* each one fits.

Authors: [Zephyr](https://github.com/JZHeadley) and [Johannes](https://jonaylor.xyz)

[Blog Post](https://www.jonaylor.com/blog/create-a-wine-recommender)

---

## Architecture (2026 rewrite)

```
   query ──▶ FastAPI ──▶ bge-small embedding ──▶ LanceDB ANN search ──▶ wines
                │                                    │                    │
                │                              (Lance files in            ▼
                │                               MinIO / S3 / GCS)   optional LLM note
                ▼
          Vite + React 19 UI
```

| Layer        | 2019                                   | 2026                                                   |
| ------------ | -------------------------------------- | ------------------------------------------------------ |
| Embeddings   | `all-MiniLM-L6-v2` via SageMaker job   | `bge-small-en-v1.5` (`backend/app/embeddings.py`)      |
| Vector index | scikit-learn `NearestNeighbors` in RAM | **LanceDB** ANN over object storage (`store.py`)       |
| Storage      | `embeddings.csv.gz` shuttled to S3     | One LanceDB table in a **cheap blob store**            |
| Serving      | SageMaker endpoints + `boto3`          | **FastAPI** container (`backend/app/main.py`)          |
| LLM          | none                                   | optional sommelier note (`llm.py`)                     |
| Frontend     | Create React App, class components, JS | **Vite + React 19 + TypeScript** (`frontend/`)         |
| Infra        | SageMaker notebooks, manual S3         | **docker-compose** + MinIO, env-driven config          |

### Why LanceDB on a blob store

LanceDB runs approximate-nearest-neighbour search directly against its columnar
Lance files. Point it at a bucket and the table *is* the data in object
storage — no vector-DB server to run or pay for. The same code targets:

- **MinIO** locally (free, S3-compatible) — `s3://wine/lancedb` + `AWS_ENDPOINT`
- **S3** in production — `s3://...` with IAM creds
- **GCS** — `gs://...` with a service account

Object storage is the cheapest durable option, which is exactly what an
embedding index wants.

## Quickstart (one command, local MinIO)

```bash
# 1. download the dataset (Kaggle: zynicide/wine-reviews)
#    -> backend/data/winemag-data-130k-v2.csv

# 2. bring up MinIO + create the bucket
docker compose up -d minio createbuckets

# 3. embed + load the table into the bucket (first run downloads the model)
docker compose run --rm backend \
  uv run python -m app.ingest --csv /data/winemag-data-130k-v2.csv --overwrite

# 4. run the API + UI
docker compose up backend frontend
# UI:  http://localhost:5173
# API: http://localhost:8000/docs
# MinIO console: http://localhost:9001  (minioadmin / minioadmin)
```

To run pieces directly without Docker, see [`backend/README.md`](backend/README.md)
and [`frontend/README.md`](frontend/README.md).

## Deploy on Google Cloud

The recommended deployment is Cloud Run + GCS:

- FastAPI backend as a Cloud Run service
- LanceDB table in a GCS bucket
- ingestion as a Cloud Run Job
- Docker images in Artifact Registry
- frontend as static files on GCS / Firebase Hosting / Cloudflare Pages

Terraform and a deployment script live in [`infra/gcp/`](infra/gcp/):

```bash
PROJECT_ID=your-gcp-project \
DATASET=backend/data/winemag-data-130k-v2.csv \
./scripts/deploy-gcp.sh
```

See [`infra/gcp/README.md`](infra/gcp/README.md) for the full step-by-step.

## Repository layout

```
backend/    FastAPI service, embeddings, LanceDB store, ingest job (uv)
frontend/   Vite + React 19 + TypeScript client
notebooks/  Original 2019 SageMaker notebook + scripts (kept for reference)
docker-compose.yml   MinIO + backend + frontend for local dev
```

## The original 2019 approach

The first version trained on AWS SageMaker: one job embedded the reviews and
wrote `embeddings.csv.gz` to S3, a second fit a scikit-learn `NearestNeighbors`
model, and inference ran on SageMaker endpoints. That notebook and its scripts
still live in [`notebooks/`](notebooks/) for comparison with the rewrite.
