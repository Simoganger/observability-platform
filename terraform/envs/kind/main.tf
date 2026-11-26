# =============================================================================
# Local lab: multi-node kind cluster whose control plane exposes its metrics
# (etcd, scheduler, controller-manager, kube-proxy) like a self-managed cluster.
# =============================================================================
locals {
  # Bind control-plane metrics on 0.0.0.0 so Prometheus can scrape them.
  control_plane_patches = [
    <<-YAML
    kind: ClusterConfiguration
    controllerManager:
      extraArgs:
        - name: bind-address
          value: 0.0.0.0
    scheduler:
      extraArgs:
        - name: bind-address
          value: 0.0.0.0
    etcd:
      local:
        extraArgs:
          - name: listen-metrics-urls
            value: http://0.0.0.0:2381
    YAML
    ,
    <<-YAML
    kind: KubeProxyConfiguration
    metricsBindAddress: 0.0.0.0:10249
    YAML
  ]
}

resource "kind_cluster" "this" {
  name           = var.cluster_name
  node_image     = var.node_image
  wait_for_ready = true

  kind_config {
    kind        = "Cluster"
    api_version = "kind.x-k8s.io/v1alpha4"

    node {
      role                   = "control-plane"
      kubeadm_config_patches = local.control_plane_patches
    }

    dynamic "node" {
      for_each = range(var.worker_count)
      content {
        role = "worker"
      }
    }
  }
}

module "bootstrap" {
  source = "../../modules/argocd-bootstrap"

  environment            = "kind"
  gitops_repo_url        = var.gitops_repo_url
  gitops_revision        = var.gitops_revision
  gitops_repo_token      = var.gitops_repo_token
  pagerduty_routing_key  = var.pagerduty_routing_key
  slack_webhook_url      = var.slack_webhook_url
  grafana_admin_password = var.grafana_admin_password

  depends_on = [kind_cluster.this]
}
