# Runbook: ArgoCDAppDegraded / ArgoCDAppOutOfSync / ArgoCDSyncFailed

1. `make status`, or Argo CD UI → the application → *App details* → *Conditions* / *Events*.
2. **Degraded**: open the red resource. Usually CrashLoopBackOff, ImagePullBackOff (wrong tag or missing DockerHub credentials) or a failed probe.
3. **OutOfSync for 30 min**: someone changed the cluster by hand, or the sync is failing. Check *Diff*. Self-heal reverts manual changes; if it can't, the diff shows why (immutable field, webhook rejection).
4. **SyncFailed**: read the sync operation message. Usual causes are a CRD missing (wave ordering), a schema error (CI should catch these: run `make render ENV=<env>`) or an admission webhook denial.
5. Roll back: `git revert` the offending commit, or Argo CD → History → Rollback (temporarily disables auto-sync).
