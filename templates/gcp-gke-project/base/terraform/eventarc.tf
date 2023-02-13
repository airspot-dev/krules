# Enable Eventarc to manage GKE clusters
# This is usually done with: gcloud eventarc gke-destinations init
#
# Eventarc creates a separate Event Forwarder pod for each trigger targeting a
# GKE service, and  requires explicit permissions to make changes to the
# cluster. This is done by granting permissions to a special service account
# (the Eventarc P4SA) to manage resources in the cluster. This needs to be done
# once per Google Cloud project.

# Make sure the Eventarc Service Agent is created upfront before
# granting permissions.


data "google_project" "projects" {
    for_each = var.all_projects

    project_id = "${each.key}"
}

resource "google_project_service" "eventarc-service" {
    for_each = var.all_projects
    project = "${ each.key }"
    service            = "eventarc.googleapis.com"
    disable_on_destroy = false
}

resource "google_project_service" "cloudresourcemanager-service" {
    for_each = var.all_projects
    project = "${ each.key }"
    service            = "cloudresourcemanager.googleapis.com"
    disable_on_destroy = false
}

resource "google_project_iam_binding" "computeViewer-iam-binding" {
    for_each = var.all_projects
    project = "${ each.key }"
    role    = "roles/compute.viewer"

    members = [
        "serviceAccount:service-${data.google_project.projects[each.key].number}@gcp-sa-eventarc.iam.gserviceaccount.com"
    ]

    depends_on = [
        google_project_service.eventarc-service
    ]
}

resource "google_project_iam_binding" "containerDeveloper-iam-binding" {
    for_each = var.all_projects
    project = "${ each.key }"
    role    = "roles/container.developer"

    members = [
        "serviceAccount:service-${data.google_project.projects[each.key].number}@gcp-sa-eventarc.iam.gserviceaccount.com"
    ]

    depends_on = [
        google_project_service.eventarc-service
    ]
}

resource "google_project_iam_binding" "serviceAccountAdmin-iam-binding" {
    for_each = var.all_projects
    project = "${ each.key }"
    role    = "roles/iam.serviceAccountAdmin"

    members = [
        "serviceAccount:service-${data.google_project.projects[each.key].number}@gcp-sa-eventarc.iam.gserviceaccount.com"
    ]

    depends_on = [
        google_project_service.eventarc-service
    ]
}

resource "google_project_service_identity" "eventarc-service-identity" {
    provider = google-beta

    for_each = var.all_projects
    project = "${ each.key }"
    service = "eventarc.googleapis.com"
    depends_on = [
        google_project_service.eventarc-service,
        google_project_service.cloudresourcemanager-service
    ]
}

##################### TRIGGERS ################################
// Example: how to receive events from Pub/Sub (See pubsub.tf)
/*
resource "google_eventarc_trigger" "pubsub-ingestion-message-published" {
    for_each = var.targets

    project         = each.value.project_id
    name            = "${var.project_name}-pubsub-message-published-${each.key}"
    location        = "${each.value.region}"
    service_account = "${data.google_project.projects[each.value.project].number}-compute@developer.gserviceaccount.com"
    matching_criteria {
            attribute = "type"
            value     = "google.cloud.pubsub.topic.v1.messagePublished"
    }
    transport {
        pubsub {
            topic     = "${var.ingestion_topic_basename}-${each.key}"
        }
    }
    destination {
            gke {
                    cluster   = "${each.value.cluster}"
                    location  = "${each.value.zone}"
                    namespace = "knative-eventing"
                    service   = "kafka-broker-ingress"
                    path      = "${each.value.namespace}/pubsub-ingested"
            }
    }
    depends_on = [
        google_pubsub_topic.ingestion,
        google_project_service.eventarc-service
    ]
}
*/
