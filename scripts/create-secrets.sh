#!/usr/bin/env bash
# Creates the out-of-Git secrets for an EXISTING cluster (Terraform does this for kind/eks/gke).
# Production: replace with External Secrets Operator / Vault / cloud secret manager.
#   PAGERDUTY_ROUTING_KEY=... SLACK_WEBHOOK_URL=... scripts/create-secrets.sh
set -euo pipefail
NS="${NAMESPACE:-observability}"
kubectl create namespace "$NS" --dry-run=client -o yaml | kubectl apply -f -
kubectl label namespace "$NS" pod-security.kubernetes.io/enforce=privileged team=sre --overwrite

kubectl -n "$NS" create secret generic alertmanager-incident-secrets \
  --from-literal=pagerduty-routing-key="${PAGERDUTY_ROUTING_KEY:-REPLACE_ME}" \
  --from-literal=slack-webhook-url="${SLACK_WEBHOOK_URL:-https://hooks.slack.com/services/REPLACE/ME/PLEASE}" \
  --dry-run=client -o yaml | kubectl apply -f -

PASS="${GRAFANA_ADMIN_PASSWORD:-$(LC_ALL=C tr -dc 'A-Za-z0-9' </dev/urandom | head -c 24)}"
kubectl -n "$NS" create secret generic grafana-admin \
  --from-literal=admin-user=admin --from-literal=admin-password="$PASS" \
  --dry-run=client -o yaml | kubectl apply -f -
echo "Secrets ready in namespace $NS. Grafana admin password: $PASS"
