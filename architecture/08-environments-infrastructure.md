# 8. Environments & infrastructure

One Git tree, four targets. The environment name selects `values-<env>.yaml` everywhere (root catalog and every component).

## 8.1 Side by side

| | **kind** (lab) | **eks** | **gke** | **existing** (brownfield) |
|---|---|---|---|---|
| Created by | Terraform `envs/kind` (tehcyx/kind) | Terraform `envs/eks` | Terraform `envs/gke` | you |
| Nodes | 1 control plane + 2 workers | managed node group 3–6 × m6i/m6a.xlarge, private subnets | regional node pool, autoscaling | yours |
| Argo CD | installed, single replicas | HA (redis-ha, 2× server/repo-server) | HA | **your** Argo CD (`argocd` disabled) |
| Gateway | provider default (Istio), NodePort + host ports 80/443 | Istio, internet-facing NLB | Istio, external passthrough LB | disabled (bring your own) |
| TLS | lab CA (self-signed) | Let's Encrypt HTTP-01 | Let's Encrypt HTTP-01 | yours |
| Keycloak | dev mode, H2, demo users | 2 replicas, PostgreSQL (RDS) | 2 replicas, PostgreSQL (Cloud SQL) | disabled (your IdP) |
| Prometheus | 1 replica, 3 d / 4 GB | 2 replicas, 15 d, 100 Gi gp3, zone spread | 2 replicas, 15 d, 100 Gi premium-rwo | 1 replica |
| Alertmanager | 1 | 3 (mesh) | 3 | 1 |
| Loki | SingleBinary, filesystem, 72 h | Distributed, S3, 31 d | Distributed, GCS, 31 d | SingleBinary on PVC |
| Tempo | monolithic, local, 72 h | tempo-distributed, S3, 14 d | tempo-distributed, GCS | tempo-distributed, your bucket |
| OTel gateway | 1 | HPA 3–10, zone spread | HPA 3–10 | 2 |
| Control-plane metrics | etcd, scheduler, controller-manager, kube-proxy | managed (off) | managed (off) | off |
| Storage identity | — | IRSA | Workload Identity | yours |
| Demo app | on | on | on | off |

## 8.2 kind

```mermaid
flowchart TB
  subgraph host[Laptop · Docker]
    subgraph cp[control-plane node]
      kp[kube-proxy NodePort 30080/30443]
      cpm[etcd · scheduler · controller-manager<br/>metrics bound on 0.0.0.0]
    end
    subgraph w1[worker 1]
      p1[platform pods]
    end
    subgraph w2[worker 2]
      p2[platform pods]
    end
  end
  user([Browser]) -->|127.0.0.1:80/443| kp
  dns[CoreDNS rewrite<br/>*.127.0.0.1.nip.io → gateway Service] -.-> p1 & p2
```

* kubeadm patches bind control-plane metrics to `0.0.0.0` so the stack is monitored like a self-managed cluster.
* The demo image is built locally and loaded with `kind load` (no registry).
* Changing host port mappings requires recreating the cluster.
* Docker needs about 8 GB free for the full stack.

## 8.3 EKS

```mermaid
flowchart TB
  subgraph vpc[VPC · 3 AZs]
    subgraph pub[public subnets]
      nlb[NLB<br/>gateway Service]
      nat[NAT gateway · single for the lab]
    end
    subgraph priv[private subnets]
      ng[managed node group<br/>3–6 nodes]
    end
  end
  eks[EKS control plane<br/>IRSA · addons: vpc-cni, coredns, kube-proxy,<br/>pod-identity-agent, ebs-csi]
  s3l[(S3 loki-chunks)]
  s3t[(S3 tempo-traces)]
  rds[(PostgreSQL for Keycloak<br/>you provide)]
  dns[(DNS *.domain)] --> nlb --> ng
  ng --> s3l & s3t
  ng --> rds
  eks --- ng
```

* `gp3` StorageClass (EBS CSI with its own IRSA role) for Prometheus, Alertmanager, Loki and Tempo ingesters.
* Buckets: SSE, public access blocked, lifecycle expiry = retention + 7 days, one IRSA role per store.
* Production hardening left to you: one NAT gateway per AZ, private API endpoint, `force_destroy = false` on buckets.

## 8.4 GKE

* VPC-native cluster (secondary ranges for pods and services), release channel, Workload Identity pool `<project>.svc.id.goog`.
* Dedicated node service account; autoscaling node pool.
* GCS buckets with a Google service account per store, bound to the Kubernetes service account via Workload Identity.
* The cloud's own Gateway controller can be used instead of Istio with `gatewayProvider: external` and `gateway.className: gke-l7-global-external-managed`.

## 8.5 Existing cluster

```mermaid
flowchart LR
  you[Your Argo CD] -->|one Application| root[gitops/root · values-existing.yaml]
  root --> obs[observability stack]
  sec[scripts/create-secrets.sh] --> k8s[(secrets)]
  obs -->|annotation opt-in| wl[your workloads]
```

The platform drops in next to running workloads: it discovers ServiceMonitors/PrometheusRules from every namespace, leaves ingress, certificates and identity to you, and onboards workloads with one annotation. Options to reuse an existing Prometheus Operator or Grafana are in [docs/onboarding-existing-cluster.md](../docs/onboarding-existing-cluster.md).

## 8.6 What an environment file typically changes

| File | kind | eks / gke |
|---|---|---|
| `root/values-<env>.yaml` | `env: kind` | Tempo chart → `tempo-distributed` |
| `kube-prometheus-stack/values-<env>.yaml` | small retention, control-plane ports, Grafana URLs + lab TLS skip | HA replicas, storage class, Grafana URLs |
| `loki/` `tempo/` | filesystem / local | object storage, identity annotations, replicas |
| `otel-*/values-<env>.yaml` | — | cluster name, gateway HPA, Tempo endpoint |
| `ingress/values-<env>.yaml` | domain, NodePort, lab CA | domain, LB annotations |
| `keycloak/values-<env>.yaml` | dev mode, demo users | production mode, DB secret, replicas |
| `argocd/values-<env>.yaml` | domain, OIDC (TLS skip) | domain, OIDC, HA |
