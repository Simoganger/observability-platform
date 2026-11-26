"""Constant background traffic so dashboards and SLOs always have data."""
import os
import random
import time

import httpx

TARGET = os.getenv("TARGET_URL", "http://frontend:8080")
RPS = float(os.getenv("RPS", "5"))

with httpx.Client(timeout=10.0) as client:
    while True:
        try:
            client.post(f"{TARGET}/checkout")
            if random.random() < 0.2:
                client.get(f"{TARGET}/")
        except httpx.HTTPError as exc:  # keep generating load no matter what
            print(f"loadgen: {exc}", flush=True)
        time.sleep(max(0.0, random.expovariate(RPS)))
