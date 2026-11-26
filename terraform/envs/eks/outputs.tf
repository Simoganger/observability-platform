output "configure_kubectl" {
  value = "aws eks update-kubeconfig --region ${var.region} --name ${module.eks.cluster_name}"
}

# Paste these into gitops/platform/{loki,tempo}/values-eks.yaml
output "loki_bucket" { value = aws_s3_bucket.telemetry["loki"].id }
output "loki_role_arn" { value = aws_iam_role.telemetry["loki"].arn }
output "tempo_bucket" { value = aws_s3_bucket.telemetry["tempo"].id }
output "tempo_role_arn" { value = aws_iam_role.telemetry["tempo"].arn }

output "grafana_admin_password" {
  value     = module.bootstrap.grafana_admin_password
  sensitive = true
}
