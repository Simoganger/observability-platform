"""demo-shop — a tiny 3-tier shop used to exercise the observability platform.

One image, three roles (SERVICE_ROLE):
  frontend  →  orders  →  payments

The code contains NO OpenTelemetry SDK setup on purpose: traces and metrics are
injected at runtime by the OpenTelemetry Operator (zero-code instrumentation),
exactly how existing workloads get onboarded. If the OTel API is present
(injected), we add business metrics and stamp trace IDs into JSON logs.

Fault injection (env, or POST /chaos at runtime):
  ERROR_RATE   0.0–1.0  probability a payment fails       (payments)
  LATENCY_MS   int      extra latency added to each request (all roles)
"""
from __future__ import annotations

import json
import logging
import os
import random
import sys
import time
import uuid

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

ROLE = os.getenv("SERVICE_ROLE", "frontend")
ORDERS_URL = os.getenv("ORDERS_URL", "http://orders:8080")
PAYMENTS_URL = os.getenv("PAYMENTS_URL", "http://payments:8080")
CHAOS = {
    "error_rate": float(os.getenv("ERROR_RATE", "0.0")),
    "latency_ms": int(os.getenv("LATENCY_MS", "0")),
}

# ----------------------------------------------------------------- telemetry --
try:  # present only when the OTel Operator injected auto-instrumentation
    from opentelemetry import metrics as otel_metrics
    from opentelemetry import trace as otel_trace

    _meter = otel_metrics.get_meter("demo-shop")
    ORDERS = _meter.create_counter("shop.orders", description="Orders placed")
    REVENUE = _meter.create_counter("shop.revenue.usd", description="Revenue captured in USD")
except ImportError:  # pragma: no cover - plain local run
    otel_trace = None
    ORDERS = REVENUE = None


class JsonFormatter(logging.Formatter):
    """One JSON object per line; trace_id/span_id enable logs → traces jumps."""

    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created)) + f".{int(record.msecs):03d}Z",
            "level": record.levelname.lower(),
            "service": ROLE,
            "msg": record.getMessage(),
        }
        if otel_trace is not None:
            ctx = otel_trace.get_current_span().get_span_context()
            if ctx.is_valid:
                entry["trace_id"] = f"{ctx.trace_id:032x}"
                entry["span_id"] = f"{ctx.span_id:016x}"
        entry.update(getattr(record, "extra_fields", {}))
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry)


handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JsonFormatter())
log = logging.getLogger("demo-shop")
log.handlers = [handler]
log.setLevel(logging.INFO)
log.propagate = False


def info(msg: str, **fields) -> None:
    log.info(msg, extra={"extra_fields": fields})


def error(msg: str, **fields) -> None:
    log.error(msg, extra={"extra_fields": fields})


# ----------------------------------------------------------------------- app --
app = FastAPI(title=f"demo-shop-{ROLE}")
client = httpx.AsyncClient(timeout=5.0)


@app.middleware("http")
async def access_log(request: Request, call_next):
    if request.url.path in ("/healthz", "/readyz"):
        return await call_next(request)
    if CHAOS["latency_ms"]:
        time.sleep(CHAOS["latency_ms"] / 1000)  # blocking on purpose: shows as CPU-bound latency
    start = time.perf_counter()
    response = await call_next(request)
    info("request", method=request.method, path=request.url.path, status=response.status_code,
         duration_ms=round((time.perf_counter() - start) * 1000, 1))
    return response


@app.get("/healthz")
@app.get("/readyz")
async def health():
    return {"status": "ok", "role": ROLE}


@app.get("/chaos")
async def get_chaos():
    return CHAOS


@app.post("/chaos")
async def set_chaos(body: dict):
    """Change fault injection at runtime, e.g. {"error_rate": 0.2, "latency_ms": 300}."""
    for key in ("error_rate", "latency_ms"):
        if key in body:
            CHAOS[key] = type(CHAOS[key])(body[key])
    info("chaos updated", **CHAOS)
    return CHAOS


# ---- frontend ----------------------------------------------------------------
if ROLE == "frontend":

    @app.get("/")
    async def home():
        return {"shop": "demo-shop", "try": "POST /checkout"}

    @app.post("/checkout")
    async def checkout():
        cart = {"items": random.randint(1, 5), "amount": round(random.uniform(5, 250), 2)}
        try:
            r = await client.post(f"{ORDERS_URL}/orders", json=cart)
        except httpx.HTTPError as exc:
            error("orders unreachable", error=str(exc))
            raise HTTPException(status_code=503, detail="orders unavailable") from exc
        if r.status_code >= 400:
            error("checkout failed", upstream_status=r.status_code, amount=cart["amount"])
            return JSONResponse(status_code=502, content={"error": "checkout failed"})
        info("checkout complete", order_id=r.json()["order_id"], amount=cart["amount"])
        return r.json()

# ---- orders ------------------------------------------------------------------
if ROLE == "orders":

    @app.post("/orders")
    async def create_order(cart: dict):
        order_id = str(uuid.uuid4())
        r = await client.post(f"{PAYMENTS_URL}/charge", json={"order_id": order_id, "amount": cart["amount"]})
        if r.status_code >= 400:
            error("payment declined", order_id=order_id, upstream_status=r.status_code)
            raise HTTPException(status_code=402, detail="payment failed")
        if ORDERS is not None:
            ORDERS.add(1, {"result": "placed"})
            REVENUE.add(cart["amount"])
        info("order placed", order_id=order_id, amount=cart["amount"], items=cart.get("items"))
        return {"order_id": order_id, "status": "placed"}

# ---- payments ----------------------------------------------------------------
if ROLE == "payments":

    @app.post("/charge")
    async def charge(payment: dict):
        time.sleep(random.uniform(0.01, 0.08))  # talk to the "bank"
        if random.random() < CHAOS["error_rate"]:
            error("payment provider error", order_id=payment.get("order_id"), provider="acme-pay")
            raise HTTPException(status_code=500, detail="payment provider error")
        return {"order_id": payment.get("order_id"), "charged": payment.get("amount")}
