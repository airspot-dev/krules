// Example: how to create Google Cloud Storage bucket
/*
resource "google_storage_bucket" "default-bucket" {
    for_each = var.targets
    project       = "${each.value.project_id}"
    name          = "${each.value.project_id}-${var.project_name}-${each.key}"
    location      = "${each.value.region}"
    force_destroy = true

    uniform_bucket_level_access = true
}
*/