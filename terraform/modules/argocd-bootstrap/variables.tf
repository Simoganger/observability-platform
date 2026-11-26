variable "environment" {
  description = "GitOps environment: selects values-<env>.yaml everywhere (kind | eks | gke | existing)."
  type        = string
  validation {
    condition     = contains(["kind", "eks", "gke", "existing"], var.environment)
    error_message = "environment must be one of kind, eks, gke, existing."
  }
}

variable "gitops_repo_url" {
  description = "HTTPS URL of the Git repository Argo CD syncs from (this repo)."
  type        = string
}

variable "gitops_revision" {
  description = "Branch, tag or commit Argo CD tracks."
  type        = string
  default     = "main"
}

variable "gitops_repo_token" {
  description = "Optional GitHub token (read-only, contents:read) for a PRIVATE repo."
  type        = string
  default     = ""
  sensitive   = true
}

variable "argocd_chart_version" {
  description = "argo-cd Helm chart version (keep in sync with gitops/root/values.yaml)."
  type        = string
  default     = "10.20.0"
}

variable "argocd_apps_chart_version" {
  description = "argocd-apps Helm chart version (renders the root Application)."
  type        = string
  default     = "2.0.10"
}

variable "install_argocd" {
  description = "Install Argo CD. Set false to reuse an Argo CD that already runs in the cluster."
  type        = bool
  default     = true
}

variable "observability_namespace" {
  type    = string
  default = "observability"
}

variable "grafana_admin_password" {
  description = "Grafana admin password. Empty → a random one is generated (see outputs)."
  type        = string
  default     = ""
  sensitive   = true
}

variable "pagerduty_routing_key" {
  description = "PagerDuty Events API v2 integration (routing) key for critical alerts."
  type        = string
  default     = "REPLACE_ME"
  sensitive   = true
}

variable "slack_webhook_url" {
  description = "Slack incoming-webhook URL for #alerts / #incidents."
  type        = string
  default     = "https://hooks.slack.com/services/REPLACE/ME/PLEASE"
  sensitive   = true
}
