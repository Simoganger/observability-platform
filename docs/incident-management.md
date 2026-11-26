# Incident management

## Signal → human

```
PrometheusRule ──► Alertmanager ──┬─ severity=critical ─► PagerDuty (Events API v2) ─► on-call phone
   (runbook_url,                  │                     └► Slack #incidents
    dashboard_url)                ├─ severity=warning ──► Slack #alerts
                                  └─ Watchdog ──────────► dead-man's switch (enable in prod)
```

* **Grouping:** `alertname, cluster, namespace, service_name`. One incident per broken thing, not one per pod.
* **Inhibition:** a critical alert mutes its own warnings, and `KubeNodeNotReady` mutes pod alerts on that cluster.
* **De-duplication:** PagerDuty dedups on the Alertmanager group key and auto-resolves when the alert resolves (`send_resolved: true`).
* **Context in the page:** summary, description, runbook link, SRE dashboard link and the Prometheus query.

## Severity matrix

| Severity | Examples | Route | Response |
|---|---|---|---|
| **critical** (P1/P2) | Fast/medium SLO burn, OTel collector down, Loki down, Argo CD app degraded, export queue full | PagerDuty + #incidents | Ack ≤ 5 min, mitigate first |
| **warning** (P3) | Slow SLO burn, latency SLO, export failures, app out of sync, Tempo down | #alerts | Next business day / ticket |
| **info** | InfoInhibitor, informational | none | — |

## Set up PagerDuty

1. PagerDuty → **Services → New service** (e.g. "Kubernetes platform"), with an escalation policy (primary → secondary → manager).
2. **Integrations → Events API v2** and copy the **Integration key**.
3. Store it as `pagerduty-routing-key`:
   * kind/EKS/GKE: `pagerduty_routing_key` in `terraform.tfvars`, then `terraform apply`
   * existing: `PAGERDUTY_ROUTING_KEY=... scripts/create-secrets.sh`
4. Optional: install the PagerDuty Slack app so `/pd` commands work from #incidents.

## Set up Slack

Create an incoming webhook (Slack → Apps → Incoming Webhooks) and store it as `slack-webhook-url`. Channels `#incidents` and `#alerts` are set in `kube-prometheus-stack/values.yaml`.

## Dead-man's switch (production)

`Watchdog` always fires. Route it to a heartbeat monitor (PagerDuty heartbeat, healthchecks.io, Cronitor). If the heartbeat stops, your alerting pipeline is down. Replace the `"null"` receiver on the Watchdog route with:

```yaml
- name: deadmans-switch
  webhook_configs:
    - url_file: /etc/alertmanager/secrets/alertmanager-incident-secrets/heartbeat-url
      send_resolved: false
```

and set `repeat_interval: 1m` on that route.

## Using another tool

Alertmanager has native receivers for **Opsgenie**, **incident.io** and **Splunk On-Call (VictorOps)**, plus webhooks for **Grafana IRM**, **FireHydrant**, **Rootly** and **ServiceNow**. Swap the `pagerduty_configs` block. Routing, grouping and runbooks stay the same.

## Incident lifecycle

1. **Detect**: the page arrives with its runbook link.
2. **Triage**: open the *SRE Command Center*, filtered to the service from the page. Check the situation row, then golden signals, then the deploy annotation ("did we just ship?").
3. **Mitigate**: rollback is `git revert` on the deploy commit (Argo CD syncs it), or use Argo CD → History → Rollback.
4. **Communicate**: status in #incidents every 30 min for P1.
5. **Resolve**: the alert auto-resolves in PagerDuty when the SLI recovers.
6. **Learn**: write a post-mortem (template below) within 5 business days. The time-in-incident and error-budget panels on the Executive dashboard show the impact.

### Post-mortem template

```markdown
# <date> <service> <one-line impact>
**Severity:** P1 · **Duration:** hh:mm · **Error budget consumed:** x %
## Impact      — who/what was affected, numbers from the Executive dashboard
## Timeline    — detect / ack / mitigate / resolve (UTC)
## Root cause  — 5 whys, link traces/logs
## What went well / what didn't
## Action items — owner, ticket, due date (prevent · detect · mitigate)
```
