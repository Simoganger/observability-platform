# =============================================================================
# Bootstraps GitOps on any cluster:
#   1. namespaces + the few secrets that must never live in Git
#   2. Argo CD (Helm) — afterwards it manages ITSELF from gitops/platform/argocd
#   3. the root "app-of-apps" Application → everything else comes from Git
# =============================================================================
locals {
  repo_root = abspath("${path.module}/../../..")
}

resource "kubernetes_namespace_v1" "argocd" {
  count = var.install_argocd ? 1 : 0
  metadata {
    name = "argocd"
  }
}

resource "kubernetes_namespace_v1" "observability" {
  metadata {
    name = var.observability_namespace
    labels = {
      team                                 = "sre"
      "pod-security.kubernetes.io/enforce" = "privileged" # node-exporter & log agents need host access
    }
  }
}

# ------------------------------------------------------------------ secrets ---
resource "random_password" "grafana" {
  length  = 24
  special = false
}

resource "kubernetes_secret_v1" "grafana_admin" {
  metadata {
    name      = "grafana-admin"
    namespace = kubernetes_namespace_v1.observability.metadata[0].name
  }
  data = {
    admin-user     = "admin"
    admin-password = var.grafana_admin_password != "" ? var.grafana_admin_password : random_password.grafana.result
  }
}

resource "kubernetes_secret_v1" "alertmanager_incident" {
  metadata {
    name      = "alertmanager-incident-secrets"
    namespace = kubernetes_namespace_v1.observability.metadata[0].name
  }
  data = {
    pagerduty-routing-key = var.pagerduty_routing_key
    slack-webhook-url     = var.slack_webhook_url
  }
}

resource "kubernetes_secret_v1" "repo" {
  count = var.gitops_repo_token != "" ? 1 : 0
  metadata {
    name      = "gitops-repo"
    namespace = "argocd"
    labels    = { "argocd.argoproj.io/secret-type" = "repository" }
  }
  data = {
    type     = "git"
    url      = var.gitops_repo_url
    username = "git"
    password = var.gitops_repo_token
  }
  depends_on = [helm_release.argocd]
}

# ------------------------------------------------------------------ Argo CD ---
resource "helm_release" "argocd" {
  count      = var.install_argocd ? 1 : 0
  name       = "argocd"
  namespace  = kubernetes_namespace_v1.argocd[0].metadata[0].name
  repository = "https://argoproj.github.io/argo-helm"
  chart      = "argo-cd"
  version    = var.argocd_chart_version
  timeout    = 600
  wait       = true

  # Same values Argo CD will later apply to itself …
  values = [file("${local.repo_root}/gitops/platform/argocd/values.yaml")]
  # … minus ServiceMonitors: their CRD arrives later with kube-prometheus-stack.
  set = [
    for c in ["controller", "server", "repoServer", "applicationSet", "notifications"] :
    { name = "${c}.metrics.serviceMonitor.enabled", value = "false" }
  ]

  # From now on Argo CD owns its own release.
  lifecycle {
    ignore_changes = all
  }
}

# --------------------------------------------------------- root app-of-apps ---
resource "helm_release" "root_app" {
  name       = "observability-root"
  namespace  = "argocd"
  repository = "https://argoproj.github.io/argo-helm"
  chart      = "argocd-apps"
  version    = var.argocd_apps_chart_version

  values = [yamlencode({
    applications = {
      observability-root = {
        namespace  = "argocd"
        project    = "default"
        finalizers = ["resources-finalizer.argocd.argoproj.io"]
        source = {
          repoURL        = var.gitops_repo_url
          targetRevision = var.gitops_revision
          path           = "gitops/root"
          helm = {
            valueFiles = ["values.yaml", "values-${var.environment}.yaml"]
            parameters = [
              { name = "global.repoURL", value = var.gitops_repo_url },
              { name = "global.targetRevision", value = var.gitops_revision },
              { name = "global.env", value = var.environment },
            ]
          }
        }
        destination = {
          server    = "https://kubernetes.default.svc"
          namespace = "argocd"
        }
        syncPolicy = {
          automated   = { prune = true, selfHeal = true }
          syncOptions = ["CreateNamespace=true"]
        }
      }
    }
  })]

  depends_on = [
    helm_release.argocd,
    kubernetes_secret_v1.repo,
    kubernetes_secret_v1.grafana_admin,
    kubernetes_secret_v1.alertmanager_incident,
  ]
}
