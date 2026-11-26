import importlib

import pytest
from fastapi.testclient import TestClient


def load(role: str, monkeypatch, **env):
    monkeypatch.setenv("SERVICE_ROLE", role)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    import app.main as main

    return importlib.reload(main)


def test_health(monkeypatch):
    main = load("frontend", monkeypatch)
    r = TestClient(main.app).get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "role": "frontend"}


def test_payments_success(monkeypatch):
    main = load("payments", monkeypatch, ERROR_RATE="0")
    r = TestClient(main.app).post("/charge", json={"order_id": "x", "amount": 10})
    assert r.status_code == 200
    assert r.json()["charged"] == 10


def test_payments_chaos(monkeypatch):
    main = load("payments", monkeypatch, ERROR_RATE="1")
    r = TestClient(main.app).post("/charge", json={"order_id": "x", "amount": 10})
    assert r.status_code == 500


@pytest.mark.parametrize("body,expected", [({"error_rate": 0.3}, 0.3), ({"latency_ms": 50}, 0.0)])
def test_runtime_chaos(monkeypatch, body, expected):
    main = load("payments", monkeypatch, ERROR_RATE="0", LATENCY_MS="0")
    c = TestClient(main.app)
    assert c.post("/chaos", json=body).status_code == 200
    assert c.get("/chaos").json()["error_rate"] == expected
