# Wine in a Million

A natural-language wine recommender: describe what you want ("bold and earthy
for steak night") and get the closest matches from 130k wine reviews — with an
streamed LLM "sommelier's note" explaining *why* each one fits.

Authors: [Zephyr](https://github.com/JZHeadley) and [Johannes](https://jonaylor.xyz)

Blog posts:

- [Original SageMaker write-up](https://www.jonaylor.com/blog/create-a-wine-recommender)
- [2026 modernization with LanceDB, Cloud Run, and Cloudflare](https://jonaylor.com/blog/modernizing-a-wine-recommender-with-lancedb/)

---

## Architecture (2026 rewrite)

```
   query ──▶ FastAPI ──▶ bge-small embedding ──▶ LanceDB ANN search ──▶ wines
                │                                    │                    │
                │                              (Lance files in            ▼
                │                               MinIO / S3 / GCS)   streamed LLM note
                ▼
          Vite + React 19 UI
```

| Layer        | 2019                                   | 2026                                                   |
| ------------ | -------------------------------------- | ------------------------------------------------------ |
| Embeddings   | `all-MiniLM-L6-v2` via SageMaker job   | `bge-small-en-v1.5` (`backend/app/embeddings.py`)      |
| Vector index | scikit-learn `NearestNeighbors` in RAM | **LanceDB** ANN over object storage (`store.py`)       |
| Storage      | `embeddings.csv.gz` shuttled to S3     | One LanceDB table in a **cheap blob store**            |
| Serving      | SageMaker endpoints + `boto3`          | **FastAPI** container (`backend/app/main.py`)          |
| LLM          | none                                   | streamed sommelier note (`llm.py`)                     |
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

## Quickstart (local MinIO)

```bash
cp .env.example .env
# fill KAGGLE_API_TOKEN in .env, or run: uvx --from kaggle kaggle auth login

make download
make local
# UI:  http://localhost:5173
# API: http://localhost:8000/docs
# MinIO console: http://localhost:9001  (minioadmin / minioadmin)
```

`make local` starts MinIO, creates the bucket, creates the LanceDB table only if
it is missing, and then runs backend/frontend in hot-reload mode. Backend code
changes reload via `uvicorn --reload`; frontend changes reload through Vite.

Set `FORCE_REEMBED=true make local` to rebuild the local embeddings.
Set `HUGGINGFACE_TOKEN` in `.env` if you hit rate limits or use a gated model.

To run pieces directly without Docker, see [`backend/README.md`](backend/README.md)
and [`frontend/README.md`](frontend/README.md).

## Deploy on Google Cloud + Cloudflare Workers

The recommended deployment is Cloud Run + GCS for the API/data and Cloudflare
Workers for the always-warm frontend:

- FastAPI backend as a Cloud Run service
- LanceDB table in a GCS bucket
- ingestion as a Cloud Run Job
- Docker images in Artifact Registry
- frontend as a Cloudflare Worker with Static Assets and a same-origin `/api/*` proxy

After authenticating `gcloud` and Cloudflare Wrangler, copy the root env file
and deploy:

```bash
cp .env.example .env
# fill KAGGLE_API_TOKEN in .env, or run: uvx --from kaggle kaggle auth login

make download

AUTO_APPROVE=true make deploy
```

`download-dataset.py` is a uv script: it installs/uses the Kaggle client
in an isolated uv environment, so you do not need to `pip install kaggle`.

This runs Terraform, builds/pushes the backend image, uploads the dataset,
creates production embeddings locally into the GCS LanceDB bucket, and deploys
the Cloudflare Worker frontend. It is safe to rerun: backend images are tagged
by source hash, unchanged OpenAI secrets do not get new versions, completed
embeddings are marked with `_SUCCESS`, and Artifact Registry has cleanup
policies for old images.
See [`infra/gcp/README.md`](infra/gcp/README.md) for prerequisites and the full
step-by-step.

Because the frontend is served by Cloudflare, it loads instantly even when Cloud
Run has scaled the API to zero. The UI polls `/api/health?warm=true` with short
timeouts and shows a "Warming the API" indicator until the backend is awake, the
embedding model is loaded, and the LanceDB table is ready.

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
