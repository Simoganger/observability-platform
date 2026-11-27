variable "region" {
  type    = string
  default = "eu-west-1"
}

variable "cluster_name" {
  type    = string
  default = "eks-observability"
}

variable "kubernetes_version" {
  type    = string
  default = "1.34"
}

variable "vpc_cidr" {
  type    = string
  default = "10.42.0.0/16"
}

variable "node_instance_types" {
  type    = list(string)
  default = ["m6i.xlarge", "m6a.xlarge"]
}

variable "node_min" {
  type    = number
  default = 3
}

variable "node_max" {
  type    = number
  default = 6
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
