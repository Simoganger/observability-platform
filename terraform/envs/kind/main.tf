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

      # Host :80/:443 → the Envoy gateway's fixed node ports (gitops/platform/ingress/values-kind.yaml).
      extra_port_mappings {
        container_port = 30080
        host_port      = 80
        listen_address = "127.0.0.1"
      }
      extra_port_mappings {
        container_port = 30443
        host_port      = 443
        listen_address = "127.0.0.1"
      }
    }

    dynamic "node" {
      for_each = range(var.worker_count)
      content {
        role = "worker"
      }
    }
  }
}

# ----------------------------------------------------- in-cluster DNS ---
# *.<domain> resolves to 127.0.0.1 — right for your browser, wrong inside a pod.
# Grafana and Argo CD must reach Keycloak at the SAME public URL the browser
# uses (OIDC issuer), so CoreDNS answers those names with the gateway Service.
# This is kind's default Corefile plus the `rewrite` line.
resource "kubernetes_config_map_v1_data" "coredns" {
  metadata {
    name      = "coredns"
    namespace = "kube-system"
  }
  force = true
  data = {
    Corefile = <<-EOT
      .:53 {
          errors
          health {
             lameduck 5s
          }
          ready
          rewrite stop name regex ^[^.]+\.${replace(var.domain, ".", "\\.")}\.$ platform-gateway.envoy-gateway-system.svc.cluster.local. answer auto
          kubernetes cluster.local in-addr.arpa ip6.arpa {
             pods insecure
             fallthrough in-addr.arpa ip6.arpa
             ttl 30
          }
          prometheus :9153
          forward . /etc/resolv.conf {
             max_concurrent 1000
          }
          cache 30
          loop
          reload
          loadbalance
      }
    EOT
  }
  depends_on = [kind_cluster.this]
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
