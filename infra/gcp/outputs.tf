output "artifact_registry_repository" {
  description = "Artifact Registry Docker repository."
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.docker.repository_id}"
}

output "backend_service_url" {
  description = "Cloud Run API URL, once deploy_backend=true and backend_image is set."
  value       = length(google_cloud_run_v2_service.backend) > 0 ? google_cloud_run_v2_service.backend[0].uri : null
}

output "lancedb_uri" {
  description = "LanceDB object-store URI used by the backend."
  value       = "gs://${google_storage_bucket.lancedb.name}/lancedb"
}

output "dataset_bucket" {
  description = "Upload the winemag CSV here before running the ingest job."
  value       = "gs://${google_storage_bucket.datasets.name}"
}

output "ingest_job" {
  description = "Cloud Run Job name, if created."
  value       = length(google_cloud_run_v2_job.ingest) > 0 ? google_cloud_run_v2_job.ingest[0].name : null
}
