# Runbook: SLOErrorBudgetBurn (Fast / Medium / Slow)

**Meaning:** a service fails more than its 99.5 % availability SLO allows. *Fast* = 2 % of the monthly budget gone in 1 h; *Medium* = 5 % in 6 h; *Slow* = 10 % in 3 days.

## Triage (≤ 5 min)
1. Open **SRE Command Center** with `service=<service_name>` from the alert.
2. **Did we just deploy?** Look for a purple deploy annotation right before the error ramp.
   → Yes: roll back (`git revert <deploy commit>` and push, or Argo CD → app → History → Rollback). Then investigate.
3. **Is it this service or a dependency?** Check the *Service map*: a red edge shows where errors start.
4. **Which requests?** Use *Recent failed requests (traces)*, open a trace, and find the first span with `status=error`.
5. **Why?** In the trace, use *Logs for this span* to see the exception, or check *Error logs* on the dashboard.

## Common causes
| Symptom | Likely cause | Action |
|---|---|---|
| Errors on one pod only | Bad node / OOM / stale config | `kubectl delete pod`, check *Restarts & OOM* |
| Errors on all pods after deploy | Regression | Roll back |
| Errors from a downstream span | Dependency outage | Fail over / degrade gracefully, page dependency owner |
| 5xx + high latency + CPU throttling | Under-provisioned | Scale out, raise CPU limit |

## Lab reproduction
`make chaos-errors` (20 % payment failures) · `make chaos-reset`
