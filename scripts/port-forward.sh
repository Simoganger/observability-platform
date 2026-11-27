#!/usr/bin/env bash
# Local access to every UI (Ctrl-C to stop all).
set -euo pipefail
trap 'kill 0' EXIT
pf() { kubectl -n "$1" port-forward "svc/$2" "$3" >/dev/null 2>&1 & echo "  http://localhost:${3%%:*}  $4"; }
echo "Via the gateway (SSO — make sso-users; local admin still works):"
echo "  https://grafana.${DOMAIN:-127.0.0.1.nip.io}   https://argocd.${DOMAIN:-127.0.0.1.nip.io}   https://keycloak.${DOMAIN:-127.0.0.1.nip.io}"
echo "Forwarding (not exposed on the gateway: no authentication of their own):"
pf observability grafana          3000:80   "Grafana        (break-glass: admin / make grafana-password)"
pf argocd        argocd-server    8080:80   "Argo CD        (break-glass: admin / make argocd-password)"
pf observability kps-prometheus   9090:9090 "Prometheus"
pf observability kps-alertmanager 9093:9093 "Alertmanager"
pf observability opencost         9091:9090 "OpenCost UI"
pf demo          frontend         8081:8080 "demo-shop      (POST /checkout, POST /chaos)"
wait
