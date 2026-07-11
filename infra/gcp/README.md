# GCP deployment

Terraform for the recommended production-ish deployment:

```txt
Frontend:    Cloudflare Worker with Static Assets + /api proxy
Backend:     Cloud Run service
Vectors:     LanceDB table in GCS
Ingest:      Cloud Run Job
Images:      Artifact Registry
Secrets:     Secret Manager (required OpenAI-compatible API key)
```

This keeps the app cheap: Cloud Run can scale to zero, the frontend never cold
starts because it is just static files, and LanceDB lives in a plain GCS bucket
rather than a hosted vector database.

The frontend calls `/api/health?warm=true` with a short timeout on page load. If
Cloud Run is cold, users see a "Warming the API" indicator while those health
checks poke the service awake and force-load the embedding model before the
first real search.

## Prerequisites

- `gcloud` authenticated with permissions to manage the project
- Terraform >= 1.7
- Docker
- A GCP project with billing enabled
- A Cloudflare account/API login for `wrangler deploy`
- The dataset CSV: `winemag-data-130k-v2.csv`

```bash
gcloud auth login
gcloud auth application-default login
gcloud config set project wine-in-a-million-501121
npx --yes wrangler@4.22.0 login   # or set CLOUDFLARE_API_TOKEN
```

## One-command deploy

Once the prerequisites above are done, create `.env`, download the dataset, and
run from the repo root:

```bash
cp .env.example .env
# fill KAGGLE_API_TOKEN in .env, or run: uvx --from kaggle kaggle auth login

make download

AUTO_APPROVE=true make deploy
```

`download-dataset.py` is a uv script: it installs/uses the Kaggle client
in an isolated uv environment, so you do not need to `pip install kaggle`.

`make deploy` runs every deploy step: Terraform, backend image build/push,
dataset upload, Cloud Run deploy, local embedding into the production GCS
LanceDB bucket, and Cloudflare Worker deploy.

It is designed to be safe to rerun:

- backend images are built with Docker Buildx for `linux/amd64` (Cloud Run requirement) and tagged by a hash of `backend/Dockerfile`, `backend/pyproject.toml`, `backend/app/**`, `EMBEDDING_MODEL`, and `BACKEND_PLATFORM`,
- unchanged `OPENAI_API_KEY` values do not create new Secret Manager versions,
- the dataset object is overwritten at the same GCS path,
- deploy embeds locally by default (`INGEST_MODE=local`) and writes directly to GCS,
- deploy cancels stale Cloud Run ingest executions before local ingest,
- deploy skips ingest only when a `_SUCCESS` marker exists unless `FORCE_REEMBED=true`,
- `INGEST_MODE=cloud` remains available as a Cloud Run Job fallback,
- Artifact Registry deletes stale/untagged images via cleanup policies.

If you prefer to inspect Terraform plans before applying, omit `AUTO_APPROVE=true`.

The lower-level commands below are for debugging only; normal deployment should
use `make deploy`.

## Manual deploy steps

### 1. Create the base infrastructure

```bash
cd infra/gcp
cp terraform.tfvars.example terraform.tfvars
# edit terraform.tfvars if you need to override project_id, region, or name
terraform init
terraform apply
```

This creates:

- the LanceDB bucket,
- a dataset bucket,
- an Artifact Registry Docker repository,
- the backend service account and IAM.

The frontend is not provisioned in GCP; it is a Cloudflare Worker deployed from
`frontend/wrangler.toml`.

At this stage `deploy_backend=false`, because Cloud Run needs a pushed image.

### 2. Build and push the backend image

From the repo root:

```bash
PROJECT_ID=wine-in-a-million-501121
REGION=us-central1
NAME=wine-in-a-million
IMAGE="$REGION-docker.pkg.dev/$PROJECT_ID/$NAME/backend:$(date +%Y%m%d%H%M%S)"

gcloud auth configure-docker "$REGION-docker.pkg.dev"
docker build -t "$IMAGE" ./backend
docker push "$IMAGE"
```

### 3. Upload the dataset

```bash
DATASET_BUCKET=$(terraform -chdir=infra/gcp output -raw dataset_bucket)
gcloud storage cp backend/data/winemag-data-130k-v2.csv "$DATASET_BUCKET/"
```

### 4. Deploy Cloud Run + create the ingest job

Edit `infra/gcp/terraform.tfvars`:

```hcl
deploy_backend = true
backend_image  = "us-central1-docker.pkg.dev/wine-in-a-million-501121/wine-in-a-million/backend:TAG"
ingest_csv_uri = "gs://wine-in-a-million-501121-wine-in-a-million-datasets/winemag-data-130k-v2.csv"
```

Then:

```bash
terraform -chdir=infra/gcp apply
```

### 5. Run ingestion

```bash
gcloud run jobs execute wine-in-a-million-ingest \
  --region us-central1 \
  --wait
```

This embeds the reviews and writes the LanceDB table to:

```bash
terraform -chdir=infra/gcp output -raw lancedb_uri
```

### 6. Smoke test the API

```bash
API=$(terraform -chdir=infra/gcp output -raw backend_service_url)
curl -s "$API/health" | jq
curl -s "$API/search" \
  -H 'content-type: application/json' \
  -d '{"query":"bold earthy red for steak night","k":5}' | jq
```

### 7. Deploy the frontend to Cloudflare Workers

The frontend should not run on Cloud Run. It is deployed as a **Cloudflare
Worker with Static Assets**. The Worker serves the Vite build and proxies
same-origin `/api/*` requests to Cloud Run:

```txt
browser ──▶ Cloudflare Worker ──▶ static assets
                         └──────▶ /api/* → Cloud Run
```

That gives the best behavior for cold starts: the page loads instantly from
Cloudflare, then the UI polls `/api/health`. If Cloud Run is cold, users see the
"Warming the API" indicator while the Worker wakes the backend.

Frontend deployment is handled by `make deploy`, which injects the
Cloud Run URL into a temporary Wrangler config before deploying.

For custom domains, attach the Worker route in Cloudflare. Because the browser
calls the Worker on the same origin, the API proxy does not require browser CORS
for normal usage. Keep `cors_origins` strict only if you also allow direct
browser calls to the Cloud Run URL.

## Streaming LLM recommendations

`LLM_API_KEY` is required. The easiest path is to put `OPENAI_API_KEY` in the
root `.env`; `make deploy` creates/updates the Secret Manager secret and
wires it into Cloud Run as `LLM_API_KEY`.

For OpenAI, leave `LLM_BASE_URL` blank. For OpenAI-compatible providers, set
`LLM_BASE_URL` and `LLM_MODEL` in `.env`.

## Costs / tuning

- `backend_min_instances = 0` is cheapest but first request may be slow because
  the embedding model loads on cold start.
- Set `backend_min_instances = 1` for a snappier demo.
- The LanceDB table is just GCS objects, so idle storage cost is tiny.
- Full-dataset ingestion takes about an hour on CPU. By default it runs locally
  during `make deploy`; keep your laptop awake. If using `INGEST_MODE=cloud`,
  `INGEST_TIMEOUT` defaults to `7200s` because the old one-hour timeout killed
  the job at ~93%.
- If ingestion runs out of memory, temporarily increase `BACKEND_MEMORY` to
  `4Gi` for the job/service image, run ingestion, then lower it again.
