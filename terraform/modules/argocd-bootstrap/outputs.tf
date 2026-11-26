output "grafana_admin_password" {
  description = "Grafana admin password (user: admin)."
  value       = kubernetes_secret_v1.grafana_admin.data["admin-password"]
  sensitive   = true
}

output "argocd_admin_password_command" {
  description = "Command that prints the initial Argo CD admin password."
  value       = "kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d"
}
