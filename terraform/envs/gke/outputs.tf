output "configure_kubectl" {
  value = "gcloud container clusters get-credentials ${google_container_cluster.this.name} --region ${var.region} --project ${var.project_id}"
}

# Paste these into gitops/platform/{loki,tempo}/values-gke.yaml
output "loki_bucket" { value = google_storage_bucket.telemetry["loki"].name }
output "loki_gsa_email" { value = google_service_account.telemetry["loki"].email }
output "tempo_bucket" { value = google_storage_bucket.telemetry["tempo"].name }
output "tempo_gsa_email" { value = google_service_account.telemetry["tempo"].email }

output "grafana_admin_password" {
  value     = module.bootstrap.grafana_admin_password
  sensitive = true
}

output "keycloak_admin_password" {
  description = "Keycloak admin console (user: admin)."
  value       = module.bootstrap.keycloak_admin_password
  sensitive   = true
}
