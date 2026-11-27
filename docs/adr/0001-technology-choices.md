# ADR 0001 — Technology choices

**Status:** accepted · **Date:** 2026-11-26

## Context
We need full-stack Kubernetes observability (metrics, logs, traces, events) that is CNCF-first, vendor-neutral, GitOps-delivered and portable across kind, EKS, GKE and existing clusters. It must still let teams use commercial tools (Datadog) where the business wants them.

## Decisions

| Area | Chosen | Considered | Rationale |
|---|---|---|---|
| Instrumentation & pipeline | **OpenTelemetry** (Operator + Collector) | Vendor agents, Fluent Bit + Prom agent | One CNCF standard for every signal. Backends become swappable config, not re-instrumentation. Operator gives zero-code onboarding |
| Log shipper | **OTel Collector filelog** | **Fluent Bit** (CNCF graduated), Vector, Promtail (deprecated) | One agent per node instead of two; same k8s enrichment for all signals. Fluent Bit remains a good choice when you need its plugin ecosystem; it can ship OTLP to the gateway |
| Metrics | **Prometheus** (Operator) | Mimir, VictoriaMetrics, Datadog | CNCF graduated, ecosystem standard, native OTLP since v3. Long-term storage via remote-write (Thanos/Mimir/managed) when needed |
| Logs backend | **Loki** | Elasticsearch/OpenSearch, ClickHouse | Object-storage cost model, label model aligned with Prometheus, native OTLP. Trade-off: no full-text index (fine for ops logs) |
| Traces backend | **Tempo** | **Jaeger v2** (CNCF graduated), Zipkin, Elastic APM | Object-storage only, TraceQL, deep Grafana correlation. Jaeger v2 is a drop-in alternative: swap the `otlp/tempo` exporter and the datasource |
| RED metrics | **OTel spanmetrics/servicegraph connectors** | Tempo metrics-generator | Backend-agnostic, computed before tail sampling (accurate), feeds Datadog too |
| Sampling | **Tail sampling in gateway** | Head sampling | Keeps every error and slow trace at ~25 % of the cost |
| GitOps | **Argo CD** | Flux | UI for operators and stakeholders, app-of-apps, sync waves, metrics for DORA |
| IaC | **Terraform** | Pulumi, Crossplane | Most widely adopted; providers for kind/AWS/GCP; only used for bootstrap |
| Incident mgmt | **Alertmanager → PagerDuty + Slack** | Opsgenie (end-of-sale), Grafana IRM, incident.io | PagerDuty is the market leader; receivers are swappable config |
| Cost | **OpenCost** | Kubecost | CNCF incubating, open spec, Prometheus-native |
| Commercial | **Datadog** (optional) | New Relic, Dynatrace | Most requested in industry; enabled as a second destination, not a dependency |
| Ingress | **Gateway API** programmed by **Istio** (pluggable: Envoy Gateway, or an existing controller) + **cert-manager** | ingress-nginx (retired 2026), Traefik, Cilium, cloud load-balancer controllers | Gateway API is the successor of Ingress and implementation-neutral, so the controller is one setting (`global.gatewayProvider`). Istio (CNCF graduated) is the default: a mature, conformant implementation that leaves room to adopt the mesh later. Only istiod runs, with no sidecars. Envoy Gateway is the lighter alternative. One Gateway with per-host listeners; cert-manager issues certificates from the listeners. Off for `existing` clusters, which bring their own |
| Identity / SSO | **Keycloak** (OIDC) | Dex, Authentik, Okta / Entra ID directly | CNCF incubating, full IdP (federates LDAP/AD and upstream IdPs), groups claim drives Grafana and Argo CD roles. Trade-off: one more stateful service (PostgreSQL in the cloud). Swappable for any OIDC IdP by changing URLs only |

## Consequences
* Changing a backend is a config change in `gitops/platform/otel-gateway`, with no application change.
* Loki/Tempo require object storage in production (provisioned by Terraform for EKS/GKE).
* Teams must emit server spans (via auto-instrumentation) to get SLOs automatically.
