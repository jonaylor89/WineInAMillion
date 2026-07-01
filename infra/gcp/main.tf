locals {
  bucket_prefix      = var.bucket_prefix != "" ? var.bucket_prefix : "${var.project_id}-${var.name}"
  lancedb_bucket     = "${local.bucket_prefix}-lancedb"
  dataset_bucket     = "${local.bucket_prefix}-datasets"
  frontend_bucket    = "${local.bucket_prefix}-frontend"
  backend_service_id = "${var.name}-api"
  ingest_job_id      = "${var.name}-ingest"

  deploy_backend = var.deploy_backend && var.backend_image != ""

  common_labels = {
    app         = var.name
    environment = "production"
    managed_by  = "terraform"
  }
}

resource "google_project_service" "apis" {
  for_each = toset([
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
    "iam.googleapis.com",
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "storage.googleapis.com",
  ])

  project            = var.project_id
  service            = each.key
  disable_on_destroy = false
}

resource "google_artifact_registry_repository" "docker" {
  location      = var.region
  repository_id = var.name
  description   = "Docker images for ${var.name}"
  format        = "DOCKER"
  labels        = local.common_labels

  depends_on = [google_project_service.apis]
}

resource "google_storage_bucket" "lancedb" {
  name                        = local.lancedb_bucket
  location                    = upper(var.region)
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  labels                      = local.common_labels

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age                = 30
      num_newer_versions = 3
      with_state         = "ARCHIVED"
    }
    action {
      type = "Delete"
    }
  }

  depends_on = [google_project_service.apis]
}

resource "google_storage_bucket" "datasets" {
  name                        = local.dataset_bucket
  location                    = upper(var.region)
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  labels                      = local.common_labels

  depends_on = [google_project_service.apis]
}

resource "google_storage_bucket" "frontend" {
  count = var.create_frontend_bucket ? 1 : 0

  name                        = local.frontend_bucket
  location                    = upper(var.region)
  uniform_bucket_level_access = true
  public_access_prevention    = "inherited"
  labels                      = local.common_labels

  website {
    main_page_suffix = "index.html"
    not_found_page   = "index.html"
  }

  depends_on = [google_project_service.apis]
}

resource "google_storage_bucket_iam_member" "frontend_public_read" {
  count = var.create_frontend_bucket ? 1 : 0

  bucket = google_storage_bucket.frontend[0].name
  role   = "roles/storage.objectViewer"
  member = "allUsers"
}

resource "google_service_account" "backend" {
  account_id   = substr(replace("${var.name}-backend", "_", "-"), 0, 30)
  display_name = "${var.name} backend runtime"

  depends_on = [google_project_service.apis]
}

resource "google_artifact_registry_repository_iam_member" "backend_artifact_reader" {
  location   = google_artifact_registry_repository.docker.location
  repository = google_artifact_registry_repository.docker.name
  role       = "roles/artifactregistry.reader"
  member     = "serviceAccount:${google_service_account.backend.email}"
}

resource "google_storage_bucket_iam_member" "backend_lancedb_admin" {
  bucket = google_storage_bucket.lancedb.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.backend.email}"
}

resource "google_storage_bucket_iam_member" "backend_dataset_reader" {
  bucket = google_storage_bucket.datasets.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.backend.email}"
}

resource "google_secret_manager_secret_iam_member" "backend_llm_secret_access" {
  count = var.llm_api_key_secret != "" ? 1 : 0

  project   = var.project_id
  secret_id = var.llm_api_key_secret
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.backend.email}"
}

resource "google_cloud_run_v2_service" "backend" {
  count = local.deploy_backend ? 1 : 0

  name     = local.backend_service_id
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"
  labels   = local.common_labels

  template {
    service_account                  = google_service_account.backend.email
    max_instance_request_concurrency = var.backend_concurrency
    timeout                          = "300s"

    scaling {
      min_instance_count = var.backend_min_instances
      max_instance_count = var.backend_max_instances
    }

    containers {
      image = var.backend_image

      ports {
        container_port = 8000
      }

      resources {
        limits = {
          cpu    = var.backend_cpu
          memory = var.backend_memory
        }
      }

      env {
        name  = "LANCEDB_URI"
        value = "gs://${google_storage_bucket.lancedb.name}/lancedb"
      }
      env {
        name  = "LANCEDB_TABLE"
        value = "wines"
      }
      env {
        name  = "EMBEDDING_MODEL"
        value = var.embedding_model
      }
      env {
        name  = "EMBEDDING_DIM"
        value = tostring(var.embedding_dim)
      }
      env {
        name  = "CORS_ORIGINS"
        value = var.cors_origins
      }
      env {
        name  = "LLM_ENABLED"
        value = tostring(var.llm_enabled)
      }
      env {
        name  = "LLM_MODEL"
        value = var.llm_model
      }

      dynamic "env" {
        for_each = var.llm_base_url != "" ? [var.llm_base_url] : []
        content {
          name  = "LLM_BASE_URL"
          value = env.value
        }
      }

      dynamic "env" {
        for_each = var.llm_api_key_secret != "" ? [var.llm_api_key_secret] : []
        content {
          name = "LLM_API_KEY"
          value_source {
            secret_key_ref {
              secret  = env.value
              version = "latest"
            }
          }
        }
      }
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  depends_on = [
    google_project_service.apis,
    google_artifact_registry_repository_iam_member.backend_artifact_reader,
    google_storage_bucket_iam_member.backend_lancedb_admin,
    google_storage_bucket_iam_member.backend_dataset_reader,
    google_secret_manager_secret_iam_member.backend_llm_secret_access,
  ]
}

resource "google_cloud_run_v2_service_iam_member" "public_backend" {
  count = local.deploy_backend && var.public_backend ? 1 : 0

  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.backend[0].name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_v2_job" "ingest" {
  count = local.deploy_backend && var.ingest_csv_uri != "" ? 1 : 0

  name     = local.ingest_job_id
  location = var.region
  labels   = local.common_labels

  template {
    template {
      service_account = google_service_account.backend.email
      timeout         = "3600s"

      containers {
        image   = var.backend_image
        command = ["uv"]
        args = [
          "run",
          "python",
          "-m",
          "app.ingest",
          "--csv",
          var.ingest_csv_uri,
          "--overwrite",
        ]

        resources {
          limits = {
            cpu    = var.backend_cpu
            memory = var.backend_memory
          }
        }

        env {
          name  = "LANCEDB_URI"
          value = "gs://${google_storage_bucket.lancedb.name}/lancedb"
        }
        env {
          name  = "LANCEDB_TABLE"
          value = "wines"
        }
        env {
          name  = "EMBEDDING_MODEL"
          value = var.embedding_model
        }
        env {
          name  = "EMBEDDING_DIM"
          value = tostring(var.embedding_dim)
        }
      }
    }
  }

  depends_on = [
    google_project_service.apis,
    google_artifact_registry_repository_iam_member.backend_artifact_reader,
    google_storage_bucket_iam_member.backend_lancedb_admin,
    google_storage_bucket_iam_member.backend_dataset_reader,
  ]
}
