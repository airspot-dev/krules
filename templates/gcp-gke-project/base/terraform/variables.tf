variable "project_name" {
    description = "The name of the project. This is not the Google project id which is target related"
    type = string
}

variable "primary_target" {
    description = "Primary target. Usually the first target in the list of targets"
    type = map
}

variable "targets" {
    description = "Deployment targets"
    type = map
/*    type = list(object({
       name = string
       project = string
       region = string
       zone = string
       cluster = string
       namespace = string
       location = string
       require_approval = bool
    }))*/
}

variable "all_projects" {
    description="All involved google projects"
    type = set(string)
}

variable "ingestion_topic_basename" {
    description="Pub/Sub source topic basename"
    type = string
}

