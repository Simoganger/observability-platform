# Runbook: SLOLatencyBudgetBurn

**Meaning:** more than 1 % of requests to the service take longer than 500 ms (burning ≥ 14×).

1. SRE Command Center → *Latency p50/p95/p99*. Click an **exemplar dot** on the p99 line to open a slow trace.
2. In the trace, find the longest span: is it your code, a DB call or a downstream service?
3. Check *CPU throttling* and *Node CPU*. Throttling over 25 % means the CPU limit is too low.
4. Check *Slowest requests (> 500 ms)* for a common route or attribute.
5. Mitigate: scale out (`kubectl scale`, or raise HPA min via Git), roll back, or shed load.

Lab reproduction: `make chaos-latency` · `make chaos-reset`
