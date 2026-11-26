#!/usr/bin/env bash
# Game-day helper: inject failures into the demo shop and watch the platform react.
#   scripts/chaos.sh errors 0.2     # 20 % payment failures → SLO burn alerts → PagerDuty/Slack
#   scripts/chaos.sh latency 800    # +800 ms per request   → latency SLO alert, slow traces
#   scripts/chaos.sh crash          # crash-loop payments   → KubePodCrashLooping, k8s events
#   scripts/chaos.sh reset
set -euo pipefail
NS=demo
post() { kubectl -n $NS exec deploy/"$1" -c app -- python -c \
  "import httpx,sys; print(httpx.post('http://localhost:8080/chaos', json=$2).text)"; }
case "${1:-}" in
  errors)  for p in $(kubectl -n $NS get pod -l app.kubernetes.io/name=payments -o name); do
             kubectl -n $NS exec "$p" -c app -- python -c "import httpx; print(httpx.post('http://localhost:8080/chaos', json={'error_rate': ${2:-0.2}}).text)"; done ;;
  latency) post orders "{'latency_ms': ${2:-800}}" ;;
  crash)   kubectl -n $NS patch deploy payments --type json -p '[{"op":"replace","path":"/spec/template/spec/containers/0/command","value":["python","-c","raise SystemExit(1)"]}]' ;;
  reset)   kubectl -n $NS rollout restart deploy/payments deploy/orders deploy/frontend
           echo "Note: Argo CD self-heal reverts manual spec changes (e.g. 'crash') within ~3 min." ;;
  *) sed -n '2,7p' "$0"; exit 1 ;;
esac
