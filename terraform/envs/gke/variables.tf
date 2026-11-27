variable "project_id" {
  type = string
}

variable "region" {
  type    = string
  default = "europe-west1"
}

variable "cluster_name" {
  type    = string
  default = "gke-observability"
}

variable "machine_type" {
  type    = string
  default = "e2-standard-4"
}

variable "node_min" {
  description = "Min nodes PER ZONE (regional cluster → x3)."
  type        = number
  default     = 1
}

variable "node_max" {
  type    = number
  default = 3
}

variable "gitops_repo_url" {
  type = string
}

variable "gitops_revision" {
  type    = string
  default = "main"
}

variable "gitops_repo_token" {
  type      = string
  default   = ""
  sensitive = true
}

variable "pagerduty_routing_key" {
  type      = string
  default   = "REPLACE_ME"
  sensitive = true
}

variable "slack_webhook_url" {
  type      = string
  default   = "https://hooks.slack.com/services/REPLACE/ME/PLEASE"
  sensitive = true
}

variable "keycloak_database" {
  description = "PostgreSQL for Keycloak (host, database, username, password). Required for SSO: docs/sso.md."
  type = object({
    host     = string
    database = string
    username = string
    password = string
  })
  default   = null
  sensitive = true
}
