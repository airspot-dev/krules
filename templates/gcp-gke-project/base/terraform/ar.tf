resource "google_artifact_registry_repository" "artifact-registry" {
    provider = google-beta

    project       = var.primary_target.project_id
    location      = var.primary_target.region
    repository_id = var.project_name
    description   = "Image registry for {{ project_name }}"
    format        = "DOCKER"
}

