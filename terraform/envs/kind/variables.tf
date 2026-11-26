variable "cluster_name" {
  type    = string
  default = "observability"
}

variable "node_image" {
  description = "kindest/node image; null = kind's default for the installed kind version."
  type        = string
  default     = null
}

variable "worker_count" {
  type    = number
  default = 2
}

variable "gitops_repo_url" {
  description = "Your fork of this repo, e.g. https://github.com/<you>/observability-lab.git"
  type        = string
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

variable "grafana_admin_password" {
  type      = string
  default   = ""
  sensitive = true
}
