#!/usr/bin/env python3
"""Dashboards-as-code: regenerates the Grafana JSON in gitops/observability-config/base/dashboards.

Usage: python3 scripts/generate-dashboards.py   (then commit the JSON; CI validates it)
"""
import json, sys, os

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "gitops", "observability-config", "base", "dashboards")
PROM = {"type": "prometheus", "uid": "prometheus"}
LOKI = {"type": "loki", "uid": "loki"}
TEMPO = {"type": "tempo", "uid": "tempo"}


class Board:
    def __init__(self):
        self.panels, self.y, self.id = [], 0, 1
        self.x, self.row_h = 0, 0

    def _place(self, w, h):
        if self.x + w > 24:
            self.y += self.row_h
            self.x, self.row_h = 0, 0
        pos = {"x": self.x, "y": self.y, "w": w, "h": h}
        self.x += w
        self.row_h = max(self.row_h, h)
        return pos

    def row(self, title):
        if self.x:
            self.y += self.row_h
        self.x, self.row_h = 0, 0
        self.panels.append({"type": "row", "title": title, "id": self.id, "collapsed": False,
                            "gridPos": {"x": 0, "y": self.y, "w": 24, "h": 1}, "panels": []})
        self.id += 1
        self.y += 1

    def add(self, panel, w, h):
        panel["id"] = self.id
        panel["gridPos"] = self._place(w, h)
        self.id += 1
        self.panels.append(panel)


def t(expr, legend="", instant=False, fmt=None, ref="A"):
    q = {"datasource": PROM, "expr": expr, "refId": ref, "legendFormat": legend or "__auto",
         "range": not instant, "instant": instant}
    if fmt:
        q["format"] = fmt
    return q


def thresholds(steps):
    return {"mode": "absolute", "steps": [{"color": c, "value": v} for c, v in steps]}


def stat(title, expr, unit="none", steps=None, desc="", decimals=None, color_mode="background", graph=False, instant=True):
    fc = {"unit": unit, "thresholds": thresholds(steps or [("green", None)]), "color": {"mode": "thresholds"}}
    if decimals is not None:
        fc["decimals"] = decimals
    return {"type": "stat", "title": title, "description": desc, "datasource": PROM,
            "targets": [t(expr, instant=instant)],
            "fieldConfig": {"defaults": fc, "overrides": []},
            "options": {"reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
                        "colorMode": color_mode, "graphMode": "area" if graph else "none",
                        "textMode": "value", "justifyMode": "center", "orientation": "auto"}}


def ts(title, targets, unit="none", desc="", stack=False, bars=False, min0=True, steps=None, legend_table=False, maxv=None):
    custom = {"drawStyle": "bars" if bars else "line", "lineWidth": 2, "fillOpacity": 60 if bars else 12,
              "gradientMode": "opacity", "showPoints": "never", "spanNulls": True,
              "stacking": {"mode": "normal" if stack else "none", "group": "A"}}
    fc = {"unit": unit, "custom": custom, "color": {"mode": "palette-classic"}}
    if min0:
        fc["min"] = 0
    if maxv is not None:
        fc["max"] = maxv
    if steps:
        fc["thresholds"] = thresholds(steps)
        custom["thresholdsStyle"] = {"mode": "dashed"}
    return {"type": "timeseries", "title": title, "description": desc, "datasource": PROM, "targets": targets,
            "fieldConfig": {"defaults": fc, "overrides": []},
            "options": {"legend": {"displayMode": "table" if legend_table else "list", "placement": "bottom",
                                   "calcs": ["lastNotNull", "max"] if legend_table else []},
                        "tooltip": {"mode": "multi", "sort": "desc"}}}


def bargauge(title, expr, legend, unit, steps, desc="", minv=None, maxv=None, sort=True):
    fc = {"unit": unit, "thresholds": thresholds(steps), "color": {"mode": "thresholds"}}
    if minv is not None:
        fc["min"] = minv
    if maxv is not None:
        fc["max"] = maxv
    expr = f"sort({expr})" if sort else expr
    return {"type": "bargauge", "title": title, "description": desc, "datasource": PROM,
            "targets": [t(expr, legend, instant=True)],
            "fieldConfig": {"defaults": fc, "overrides": []},
            "options": {"reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
                        "orientation": "horizontal", "displayMode": "gradient", "showUnfilled": True,
                        "valueMode": "color", "namePlacement": "left", "sizing": "auto"}}


def pie(title, expr, legend, unit, desc=""):
    return {"type": "piechart", "title": title, "description": desc, "datasource": PROM,
            "targets": [t(expr, legend, instant=True)],
            "fieldConfig": {"defaults": {"unit": unit, "color": {"mode": "palette-classic"}}, "overrides": []},
            "options": {"pieType": "donut", "reduceOptions": {"calcs": ["lastNotNull"], "values": False},
                        "legend": {"displayMode": "table", "placement": "right", "values": ["value", "percent"]},
                        "tooltip": {"mode": "single"}}}


def table(title, targets, desc="", overrides=None, transformations=None, unit="none"):
    return {"type": "table", "title": title, "description": desc, "datasource": PROM, "targets": targets,
            "fieldConfig": {"defaults": {"unit": unit, "custom": {"align": "auto", "cellOptions": {"type": "auto"}}},
                            "overrides": overrides or []},
            "options": {"showHeader": True, "cellHeight": "sm", "footer": {"show": False}},
            "transformations": transformations or []}


def logs(title, expr, desc=""):
    return {"type": "logs", "title": title, "description": desc, "datasource": LOKI,
            "targets": [{"datasource": LOKI, "expr": expr, "refId": "A", "queryType": "range"}],
            "options": {"showTime": True, "wrapLogMessage": True, "sortOrder": "Descending",
                        "enableLogDetails": True, "prettifyLogMessage": False, "dedupStrategy": "none"}}


def text(title, content):
    return {"type": "text", "title": title, "options": {"mode": "markdown", "content": content}}


def dashboard(uid, title, tags, board, templating=None, annotations=None, refresh="1m", time_from="now-24h", desc="", links=None):
    return {
        "uid": uid, "title": title, "tags": tags, "description": desc, "editable": False,
        "schemaVersion": 39, "version": 1, "refresh": refresh, "timezone": "browser",
        "graphTooltip": 1, "time": {"from": time_from, "to": "now"},
        "templating": {"list": templating or []},
        "annotations": {"list": [{
            "builtIn": 1, "datasource": {"type": "grafana", "uid": "-- Grafana --"}, "enable": True,
            "hide": True, "iconColor": "rgba(0, 211, 255, 1)", "name": "Annotations & Alerts", "type": "dashboard"}]
            + (annotations or [])},
        "links": links or [],
        "panels": board.panels,
    }


DEPLOY_ANNOTATION = {
    "name": "Deployments (Argo CD)", "enable": True, "iconColor": "#8F3BB8", "datasource": PROM,
    "expr": 'sum by (name) (changes(argocd_app_sync_total{phase="Succeeded"}[2m])) > 0',
    "step": "1m", "titleFormat": "Deploy: {{name}}", "textFormat": "Argo CD sync succeeded", "useValueForTime": False,
}
INCIDENT_ANNOTATION = {
    "name": "Critical incidents", "enable": True, "iconColor": "#E02F44", "datasource": PROM,
    "expr": 'ALERTS{alertstate="firing", severity="critical"}', "step": "1m",
    "titleFormat": "{{alertname}}", "textFormat": "{{service_name}} {{namespace}}", "useValueForTime": False,
}
LINKS = [
    {"title": "Executive overview", "type": "link", "url": "/d/executive-overview", "icon": "dashboard"},
    {"title": "SRE command center", "type": "link", "url": "/d/sre-command-center", "icon": "dashboard"},
    {"title": "Telemetry pipeline", "type": "link", "url": "/d/telemetry-pipeline", "icon": "dashboard"},
]

# =========================================================================== #
# 1. EXECUTIVE OVERVIEW — for stakeholders / decision making
# =========================================================================== #
b = Board()
b.add(text("", (
    "### Platform health for decision makers\n"
    "**Reliability** is measured against a **99.5 % availability SLO** per service (30-day window). "
    "**Error budget** = how much unreliability we can still \"spend\" on releases and experiments this month. "
    "**Cost** is OpenCost's estimate at today's run-rate. Green = on track · Amber = watch · Red = action needed.")), 24, 3)

b.row("Reliability at a glance (last 30 days)")
b.add(stat("Platform availability", "avg(1 - slo:sli_error:ratio_rate30d)", "percentunit",
           [("red", None), ("orange", 0.99), ("green", 0.995)], decimals=3,
           desc="Average success ratio of all user-facing services over 30 days. Target: 99.5 %."), 5, 5)
b.add(stat("Services meeting SLO", "count(slo:sli_error:ratio_rate30d <= 0.005) / count(slo:sli_error:ratio_rate30d)",
           "percentunit", [("red", None), ("orange", 0.8), ("green", 1)], decimals=0,
           desc="Share of services whose 30-day availability is at or above 99.5 %."), 4, 5)
b.add(stat("Lowest error budget left", "clamp_min(min(slo:error_budget_remaining:ratio), 0)", "percentunit",
           [("red", None), ("orange", 0.25), ("green", 0.5)], decimals=0,
           desc="Error budget left for the worst service. 0 % means freeze risky changes for that service."), 5, 5)
b.add(stat("Open critical incidents", "platform:incidents_open:count", "none",
           [("green", None), ("red", 1)], desc="Distinct critical alert groups currently paging the on-call."), 5, 5)
b.add(stat("Time in incident (30d)", "sum_over_time(platform:incident_active:bool[30d:1m]) * 60", "s",
           [("green", None), ("orange", 3600), ("red", 4 * 3600)], decimals=1,
           desc="Total time with at least one critical incident open during the last 30 days."), 5, 5)

b.row("Service level objectives")
b.add(bargauge("30-day availability by service", "1 - slo:sli_error:ratio_rate30d", "{{service_name}}", "percentunit",
               [("red", None), ("orange", 0.99), ("green", 0.995)], minv=0.98, maxv=1,
               desc="Bars turn red below 99 % and amber below the 99.5 % objective."), 12, 8)
b.add(bargauge("Error budget remaining by service", "clamp_min(slo:error_budget_remaining:ratio, 0)", "{{service_name}}",
               "percentunit", [("red", None), ("orange", 0.25), ("green", 0.5)], minv=0, maxv=1,
               desc="100 % = untouched budget. Services under 25 % should prioritise reliability work."), 12, 8)
b.add(ts("Daily availability trend", [t("1 - slo:sli_error:ratio_rate1d", "{{service_name}}")], "percentunit",
         min0=False, steps=[("red", None), ("green", 0.995)], maxv=1,
         desc="Rolling 24-hour success ratio per service; dashed line = SLO."), 12, 8)
b.add(ts("User-facing latency (p95)", [t("service:latency_p95:seconds_rate5m", "{{service_name}}")], "s",
         steps=[("green", None), ("red", 0.5)], desc="95 % of requests are faster than this. Objective: under 500 ms."), 12, 8)

b.row("Demand")
b.add(stat("Requests served (24h)", "sum(increase(traces_span_metrics_calls_total{span_kind=\"SPAN_KIND_SERVER\"}[24h]))",
           "short", [("blue", None)], color_mode="value", desc="Total requests handled by instrumented services."), 4, 6)
b.add(stat("Failed requests (24h)", "sum(increase(traces_span_metrics_calls_total{span_kind=\"SPAN_KIND_SERVER\", status_code=\"STATUS_CODE_ERROR\"}[24h]))",
           "short", [("green", None), ("orange", 100), ("red", 1000)], color_mode="value"), 4, 6)
b.add(stat("Orders placed (24h)", "sum(increase(shop_orders_total[24h]))", "short", [("purple", None)], color_mode="value",
           decimals=0, desc="Business metric emitted by the demo shop via the OpenTelemetry metrics API."), 4, 6)
b.add(stat("Revenue captured (24h)", "sum(increase(shop_revenue_usd_total[24h]))", "currencyUSD", [("purple", None)],
           color_mode="value", decimals=0, desc="Revenue flowing through checkout — puts reliability in business terms."), 4, 6)
b.add(ts("Traffic by service", [t("service:requests:rate5m", "{{service_name}}")], "reqps", stack=True,
         desc="Requests per second, stacked."), 8, 6)

b.row("Delivery performance (DORA)")
b.add(stat("Deployments (7d)", "sum(increase(argocd_app_sync_total{phase=\"Succeeded\"}[7d]))", "short",
           [("blue", None)], color_mode="value", decimals=0, desc="Successful Argo CD syncs — deployment frequency."), 6, 6)
b.add(stat("Change failure rate (30d)",
           "sum(increase(argocd_app_sync_total{phase=~\"Error|Failed\"}[30d])) / clamp_min(sum(increase(argocd_app_sync_total[30d])), 1)",
           "percentunit", [("green", None), ("orange", 0.15), ("red", 0.3)], decimals=1,
           desc="Share of deployments that failed. Elite teams: < 15 %."), 6, 6)
b.add(ts("Deployments per day", [t("platform:deployments:increase1d", "Succeeded"),
                                  t("platform:deployments_failed:increase1d", "Failed", ref="B")],
         "short", bars=True, desc="Successful vs failed syncs over a rolling day."), 12, 6)

b.row("Cost & capacity (OpenCost)")
b.add(stat("Monthly run-rate", "platform:cluster_cost:monthly", "currencyUSD", [("blue", None)], color_mode="value",
           decimals=0, desc="Infrastructure cost per month at current node count and list prices."), 6, 6)
b.add(stat("Idle spend", "platform:cost_idle:ratio", "percentunit", [("green", None), ("orange", 0.4), ("red", 0.6)],
           decimals=0, desc="Paid capacity not requested by any workload — right-sizing opportunity."), 6, 6)
b.add(stat("CPU requested vs capacity", "cluster:cpu_requests:ratio", "percentunit",
           [("blue", None), ("green", 0.4), ("orange", 0.8), ("red", 0.9)], decimals=0), 6, 6)
b.add(stat("Memory requested vs capacity", "cluster:memory_requests:ratio", "percentunit",
           [("blue", None), ("green", 0.4), ("orange", 0.8), ("red", 0.9)], decimals=0), 6, 6)
b.add(pie("Monthly cost by namespace", "sort_desc(namespace:cost_compute:monthly)", "{{namespace}}", "currencyUSD",
          desc="Compute cost allocated by requested CPU & memory."), 12, 9)
b.add(ts("Cost run-rate trend", [t("platform:cluster_cost:monthly", "Cluster $/month")], "currencyUSD", min0=False), 12, 9)

exec_dash = dashboard("executive-overview", "Executive Overview — Reliability, Delivery & Cost",
                      ["executive", "slo", "finops", "dora"], b,
                      annotations=[DEPLOY_ANNOTATION, INCIDENT_ANNOTATION], refresh="5m", time_from="now-30d",
                      desc="Stakeholder view: SLO compliance, incidents, delivery and cost.", links=LINKS)

# =========================================================================== #
# 2. SRE COMMAND CENTER — operations & incident response
# =========================================================================== #
ns_var = {"name": "namespace", "label": "Namespace", "type": "query", "datasource": PROM,
          "query": {"query": "label_values(kube_namespace_status_phase, namespace)", "refId": "ns"},
          "definition": "label_values(kube_namespace_status_phase, namespace)",
          "includeAll": True, "multi": True, "allValue": ".+", "refresh": 2, "sort": 1,
          "current": {"selected": True, "text": ["All"], "value": ["$__all"]}}
svc_var = {"name": "service", "label": "Service", "type": "query", "datasource": PROM,
           "query": {"query": "label_values(traces_span_metrics_calls_total, service_name)", "refId": "svc"},
           "definition": "label_values(traces_span_metrics_calls_total, service_name)",
           "includeAll": True, "multi": True, "allValue": ".+", "refresh": 2, "sort": 1,
           "current": {"selected": True, "text": ["All"], "value": ["$__all"]}}

b = Board()
b.row("Situation — what is broken right now?")
b.add(stat("Critical alerts", 'count(ALERTS{alertstate="firing", severity="critical"}) or vector(0)', "none",
           [("green", None), ("red", 1)]), 3, 4)
b.add(stat("Warning alerts", 'count(ALERTS{alertstate="firing", severity="warning"}) or vector(0)', "none",
           [("green", None), ("orange", 1)]), 3, 4)
b.add(stat("Nodes not ready", 'sum(kube_node_status_condition{condition="Ready", status!="true"}) or vector(0)', "none",
           [("green", None), ("red", 1)]), 3, 4)
b.add(stat("Pods not ready", 'sum(kube_pod_status_ready{condition="false", namespace=~"$namespace"} * on (namespace, pod) group_left() max by (namespace, pod) (kube_pod_status_phase{phase!~"Succeeded|Failed"})) or vector(0)',
           "none", [("green", None), ("orange", 1), ("red", 5)]), 3, 4)
b.add(stat("Crash-looping", 'count(kube_pod_container_status_waiting_reason{reason="CrashLoopBackOff", namespace=~"$namespace"}) or vector(0)',
           "none", [("green", None), ("red", 1)]), 3, 4)
b.add(stat("Restarts (1h)", 'sum(increase(kube_pod_container_status_restarts_total{namespace=~"$namespace"}[1h])) or vector(0)',
           "none", [("green", None), ("orange", 1), ("red", 10)], decimals=0), 3, 4)
b.add(stat("Targets down", 'count(up == 0) or vector(0)', "none", [("green", None), ("orange", 1)]), 3, 4)
b.add(stat("Argo CD apps unhealthy", 'count(argocd_app_info{health_status!="Healthy"}) or vector(0)', "none",
           [("green", None), ("orange", 1)]), 3, 4)
b.add(table("Firing alerts", [t('sort_desc(ALERTS{alertstate="firing", alertname!~"Watchdog|InfoInhibitor"})', instant=True, fmt="table")],
            desc="All firing alerts. Follow the runbook link in Slack/PagerDuty for the response procedure.",
            transformations=[{"id": "organize", "options": {
                "excludeByName": {"Time": True, "Value": True, "__name__": True, "alertstate": True, "prometheus": True,
                                  "endpoint": True, "instance": True, "job": True, "service": True, "uid": True,
                                  "source": True, "team": True},
                "indexByName": {"severity": 0, "alertname": 1, "namespace": 2, "service_name": 3, "pod": 4}}}],
            overrides=[{"matcher": {"id": "byName", "options": "severity"}, "properties": [
                {"id": "custom.cellOptions", "value": {"type": "color-background"}},
                {"id": "mappings", "value": [{"type": "value", "options": {
                    "critical": {"color": "red", "index": 0}, "warning": {"color": "orange", "index": 1},
                    "info": {"color": "blue", "index": 2}}}]}]}]), 24, 7)

b.row("Golden signals — services ($service)")
SEL = 'span_kind="SPAN_KIND_SERVER", service_name=~"$service"'
b.add(ts("Request rate", [t(f'sum by (service_name) (rate(traces_span_metrics_calls_total{{{SEL}}}[$__rate_interval]))', "{{service_name}}")],
         "reqps"), 6, 8)
b.add(ts("Error ratio", [t(f'sum by (service_name) (rate(traces_span_metrics_calls_total{{{SEL}, status_code="STATUS_CODE_ERROR"}}[$__rate_interval])) / sum by (service_name) (rate(traces_span_metrics_calls_total{{{SEL}}}[$__rate_interval]))', "{{service_name}}")],
         "percentunit", steps=[("green", None), ("red", 0.005)], desc="Dashed line = 0.5 % (SLO error budget)."), 6, 8)
b.add(ts("Latency p50 / p95 / p99", [
    t(f'histogram_quantile(0.99, sum by (le) (rate(traces_span_metrics_duration_seconds_bucket{{{SEL}}}[$__rate_interval])))', "p99"),
    t(f'histogram_quantile(0.95, sum by (le) (rate(traces_span_metrics_duration_seconds_bucket{{{SEL}}}[$__rate_interval])))', "p95", ref="B"),
    t(f'histogram_quantile(0.50, sum by (le) (rate(traces_span_metrics_duration_seconds_bucket{{{SEL}}}[$__rate_interval])))', "p50", ref="C")],
    "s", steps=[("green", None), ("red", 0.5)], desc="Click an exemplar dot to jump to the trace in Tempo."), 6, 8)
b.panels[-1]["targets"][0]["exemplar"] = True
b.add(ts("Error-budget burn rate (1h / 6h)", [
    t('slo:sli_error:ratio_rate1h{service_name=~"$service"} / 0.005', "{{service_name}} 1h"),
    t('slo:sli_error:ratio_rate6h{service_name=~"$service"} / 0.005', "{{service_name}} 6h", ref="B")],
    "x", steps=[("green", None), ("orange", 6), ("red", 14.4)],
    desc="1 = spending budget exactly on schedule. 6x pages after 6h, 14.4x pages after 1h."), 6, 8)
b.add(table("Service RED summary (5m)", [
    t(f'sum by (service_name) (rate(traces_span_metrics_calls_total{{{SEL}}}[5m]))', instant=True, fmt="table", ref="A"),
    t(f'sum by (service_name) (rate(traces_span_metrics_calls_total{{{SEL}, status_code="STATUS_CODE_ERROR"}}[5m])) / sum by (service_name) (rate(traces_span_metrics_calls_total{{{SEL}}}[5m]))', instant=True, fmt="table", ref="B"),
    t(f'histogram_quantile(0.95, sum by (service_name, le) (rate(traces_span_metrics_duration_seconds_bucket{{{SEL}}}[5m])))', instant=True, fmt="table", ref="C"),
    t('clamp_min(slo:error_budget_remaining:ratio{service_name=~"$service"}, 0)', instant=True, fmt="table", ref="D")],
    transformations=[{"id": "merge", "options": {}},
                     {"id": "organize", "options": {"excludeByName": {"Time": True, "k8s_namespace_name": True},
                                                    "renameByName": {"service_name": "Service", "Value #A": "Req/s", "Value #B": "Error %",
                                                                     "Value #C": "p95", "Value #D": "Budget left"}}}],
    overrides=[
        {"matcher": {"id": "byName", "options": "Req/s"}, "properties": [{"id": "unit", "value": "reqps"}, {"id": "decimals", "value": 2}]},
        {"matcher": {"id": "byName", "options": "Error %"}, "properties": [
            {"id": "unit", "value": "percentunit"}, {"id": "decimals", "value": 2},
            {"id": "custom.cellOptions", "value": {"type": "color-text"}},
            {"id": "thresholds", "value": thresholds([("green", None), ("orange", 0.005), ("red", 0.05)])}]},
        {"matcher": {"id": "byName", "options": "p95"}, "properties": [
            {"id": "unit", "value": "s"}, {"id": "custom.cellOptions", "value": {"type": "color-text"}},
            {"id": "thresholds", "value": thresholds([("green", None), ("orange", 0.3), ("red", 0.5)])}]},
        {"matcher": {"id": "byName", "options": "Budget left"}, "properties": [
            {"id": "unit", "value": "percentunit"}, {"id": "min", "value": 0}, {"id": "max", "value": 1},
            {"id": "custom.cellOptions", "value": {"type": "gauge", "mode": "gradient"}},
            {"id": "thresholds", "value": thresholds([("red", None), ("orange", 0.25), ("green", 0.5)])}]}]), 12, 8)
b.add({"type": "nodeGraph", "title": "Service map (live)", "datasource": TEMPO,
       "targets": [{"datasource": TEMPO, "refId": "A", "queryType": "serviceMap",
                    "serviceMapQuery": '{service_name=~"$service"}'}],
       "options": {}, "description": "Built from the OTel servicegraph connector. Red rings = errors."}, 12, 8)

b.row("Kubernetes workloads ($namespace)")
b.add(ts("CPU usage by pod (top 10)", [t('topk(10, sum by (namespace, pod) (rate(container_cpu_usage_seconds_total{namespace=~"$namespace", container!="", image!=""}[$__rate_interval])))', "{{namespace}}/{{pod}}")],
         "cores"), 8, 8)
b.add(ts("Memory working set by pod (top 10)", [t('topk(10, sum by (namespace, pod) (container_memory_working_set_bytes{namespace=~"$namespace", container!="", image!=""}))', "{{namespace}}/{{pod}}")],
         "bytes"), 8, 8)
b.add(ts("CPU throttling (top 10)", [t('topk(10, sum by (namespace, pod) (increase(container_cpu_cfs_throttled_periods_total{namespace=~"$namespace", container!=""}[$__rate_interval])) / sum by (namespace, pod) (increase(container_cpu_cfs_periods_total{namespace=~"$namespace", container!=""}[$__rate_interval])))', "{{namespace}}/{{pod}}")],
         "percentunit", steps=[("green", None), ("red", 0.25)], desc="> 25 % throttling usually means the CPU limit is too low."), 8, 8)
b.add(table("Recent restarts & OOM kills", [
    t('sort_desc(sum by (namespace, pod, container) (increase(kube_pod_container_status_restarts_total{namespace=~"$namespace"}[1h])) > 0)', instant=True, fmt="table", ref="A"),
    t('max by (namespace, pod, container) (kube_pod_container_status_last_terminated_reason{namespace=~"$namespace", reason=~"OOMKilled|Error"})', instant=True, fmt="table", ref="B")],
    transformations=[{"id": "merge", "options": {}},
                     {"id": "organize", "options": {"excludeByName": {"Time": True},
                                                    "renameByName": {"Value #A": "Restarts (1h)", "Value #B": "Last exit: OOM/Error"}}}]), 12, 8)
b.add(ts("Pods by phase", [t('sum by (phase) (kube_pod_status_phase{namespace=~"$namespace"}) > 0', "{{phase}}")], "short", stack=True), 12, 8)

b.row("Nodes & capacity")
b.add(ts("Node CPU utilisation", [t('1 - avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[$__rate_interval]))', "{{instance}}")],
         "percentunit", steps=[("green", None), ("orange", 0.8), ("red", 0.9)], maxv=1), 8, 7)
b.add(ts("Node memory utilisation", [t('1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes', "{{instance}}")],
         "percentunit", steps=[("green", None), ("orange", 0.8), ("red", 0.9)], maxv=1), 8, 7)
b.add(bargauge("Fullest volumes", 'topk(10, kubelet_volume_stats_used_bytes / kubelet_volume_stats_capacity_bytes)', "{{namespace}}/{{persistentvolumeclaim}}",
               "percentunit", [("green", None), ("orange", 0.75), ("red", 0.9)], minv=0, maxv=1, sort=False), 8, 7)

b.row("Logs & Kubernetes events")
b.add({"type": "timeseries", "title": "Log volume by level", "datasource": LOKI,
       "targets": [{"datasource": LOKI, "refId": "A", "queryType": "range",
                    "expr": 'sum by (detected_level) (count_over_time({k8s_namespace_name=~"$namespace"} [$__auto]))',
                    "legendFormat": "{{detected_level}}"}],
       "fieldConfig": {"defaults": {"unit": "short", "custom": {"drawStyle": "bars", "fillOpacity": 70, "stacking": {"mode": "normal"}}},
                       "overrides": [{"matcher": {"id": "byName", "options": "error"}, "properties": [{"id": "color", "value": {"mode": "fixed", "fixedColor": "red"}}]},
                                     {"matcher": {"id": "byName", "options": "warn"}, "properties": [{"id": "color", "value": {"mode": "fixed", "fixedColor": "orange"}}]}]},
       "options": {"legend": {"displayMode": "list", "placement": "bottom"}, "tooltip": {"mode": "multi"}}}, 24, 6)
b.add(logs("Error logs ($namespace)",
           '{k8s_namespace_name=~"$namespace"} | detected_level=~"error|fatal|critical" or level=~"(?i)error|fatal"',
           desc="Expand a line and click 'View trace' to jump to the request in Tempo."), 12, 10)
b.add(logs("Kubernetes warning events",
           '{service_name="k8s-events"} | k8s_event_type="Warning" | k8s_namespace_name=~"$namespace" | line_format "{{.k8s_object_kind}}/{{.k8s_object_name}} [{{.k8s_event_reason}}]"',
           desc="FailedScheduling, BackOff, Unhealthy, OOMKilling… collected by the otel-cluster collector."), 12, 10)

b.row("Traces")
b.add({"type": "table", "title": "Recent failed requests (traces)", "datasource": TEMPO,
       "targets": [{"datasource": TEMPO, "refId": "A", "queryType": "traceql", "limit": 20, "tableType": "traces",
                    "query": '{ status = error && resource.service.name =~ "${service:regex}" }'}],
       "description": "Errors are always kept by tail sampling. Click a trace ID to open it.",
       "options": {"showHeader": True}, "fieldConfig": {"defaults": {}, "overrides": []}}, 12, 9)
b.add({"type": "table", "title": "Slowest requests (> 500 ms)", "datasource": TEMPO,
       "targets": [{"datasource": TEMPO, "refId": "A", "queryType": "traceql", "limit": 20, "tableType": "traces",
                    "query": '{ kind = server && duration > 500ms && resource.service.name =~ "${service:regex}" }'}],
       "options": {"showHeader": True}, "fieldConfig": {"defaults": {}, "overrides": []}}, 12, 9)

b.row("GitOps (Argo CD)")
b.add(table("Applications", [t('max by (name, sync_status, health_status) (argocd_app_info)', instant=True, fmt="table")],
            transformations=[{"id": "organize", "options": {"excludeByName": {"Time": True, "Value": True},
                                                            "renameByName": {"name": "Application", "sync_status": "Sync", "health_status": "Health"}}}],
            overrides=[{"matcher": {"id": "byName", "options": "Health"}, "properties": [
                {"id": "custom.cellOptions", "value": {"type": "color-background"}},
                {"id": "mappings", "value": [{"type": "value", "options": {
                    "Healthy": {"color": "green", "index": 0}, "Progressing": {"color": "blue", "index": 1},
                    "Degraded": {"color": "red", "index": 2}, "Missing": {"color": "red", "index": 3},
                    "Suspended": {"color": "orange", "index": 4}}}]}]},
                {"matcher": {"id": "byName", "options": "Sync"}, "properties": [
                    {"id": "custom.cellOptions", "value": {"type": "color-text"}},
                    {"id": "mappings", "value": [{"type": "value", "options": {
                        "Synced": {"color": "green", "index": 0}, "OutOfSync": {"color": "orange", "index": 1}}}]}]}]), 12, 8)
b.add(ts("Syncs by result", [t('sum by (phase) (increase(argocd_app_sync_total[$__rate_interval]))', "{{phase}}")], "short", bars=True, stack=True), 12, 8)

sre_dash = dashboard("sre-command-center", "SRE Command Center — Operations & Incident Response",
                     ["sre", "operations", "incident-response", "slo"], b, templating=[ns_var, svc_var],
                     annotations=[DEPLOY_ANNOTATION, INCIDENT_ANNOTATION], refresh="30s", time_from="now-3h",
                     desc="Triage view: alerts → golden signals → k8s → logs/events → traces.", links=LINKS)

# =========================================================================== #
# 3. TELEMETRY PIPELINE — "who watches the watchers"
# =========================================================================== #
b = Board()
b.row("OpenTelemetry collectors")
b.add(ts("Accepted by receivers", [
    t('sum by (job) (rate(otelcol_receiver_accepted_spans_total[$__rate_interval]))', "spans {{job}}"),
    t('sum by (job) (rate(otelcol_receiver_accepted_log_records_total[$__rate_interval]))', "logs {{job}}", ref="B"),
    t('sum by (job) (rate(otelcol_receiver_accepted_metric_points_total[$__rate_interval]))', "metric points {{job}}", ref="C")],
    "short", legend_table=True), 12, 8)
b.add(ts("Export failures", [
    t('sum by (job, exporter) (rate(otelcol_exporter_send_failed_spans_total[$__rate_interval]))', "spans {{job}} → {{exporter}}"),
    t('sum by (job, exporter) (rate(otelcol_exporter_send_failed_log_records_total[$__rate_interval]))', "logs {{job}} → {{exporter}}", ref="B"),
    t('sum by (job, exporter) (rate(otelcol_exporter_send_failed_metric_points_total[$__rate_interval]))', "metrics {{job}} → {{exporter}}", ref="C")],
    "short", steps=[("green", None), ("red", 0.0001)]), 12, 8)
b.add(ts("Exporter queue fill", [t('max by (job, exporter) (otelcol_exporter_queue_size / otelcol_exporter_queue_capacity)', "{{job}} → {{exporter}}")],
         "percentunit", steps=[("green", None), ("orange", 0.5), ("red", 0.8)], maxv=1), 8, 7)
b.add(ts("Tail-sampling decisions", [t('sum by (sampled) (rate(otelcol_processor_tail_sampling_global_count_traces_sampled_total[$__rate_interval]))', "sampled={{sampled}}")],
         "short", stack=True), 8, 7)
b.add(ts("Collector memory (RSS)", [t('max by (job, pod) (otelcol_process_memory_rss_bytes)', "{{pod}}")], "bytes"), 8, 7)

b.row("Backends")
b.add(ts("Prometheus ingestion (samples/s)", [t('sum(rate(prometheus_tsdb_head_samples_appended_total[$__rate_interval]))', "samples/s")], "short"), 8, 7)
b.add(ts("Prometheus active series", [t('sum(prometheus_tsdb_head_series)', "series")], "short"), 8, 7)
b.add(ts("Loki ingestion (bytes/s)", [t('sum(rate(loki_distributor_bytes_received_total[$__rate_interval]))', "bytes/s")], "Bps"), 8, 7)
b.add(ts("Tempo ingestion (spans/s)", [t('sum(rate(tempo_distributor_spans_received_total[$__rate_interval]))', "spans/s")], "short"), 8, 7)
b.add(ts("Scrape targets down", [t('count by (job) (up == 0)', "{{job}}")], "short", bars=True), 8, 7)
b.add(ts("Alertmanager notifications failed", [t('sum by (integration) (rate(alertmanager_notifications_failed_total[$__rate_interval]))', "{{integration}}")],
         "short", steps=[("green", None), ("red", 0.0001)], desc="Failures here mean pages are NOT reaching PagerDuty/Slack."), 8, 7)

pipe_dash = dashboard("telemetry-pipeline", "Telemetry Pipeline Health", ["platform", "otel", "meta-monitoring"], b,
                      refresh="1m", time_from="now-6h", desc="Meta-monitoring of collectors and backends.", links=LINKS)

for name, d in [("executive-overview.json", exec_dash), ("sre-command-center.json", sre_dash), ("telemetry-pipeline.json", pipe_dash)]:
    with open(os.path.join(OUT, name), "w") as f:
        json.dump(d, f, indent=2)
        f.write("\n")
    print("wrote", name, len(d["panels"]), "panels")
