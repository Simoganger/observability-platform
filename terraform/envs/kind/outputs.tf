output "kubeconfig_context" {
  value = "kind-${var.cluster_name}"
}

output "grafana_admin_password" {
  value     = module.bootstrap.grafana_admin_password
  sensitive = true
}

output "argocd_admin_password_command" {
  value = module.bootstrap.argocd_admin_password_command
}

output "next_steps" {
  value = <<-EOT
    kubectl config use-context kind-${var.cluster_name}
    make ui            # port-forward Grafana :3000, Argo CD :8080, Prometheus :9090, Alertmanager :9093
    terraform -chdir=terraform/envs/kind output -raw grafana_admin_password
  EOT
}
