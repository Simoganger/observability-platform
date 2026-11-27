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
    https://grafana.${var.domain}    https://argocd.${var.domain}    https://keycloak.${var.domain}
    make sso-users     # SSO logins: alice (sre-team → admin), bob (stakeholders → viewer)
    make lab-ca        # trust the lab CA to silence browser certificate warnings
    make ui            # port-forward Prometheus :9090, Alertmanager :9093, OpenCost, demo
  EOT
}

output "keycloak_admin_password" {
  description = "Keycloak admin console (user: admin)."
  value       = module.bootstrap.keycloak_admin_password
  sensitive   = true
}

output "demo_user_password" {
  description = "Password of the demo SSO users alice (sre-team) and bob (stakeholders)."
  value       = module.bootstrap.demo_user_password
  sensitive   = true
}
