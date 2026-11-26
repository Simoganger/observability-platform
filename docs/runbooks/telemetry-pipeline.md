# Runbook: telemetry pipeline (OTelCollector*, LokiUnavailable, TempoUnavailable, PrometheusOTLPIngestionStalled)

**Meaning:** we are losing (or about to lose) observability data. Treat this as a blind spot: other alerts may not fire.

Open **Telemetry Pipeline Health** (`/d/telemetry-pipeline`).

| Alert | Check | Fix |
|---|---|---|
| OTelCollectorDown | `kubectl -n observability get pods -l app.kubernetes.io/instance=otel-<x>`; `kubectl logs` | OOMKilled → raise `resources.limits.memory` in `gitops/platform/otel-<x>/values*.yaml`; config error → see `gitops-validate` CI |
| OTelCollectorExportFailures | Which `exporter`? → that backend's pods / logs | Restore the backend; collectors retry with persistent queues |
| OTelCollectorQueueNearlyFull | Queue fill per exporter | Backend slow → scale it; gateway saturated → raise HPA max / replicas |
| OTelCollectorRefusingData | `memory_limiter` back-pressure | More memory / replicas on the gateway; check for a cardinality explosion |
| LokiUnavailable | `kubectl -n observability get pods -l app.kubernetes.io/name=loki` | PVC full (*Fullest volumes*) → expand; object-store credentials (IRSA / WI) |
| TempoUnavailable | Tempo pods, storage | As above. RED metrics keep working (computed in the gateway) |
| PrometheusOTLPIngestionStalled | Gateway logs for `otlphttp/prometheus` errors | Prometheus OTLP receiver enabled? (`enableOTLPReceiver`) |

**Alertmanager notifications failed** (panel): pages are not reaching PagerDuty/Slack. Check the `alertmanager-incident-secrets` secret values.
