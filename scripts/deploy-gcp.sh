#!/usr/bin/env bash
set -euo pipefail

# Two-phase GCP deployment for Wine in a Million.
#
# Required:
#   PROJECT_ID=your-gcp-project ./scripts/deploy-gcp.sh
# Optional:
#   REGION=us-central1 NAME=wine-in-a-million DATASET=backend/data/winemag-data-130k-v2.csv ./scripts/deploy-gcp.sh

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INFRA="$ROOT/infra/gcp"

PROJECT_ID="${PROJECT_ID:?Set PROJECT_ID}"
REGION="${REGION:-us-central1}"
NAME="${NAME:-wine-in-a-million}"
DATASET="${DATASET:-}"
TAG="${TAG:-$(date +%Y%m%d%H%M%S)}"
IMAGE="$REGION-docker.pkg.dev/$PROJECT_ID/$NAME/backend:$TAG"

cd "$ROOT"

echo "==> Phase 1: create base infra (GCS, Artifact Registry, IAM)"
terraform -chdir="$INFRA" init
terraform -chdir="$INFRA" apply \
  -var="project_id=$PROJECT_ID" \
  -var="region=$REGION" \
  -var="name=$NAME" \
  -var="deploy_backend=false"

echo "==> Build and push backend image: $IMAGE"
gcloud auth configure-docker "$REGION-docker.pkg.dev" --quiet
docker build -t "$IMAGE" "$ROOT/backend"
docker push "$IMAGE"

INGEST_CSV_URI=""
if [[ -n "$DATASET" ]]; then
  DATASET_BUCKET="$(terraform -chdir="$INFRA" output -raw dataset_bucket)"
  BASENAME="$(basename "$DATASET")"
  echo "==> Upload dataset to $DATASET_BUCKET/$BASENAME"
  gcloud storage cp "$DATASET" "$DATASET_BUCKET/$BASENAME"
  INGEST_CSV_URI="$DATASET_BUCKET/$BASENAME"
fi

echo "==> Phase 2: deploy Cloud Run"
terraform -chdir="$INFRA" apply \
  -var="project_id=$PROJECT_ID" \
  -var="region=$REGION" \
  -var="name=$NAME" \
  -var="deploy_backend=true" \
  -var="backend_image=$IMAGE" \
  -var="ingest_csv_uri=$INGEST_CSV_URI"

if [[ -n "$INGEST_CSV_URI" ]]; then
  echo "==> Run ingest job"
  gcloud run jobs execute "$NAME-ingest" --region "$REGION" --wait
fi

API="$(terraform -chdir="$INFRA" output -raw backend_service_url)"
echo "==> API deployed: $API"
echo "==> Test: curl -s '$API/health' | jq"
