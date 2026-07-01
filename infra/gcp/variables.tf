variable "project_id" {
  description = "GCP project ID to deploy into."
  type        = string
}

variable "region" {
  description = "GCP region for Cloud Run and Artifact Registry."
  type        = string
  default     = "us-central1"
}

variable "name" {
  description = "Base name for resources."
  type        = string
  default     = "wine-in-a-million"
}

variable "bucket_prefix" {
  description = "Optional globally-unique prefix for GCS buckets. Defaults to project_id-name."
  type        = string
  default     = ""
}

variable "deploy_backend" {
  description = "Create the Cloud Run service and ingest job. Set false for the first infra-only apply."
  type        = bool
  default     = false
}

variable "backend_image" {
  description = "Container image URI for the FastAPI backend. Required when deploy_backend=true."
  type        = string
  default     = ""
}

variable "public_backend" {
  description = "Allow unauthenticated requests to the API."
  type        = bool
  default     = true
}

variable "cors_origins" {
  description = "Comma-separated origins allowed by FastAPI CORS middleware. Use your frontend URL in production."
  type        = string
  default     = "*"
}

variable "embedding_model" {
  description = "SentenceTransformers embedding model loaded by the backend."
  type        = string
  default     = "BAAI/bge-small-en-v1.5"
}

variable "embedding_dim" {
  description = "Embedding vector dimension. Must match embedding_model."
  type        = number
  default     = 384
}

variable "backend_memory" {
  description = "Cloud Run memory limit. SentenceTransformers needs more than the default."
  type        = string
  default     = "2Gi"
}

variable "backend_cpu" {
  description = "Cloud Run CPU limit."
  type        = string
  default     = "2"
}

variable "backend_min_instances" {
  description = "Minimum warm Cloud Run instances. Set to 1 to avoid cold starts."
  type        = number
  default     = 0
}

variable "backend_max_instances" {
  description = "Maximum Cloud Run instances."
  type        = number
  default     = 5
}

variable "backend_concurrency" {
  description = "Cloud Run request concurrency. Lower is safer for CPU-bound local embeddings."
  type        = number
  default     = 10
}

variable "llm_enabled" {
  description = "Whether the backend should attempt to generate LLM explanations."
  type        = bool
  default     = false
}

variable "llm_model" {
  description = "OpenAI-compatible chat model name."
  type        = string
  default     = "gpt-4o-mini"
}

variable "llm_base_url" {
  description = "Optional OpenAI-compatible base URL. Leave empty for OpenAI default."
  type        = string
  default     = ""
}

variable "llm_api_key_secret" {
  description = "Optional Secret Manager secret ID containing the LLM API key. Example: wine-llm-api-key"
  type        = string
  default     = ""
}

variable "ingest_csv_uri" {
  description = "Optional gs:// URI for the wine CSV. If set with deploy_backend=true, creates a Cloud Run Job."
  type        = string
  default     = ""
}

variable "create_frontend_bucket" {
  description = "Create a public GCS static website bucket for the built frontend."
  type        = bool
  default     = true
}
