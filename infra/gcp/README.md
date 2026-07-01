# GCP deployment

Terraform for the recommended production-ish deployment:

```txt
Frontend:    static GCS bucket (or Cloudflare Pages / Firebase Hosting)
Backend:     Cloud Run service
Vectors:     LanceDB table in GCS
Ingest:      Cloud Run Job
Images:      Artifact Registry
Secrets:     Secret Manager (optional LLM API key)
```

This keeps the app cheap: Cloud Run can scale to zero, and LanceDB lives in a
plain GCS bucket rather than a hosted vector database.

## Prerequisites

- `gcloud` authenticated with permissions to manage the project
- Terraform >= 1.7
- Docker
- A GCP project with billing enabled
- The dataset CSV: `winemag-data-130k-v2.csv`

```bash
gcloud auth login
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
```

## 1. Create the base infrastructure

```bash
cd infra/gcp
cp terraform.tfvars.example terraform.tfvars
# edit terraform.tfvars: project_id, region, name
terraform init
terraform apply
```

This creates:

- the LanceDB bucket,
- a dataset bucket,
- an Artifact Registry Docker repository,
- the backend service account and IAM,
- optionally a public static frontend bucket.

At this stage `deploy_backend=false`, because Cloud Run needs a pushed image.

## 2. Build and push the backend image

From the repo root:

```bash
PROJECT_ID=YOUR_PROJECT_ID
REGION=us-central1
NAME=wine-in-a-million
IMAGE="$REGION-docker.pkg.dev/$PROJECT_ID/$NAME/backend:$(date +%Y%m%d%H%M%S)"

gcloud auth configure-docker "$REGION-docker.pkg.dev"
docker build -t "$IMAGE" ./backend
docker push "$IMAGE"
```

## 3. Upload the dataset

```bash
DATASET_BUCKET=$(terraform -chdir=infra/gcp output -raw dataset_bucket)
gcloud storage cp backend/data/winemag-data-130k-v2.csv "$DATASET_BUCKET/"
```

## 4. Deploy Cloud Run + create the ingest job

Edit `infra/gcp/terraform.tfvars`:

```hcl
deploy_backend = true
backend_image  = "us-central1-docker.pkg.dev/YOUR_PROJECT_ID/wine-in-a-million/backend:TAG"
ingest_csv_uri = "gs://YOUR_PROJECT_ID-wine-in-a-million-datasets/winemag-data-130k-v2.csv"
```

Then:

```bash
terraform -chdir=infra/gcp apply
```

## 5. Run ingestion

```bash
gcloud run jobs execute wine-in-a-million-ingest \
  --region us-central1 \
  --wait
```

This embeds the reviews and writes the LanceDB table to:

```bash
terraform -chdir=infra/gcp output -raw lancedb_uri
```

## 6. Smoke test the API

```bash
API=$(terraform -chdir=infra/gcp output -raw backend_service_url)
curl -s "$API/health" | jq
curl -s "$API/search" \
  -H 'content-type: application/json' \
  -d '{"query":"bold earthy red for steak night","k":5}' | jq
```

## 7. Deploy the frontend

Option A: GCS static bucket created by Terraform:

```bash
cd frontend
VITE_API_BASE="$API" npm run build
FRONTEND_BUCKET=$(terraform -chdir=../infra/gcp output -raw frontend_bucket)
gcloud storage rsync -r --delete dist "$FRONTEND_BUCKET"
```

Then open:

```bash
terraform -chdir=infra/gcp output -raw frontend_website_url
```

For a public blog demo, I still recommend putting **Cloudflare Pages** or
**Firebase Hosting** in front of the frontend for HTTPS, caching, and nicer
domains. Set `VITE_API_BASE` to the Cloud Run API URL during build.

## Optional: LLM explanations

Create a Secret Manager secret:

```bash
echo -n "$OPENAI_API_KEY" | gcloud secrets create wine-llm-api-key --data-file=-
```

Set in `terraform.tfvars`:

```hcl
llm_enabled        = true
llm_api_key_secret = "wine-llm-api-key"
llm_model          = "gpt-4o-mini"
```

Then `terraform apply`.

## Costs / tuning

- `backend_min_instances = 0` is cheapest but first request may be slow because
  the embedding model loads on cold start.
- Set `backend_min_instances = 1` for a snappier demo.
- The LanceDB table is just GCS objects, so idle storage cost is tiny.
- If ingestion runs out of memory, temporarily increase `backend_memory` to
  `4Gi` for the job/service image, run ingestion, then lower it again.
