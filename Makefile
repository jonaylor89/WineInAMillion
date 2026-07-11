SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
.NOTPARALLEL:

-include .env
export

export DOCKER_BUILDKIT := 1

# Keep deploys working for older .env files created before newer deploy knobs existed.
BACKEND_PLATFORM := $(if $(strip $(BACKEND_PLATFORM)),$(BACKEND_PLATFORM),linux/amd64)
BACKEND_MIN_INSTANCES := $(if $(strip $(BACKEND_MIN_INSTANCES)),$(BACKEND_MIN_INSTANCES),0)
BACKEND_MAX_INSTANCES := $(if $(strip $(BACKEND_MAX_INSTANCES)),$(BACKEND_MAX_INSTANCES),5)
BACKEND_MEMORY := $(if $(strip $(BACKEND_MEMORY)),$(BACKEND_MEMORY),2Gi)
BACKEND_CPU := $(if $(strip $(BACKEND_CPU)),$(BACKEND_CPU),2)
INGEST_TIMEOUT := $(if $(strip $(INGEST_TIMEOUT)),$(INGEST_TIMEOUT),7200s)
RUN_INGEST := $(if $(strip $(RUN_INGEST)),$(RUN_INGEST),true)
INGEST_MODE := $(if $(strip $(INGEST_MODE)),$(INGEST_MODE),local)
WAIT_FOR_INGEST := $(if $(strip $(WAIT_FOR_INGEST)),$(WAIT_FOR_INGEST),false)
FORCE_REEMBED := $(if $(strip $(FORCE_REEMBED)),$(FORCE_REEMBED),false)
BATCH_SIZE := $(if $(strip $(BATCH_SIZE)),$(BATCH_SIZE),64)

# App/deploy config lives in .env. The Makefile only derives transient values.
BACKEND_HASH := $(shell python3 -c 'import hashlib, os; from pathlib import Path; paths=[Path("backend/Dockerfile"), Path("backend/pyproject.toml")]; paths += sorted(p for p in Path("backend/app").rglob("*") if p.is_file()); h=hashlib.sha256(); [h.update(str(p).encode()) or h.update(b"\0") or h.update(p.read_bytes()) or h.update(b"\0") for p in paths]; h.update(b"embedding_model:"); h.update(os.environ.get("EMBEDDING_MODEL", "").encode()); h.update(b"backend_platform:"); h.update(os.environ.get("BACKEND_PLATFORM", "").encode()); print(h.hexdigest()[:12])')
EFFECTIVE_TAG := $(if $(strip $(TAG)),$(TAG),backend-$(BACKEND_HASH))
IMAGE := $(REGION)-docker.pkg.dev/$(PROJECT_ID)/$(NAME)/backend:$(EFFECTIVE_TAG)
DATASET_PATH := $(abspath $(DATASET))
DATASET_BASENAME := $(notdir $(DATASET))
APPLY_ARGS := $(if $(filter true,$(AUTO_APPROVE)),-auto-approve,)
TF_VARS := \
	-var="project_id=$(PROJECT_ID)" \
	-var="region=$(REGION)" \
	-var="name=$(NAME)" \
	-var="llm_api_key_secret=$(LLM_API_KEY_SECRET)" \
	-var="llm_model=$(LLM_MODEL)" \
	-var="llm_base_url=$(LLM_BASE_URL)" \
	-var="backend_min_instances=$(BACKEND_MIN_INSTANCES)" \
	-var="backend_max_instances=$(BACKEND_MAX_INSTANCES)" \
	-var="backend_memory=$(BACKEND_MEMORY)" \
	-var="backend_cpu=$(BACKEND_CPU)" \
	-var="ingest_timeout=$(INGEST_TIMEOUT)"

.PHONY: help init-env require-env download local deploy check clean \
	check-local-prereqs check-deploy-prereqs terraform-bootstrap ensure-secret \
	build-push-backend upload-dataset terraform-deploy ingest-prod deploy-worker

help: ## Show available targets
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make <target>\n\nTargets:\n"} /^[a-zA-Z0-9_-]+:.*##/ {printf "  %-18s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

init-env: ## Create .env from .env.example
	@if [[ -f .env ]]; then \
		echo ".env already exists"; \
	else \
		cp .env.example .env; \
		echo "Created .env from .env.example. Fill in secrets/config before continuing."; \
	fi

require-env:
	@if [[ ! -f .env ]]; then \
		echo "Missing .env. Run: make init-env" >&2; \
		exit 1; \
	fi

download: require-env ## Download the Kaggle dataset via uv-managed Kaggle client
	@./scripts/download-dataset.py

check-local-prereqs:
	@command -v docker >/dev/null || { echo "Missing required command: docker" >&2; exit 1; }
	@if ! docker info >/dev/null 2>&1; then \
		echo "Docker is not running or the active Docker context is not reachable." >&2; \
		echo "Start Docker/OrbStack, or switch context with: docker context use orbstack" >&2; \
		exit 1; \
	fi
	@if [[ ! -f "$(DATASET_PATH)" ]]; then \
		echo "Dataset not found: $(DATASET)" >&2; \
		echo "Run: make download" >&2; \
		exit 1; \
	fi

local: require-env check-local-prereqs ## Run local dev stack; create MinIO embeddings only if missing
	@DATASET_IN_CONTAINER="/data/$(DATASET_BASENAME)"; \
	if [[ "$(DATASET_PATH)" != "$(abspath backend/data)/"* ]]; then \
		mkdir -p backend/data; \
		cp "$(DATASET_PATH)" "backend/data/$(DATASET_BASENAME)"; \
	fi; \
	echo "==> Building backend image and pre-downloading embedding model: $(EMBEDDING_MODEL)"; \
	docker compose build backend ingest; \
	echo "==> Starting MinIO and ensuring bucket exists"; \
	docker compose up -d minio; \
	docker compose run --rm createbuckets; \
	table_ready="false"; \
	if [[ "$(FORCE_REEMBED)" != "true" ]]; then \
		table_ready="$$(docker compose run --rm --entrypoint uv ingest run python -c 'from app import store; print("true" if store.table_exists() else "false")')"; \
		table_ready="$$(printf '%s\n' "$$table_ready" | tail -n 1)"; \
	fi; \
	if [[ "$(FORCE_REEMBED)" == "true" || "$$table_ready" != "true" ]]; then \
		echo "==> LanceDB table missing or FORCE_REEMBED=true; creating embeddings"; \
		ARGS=(--csv "$$DATASET_IN_CONTAINER" --batch-size "$(BATCH_SIZE)" --overwrite); \
		if [[ -n "$(LIMIT)" ]]; then ARGS+=(--limit "$(LIMIT)"); fi; \
		docker compose run --rm ingest "$${ARGS[@]}"; \
	else \
		echo "==> LanceDB table already exists; skipping embedding creation"; \
	fi; \
	echo "==> Starting hot-reload dev stack"; \
	echo "    UI:    http://localhost:5173"; \
	echo "    API:   http://localhost:8000/docs"; \
	echo "    MinIO: http://localhost:9001  (minioadmin / minioadmin)"; \
	docker compose up backend frontend

check-deploy-prereqs:
	@for cmd in gcloud terraform docker npm; do command -v $$cmd >/dev/null || { echo "Missing required command: $$cmd" >&2; exit 1; }; done
	@if ! docker info >/dev/null 2>&1; then \
		echo "Docker is not running or the active Docker context is not reachable." >&2; \
		echo "Start Docker/OrbStack, or switch context with: docker context use orbstack" >&2; \
		exit 1; \
	fi
	@if ! npx --yes wrangler@4.22.0 whoami >/dev/null 2>&1; then \
		echo "Cloudflare Wrangler is not authenticated." >&2; \
		echo "Either run: npx --yes wrangler@4.22.0 login" >&2; \
		echo "or set CLOUDFLARE_API_TOKEN in .env with Workers deploy permissions." >&2; \
		exit 1; \
	fi
	@if [[ ! -f "$(DATASET_PATH)" ]]; then \
		echo "Dataset not found: $(DATASET)" >&2; \
		echo "Run: make download" >&2; \
		exit 1; \
	fi

terraform-bootstrap:
	@echo "==> Initialize Terraform"
	@terraform -chdir=infra/gcp init
	@echo "==> Clearing any taint left by earlier failed Cloud Run image deploys"
	@terraform -chdir=infra/gcp untaint 'google_cloud_run_v2_service.backend[0]' >/dev/null 2>&1 || true
	@terraform -chdir=infra/gcp untaint 'google_cloud_run_v2_job.ingest[0]' >/dev/null 2>&1 || true
	@if terraform -chdir=infra/gcp state show 'google_cloud_run_v2_service.backend[0]' >/dev/null 2>&1; then \
		echo "==> Cloud Run service already exists; skipping bootstrap apply"; \
	elif terraform -chdir=infra/gcp state show 'google_artifact_registry_repository.docker' >/dev/null 2>&1; then \
		echo "==> Base GCP infra already exists; skipping bootstrap apply"; \
	else \
		echo "==> Bootstrap base GCP infra"; \
		terraform -chdir=infra/gcp apply $(APPLY_ARGS) $(TF_VARS) -var="deploy_backend=false"; \
	fi

ensure-secret:
	@if [[ -z "$${OPENAI_API_KEY:-}" ]]; then \
		echo "==> OPENAI_API_KEY not set; assuming Secret Manager secret exists: $(LLM_API_KEY_SECRET)"; \
		exit 0; \
	fi; \
	echo "==> Ensuring Secret Manager secret exists: $(LLM_API_KEY_SECRET)"; \
	gcloud secrets describe "$(LLM_API_KEY_SECRET)" --project "$(PROJECT_ID)" >/dev/null 2>&1 || \
		gcloud secrets create "$(LLM_API_KEY_SECRET)" --project "$(PROJECT_ID)" --replication-policy="automatic"; \
	latest="$$(gcloud secrets versions access latest --secret "$(LLM_API_KEY_SECRET)" --project "$(PROJECT_ID)" 2>/dev/null || true)"; \
	if [[ "$$latest" == "$${OPENAI_API_KEY:-}" ]]; then \
		echo "==> Secret Manager latest version already matches .env; skipping new version"; \
	else \
		echo "==> Adding new Secret Manager version for: $(LLM_API_KEY_SECRET)"; \
		printf '%s' "$${OPENAI_API_KEY:-}" | gcloud secrets versions add "$(LLM_API_KEY_SECRET)" --project "$(PROJECT_ID)" --data-file=-; \
	fi

build-push-backend:
	@echo "==> Build and push backend image for Cloud Run platform $(BACKEND_PLATFORM): $(IMAGE)"
	@gcloud auth configure-docker "$(REGION)-docker.pkg.dev" --quiet
	@BUILD_ARGS=(--platform "$(BACKEND_PLATFORM)" --build-arg "EMBEDDING_MODEL_SOURCE=$(EMBEDDING_MODEL)" --provenance=false --tag "$(IMAGE)" --push); \
	if [[ -n "$${HUGGINGFACE_TOKEN:-}" ]]; then BUILD_ARGS+=(--secret id=hf_token,env=HUGGINGFACE_TOKEN); fi; \
	docker buildx build "$${BUILD_ARGS[@]}" backend

upload-dataset:
	@DATASET_BUCKET="$$(terraform -chdir=infra/gcp output -raw dataset_bucket)"; \
	INGEST_CSV_URI="$$DATASET_BUCKET/$(DATASET_BASENAME)"; \
	echo "==> Upload dataset to $$INGEST_CSV_URI"; \
	gcloud storage cp "$(DATASET_PATH)" "$$INGEST_CSV_URI"

terraform-deploy:
	@DATASET_BUCKET="$$(terraform -chdir=infra/gcp output -raw dataset_bucket)"; \
	INGEST_CSV_URI="$$DATASET_BUCKET/$(DATASET_BASENAME)"; \
	echo "==> Phase 2: deploy Cloud Run + ingest job"; \
	terraform -chdir=infra/gcp apply $(APPLY_ARGS) $(TF_VARS) \
		-var="deploy_backend=true" \
		-var="backend_image=$(IMAGE)" \
		-var="ingest_csv_uri=$$INGEST_CSV_URI"

ingest-prod:
	@LANCEDB_URI="$$(terraform -chdir=infra/gcp output -raw lancedb_uri)"; \
	if [[ "$(RUN_INGEST)" != "true" ]]; then \
		echo "==> RUN_INGEST=false; skipping ingest"; \
		exit 0; \
	fi; \
	if [[ "$(FORCE_REEMBED)" != "true" ]] && gcloud storage ls "$${LANCEDB_URI}/_SUCCESS" --project "$(PROJECT_ID)" >/dev/null 2>&1; then \
		echo "==> LanceDB table is marked complete at $$LANCEDB_URI; skipping ingest"; \
		exit 0; \
	fi; \
	if [[ "$(INGEST_MODE)" == "local" ]]; then \
		RUNNING_EXECUTION="$$(gcloud run jobs executions list --job "$(NAME)-ingest" --region "$(REGION)" --project "$(PROJECT_ID)" --limit 10 --format=json 2>/dev/null | python3 -c 'import json,sys; data=json.load(sys.stdin); print(next((e["metadata"]["name"] for e in data if e.get("status",{}).get("runningCount",0)), ""))')"; \
		if [[ -n "$$RUNNING_EXECUTION" ]]; then \
			echo "==> Cancelling stale Cloud Run ingest execution before local ingest: $$RUNNING_EXECUTION"; \
			gcloud run jobs executions cancel "$$RUNNING_EXECUTION" --region "$(REGION)" --project "$(PROJECT_ID)" --quiet || true; \
		fi; \
		ADC_PATH="$${GOOGLE_APPLICATION_CREDENTIALS:-$$HOME/.config/gcloud/application_default_credentials.json}"; \
		if [[ ! -f "$$ADC_PATH" ]]; then echo "Run: gcloud auth application-default login" >&2; exit 1; fi; \
		LOCAL_IMAGE="$(NAME)-backend-local-ingest:$(BACKEND_HASH)"; \
		echo "==> Building native local ingest image and pre-downloading embedding model"; \
		LOCAL_BUILD_ARGS=(--build-arg "EMBEDDING_MODEL_SOURCE=$(EMBEDDING_MODEL)" --tag "$$LOCAL_IMAGE"); \
		if [[ -n "$${HUGGINGFACE_TOKEN:-}" ]]; then LOCAL_BUILD_ARGS+=(--secret id=hf_token,env=HUGGINGFACE_TOKEN); fi; \
		docker build "$${LOCAL_BUILD_ARGS[@]}" backend; \
		echo "==> Creating production LanceDB embeddings locally at $$LANCEDB_URI"; \
		gcloud storage rm -r "$${LANCEDB_URI}/_SUCCESS" --project "$(PROJECT_ID)" >/dev/null 2>&1 || true; \
		docker run --rm \
			-e LANCEDB_URI="$$LANCEDB_URI" \
			-e LANCEDB_TABLE="wines" \
			-e EMBEDDING_MODEL="/models/embedding" \
			-e EMBEDDING_DIM="384" \
			-e GOOGLE_APPLICATION_CREDENTIALS="/gcp/adc.json" \
			-v "$$ADC_PATH:/gcp/adc.json:ro" \
			-v "$(DATASET_PATH):/data/winemag-data-130k-v2.csv:ro" \
			"$$LOCAL_IMAGE" \
			uv run python -m app.ingest --csv /data/winemag-data-130k-v2.csv --batch-size "$(BATCH_SIZE)" --overwrite; \
		printf 'completed_at=%s\n' "$$(date -u +%Y-%m-%dT%H:%M:%SZ)" | gcloud storage cp - "$${LANCEDB_URI}/_SUCCESS" --project "$(PROJECT_ID)" >/dev/null; \
	elif [[ "$(INGEST_MODE)" == "cloud" ]]; then \
		if [[ "$(WAIT_FOR_INGEST)" == "true" ]]; then \
			gcloud run jobs execute "$(NAME)-ingest" --region "$(REGION)" --project "$(PROJECT_ID)" --wait; \
			printf 'completed_at=%s\n' "$$(date -u +%Y-%m-%dT%H:%M:%SZ)" | gcloud storage cp - "$${LANCEDB_URI}/_SUCCESS" --project "$(PROJECT_ID)" >/dev/null; \
		else \
			gcloud run jobs execute "$(NAME)-ingest" --region "$(REGION)" --project "$(PROJECT_ID)" --async; \
		fi; \
	else \
		echo "Unsupported INGEST_MODE=$(INGEST_MODE) (expected local or cloud)" >&2; exit 1; \
	fi

deploy-worker:
	@API_URL="$$(terraform -chdir=infra/gcp output -raw backend_service_url)"; \
	if [[ -z "$$API_URL" || "$$API_URL" == "null" ]]; then echo "Could not read backend_service_url" >&2; exit 1; fi; \
	echo "==> Build and deploy Cloudflare Worker frontend -> $$API_URL"; \
	cd frontend; \
	npm run build; \
	WRANGLER_CONFIG="$$PWD/.wrangler.deploy.toml"; \
	API_URL="$$API_URL" WORKER_NAME="$(WORKER_NAME)" python3 -c 'from pathlib import Path; import os; config = Path("wrangler.toml").read_text(); config = config.replace("name = \"wine-in-a-million\"", "name = \"" + os.environ["WORKER_NAME"] + "\""); config = config.replace("API_ORIGIN = \"http://localhost:8000\"", "API_ORIGIN = \"" + os.environ["API_URL"] + "\""); Path(".wrangler.deploy.toml").write_text(config)'; \
	npx --yes wrangler@4.22.0 deploy --config "$$WRANGLER_CONFIG"; \
	rm -f "$$WRANGLER_CONFIG"; \
	echo "==> Done"; \
	echo "Cloud Run API: $$API_URL"; \
	echo "Frontend Worker: $(WORKER_NAME)"; \
	echo "Backend image: $(IMAGE)"; \
	echo "Health check: curl -s '$$API_URL/health?warm=true' | jq"

deploy: require-env check-deploy-prereqs terraform-bootstrap ensure-secret build-push-backend upload-dataset terraform-deploy ingest-prod deploy-worker ## Deploy GCP backend/data + Cloudflare Worker

check: ## Run local validation checks
	@python3 -m py_compile backend/app/*.py scripts/download-dataset.py
	@terraform -chdir=infra/gcp validate
	@cd frontend && npm run build
	@rm -rf frontend/dist frontend/tsconfig.tsbuildinfo backend/app/__pycache__ scripts/__pycache__

clean: ## Remove local generated frontend/build artifacts
	@rm -rf frontend/dist frontend/tsconfig.tsbuildinfo backend/app/__pycache__ scripts/__pycache__
