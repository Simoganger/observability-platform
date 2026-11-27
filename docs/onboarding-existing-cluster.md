# Plugging the platform into an existing cluster

This repo is designed to drop into a cluster that already runs workloads, with or without Argo CD.

## 1. Prerequisites

| Requirement | Why |
|---|---|
| Kubernetes ≥ 1.29 | Native sidecars, EndpointSlices |
| A default StorageClass | Prometheus / Loki / Alertmanager PVCs |
| Object storage bucket (S3/GCS/Azure) | tempo-distributed (and Loki at scale) |
| `observability` namespace may run privileged pods | node-exporter and the log agent read host paths |
| Argo CD ≥ 2.6 (or let us install it) | Multi-source Applications |

## 2. Configure

1. Fork the repo and run `scripts/configure-repo.sh <github-owner> <dockerhub-user>`.
2. Replace the remaining `CHANGE_ME` values (cluster name) in:
   * `gitops/platform/kube-prometheus-stack/values-existing.yaml`: `externalLabels.cluster`
   * `gitops/platform/otel-agent/values-existing.yaml` and `otel-cluster/values-existing.yaml`: `k8s.cluster.name`
   * `gitops/platform/opencost/values-existing.yaml`
   * `gitops/platform/tempo/values-existing.yaml`: bucket and endpoint
3. Review the toggles in `gitops/root/values-existing.yaml`.

**Already running Prometheus Operator?** Set `crds.enabled: false` and `prometheusOperator.enabled: false` in `kube-prometheus-stack/values-existing.yaml`. Alternatively, disable the component and point the OTel gateway's `otlphttp/prometheus` exporter at your Prometheus (which needs `--web.enable-otlp-receiver`).

**Already running Grafana?** Set `grafana.enabled: false`, then import `gitops/observability-config/base/dashboards/*.json` and the datasources from `datasources.yaml`.

## 3. Secrets

```bash
PAGERDUTY_ROUTING_KEY=... SLACK_WEBHOOK_URL=https://hooks.slack.com/services/... \
  scripts/create-secrets.sh
```

For SSO against your own identity provider, also pass `GRAFANA_OIDC_CLIENT_SECRET` / `ARGOCD_OIDC_CLIENT_SECRET` and follow [sso.md](sso.md#using-another-keycloak-or-idp). Ingress, cert-manager and Keycloak are disabled for this environment by default; enable them in `gitops/root/values-existing.yaml` if your cluster lacks them.

In production, manage `alertmanager-incident-secrets` and `grafana-admin` with External Secrets Operator, Vault or your cloud secret manager. The names and keys are the contract.

## 4. Deploy

**You already run Argo CD.** Apply one Application:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: observability-root
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/<you>/observability-lab.git
    targetRevision: main
    path: gitops/root
    helm:
      valueFiles: [values.yaml, values-existing.yaml]
      parameters:
        - { name: global.repoURL, value: "https://github.com/<you>/observability-lab.git" }
        - { name: global.env, value: existing }
  destination: { server: https://kubernetes.default.svc, namespace: argocd }
  syncPolicy: { automated: { prune: true, selfHeal: true } }
```

Also add the Application health check from `gitops/platform/argocd/values.yaml` (`resource.customizations.health.argoproj.io_Application`) to your `argocd-cm`, so sync waves are respected across apps.

**No Argo CD yet.** Use the Terraform module directly:

```hcl
module "observability" {
  source          = "github.com/<you>/observability-lab//terraform/modules/argocd-bootstrap"
  environment     = "existing"
  gitops_repo_url = "https://github.com/<you>/observability-lab.git"
}
```

## 5. Onboard workloads

| Signal | What you do | What you get |
|---|---|---|
| **Traces + RED metrics + SLO** | Add one pod annotation (below) | Spans, span-metrics, service map, burn-rate alerts, SRE dashboard rows |
| **Logs** | Nothing; write to stdout (JSON preferred) | Logs in Loki with namespace/pod/deployment labels; `trace_id` in JSON → trace links |
| **Custom metrics** | Expose `/metrics` and add a `ServiceMonitor`/`PodMonitor` (any namespace) **or** push OTLP | Prometheus scrapes it (selectors are cluster-wide) |
| **Kubernetes events** | Nothing | Warning events on the SRE dashboard, 31-day history |
| **Cost** | Label namespaces with `team`, `cost-center` | Cost per namespace / team on the Executive dashboard |

```yaml
spec:
  template:
    metadata:
      annotations:
        instrumentation.opentelemetry.io/inject-java: "observability/default"     # or -python, -nodejs, -dotnet
        # Go (eBPF, needs privileged + the binary path):
        # instrumentation.opentelemetry.io/inject-go: "observability/default"
        # instrumentation.opentelemetry.io/otel-go-auto-target-exe: "/app/server"
      labels:
        app.kubernetes.io/name: checkout          # → service.name
        app.kubernetes.io/version: "1.4.2"        # → service.version
```

Or opt in a whole namespace: `kubectl annotate ns shop instrumentation.opentelemetry.io/inject-java=observability/default`.

Already instrumented with an OTel SDK? Point it at `http://$(NODE_IP):4318` (node agent) or `http://otel-gateway.observability:4318`.

## 6. Verify

```bash
make status                                       # all Applications Synced/Healthy
kubectl -n observability get pods
# Grafana → Explore → Tempo → Service graph  (your service appears after the first requests)
# Grafana → SRE Command Center → Service = <yours>
```
