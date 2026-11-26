module "bootstrap" {
  source = "../../modules/argocd-bootstrap"

  environment           = "eks"
  gitops_repo_url       = var.gitops_repo_url
  gitops_revision       = var.gitops_revision
  gitops_repo_token     = var.gitops_repo_token
  pagerduty_routing_key = var.pagerduty_routing_key
  slack_webhook_url     = var.slack_webhook_url

  depends_on = [module.eks, kubernetes_storage_class_v1.gp3]
}
