"""Stateless demo API; no AWS credentials or SDK required in the application."""

import json
import logging
import os
import re
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse
from prometheus_client import CollectorRegistry, Counter, Histogram, generate_latest
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger("platform.requests")
logger.setLevel(logging.INFO)
if not logger.handlers:
    logger.addHandler(logging.StreamHandler())
logger.propagate = False

registry = CollectorRegistry()
requests_total = Counter(
    "platform_http_requests_total",
    "Completed requests",
    ["route", "method", "status"],
    registry=registry,
)
latency = Histogram(
    "platform_http_request_duration_seconds",
    "Request duration",
    ["route", "method"],
    registry=registry,
)

app = FastAPI(title="Fargate Platform API", version="1.0.0")


class QuoteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    task_count: int = Field(ge=1, le=100)
    cpu_units: int = Field(default=256, ge=256, le=16384)
    memory_mib: int = Field(default=512, ge=512, le=122880)


@app.middleware("http")
async def instrument(request: Request, call_next):
    start = time.perf_counter()
    supplied = request.headers.get("x-request-id", "")
    request_id = supplied if re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", supplied) else uuid.uuid4().hex
    status = 500
    try:
        oversized = False
        if request.method == "POST":
            body = bytearray()
            async for chunk in request.stream():
                if len(body) + len(chunk) > 16_384:
                    oversized = True
                    break
                body.extend(chunk)
            if not oversized:
                request._body = bytes(body)
        response = Response(status_code=413) if oversized else await call_next(request)
        status = response.status_code
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        if request.url.path in {"/", "/assets/app.js", "/assets/style.css"}:
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
            )
        return response
    finally:
        route = request.scope.get("route")
        # Never label/log arbitrary URL paths, request bodies or query strings.
        route_name = getattr(route, "path", "unmatched")
        method = request.method if request.method in {"GET", "POST", "HEAD", "OPTIONS"} else "OTHER"
        elapsed = time.perf_counter() - start
        requests_total.labels(route_name, method, str(status)).inc()
        latency.labels(route_name, method).observe(elapsed)
        logger.info(
            json.dumps(
                {
                    "event": "http_request",
                    "request_id": request_id,
                    "route": route_name,
                    "method": method,
                    "status": status,
                    "duration_ms": round(elapsed * 1000, 2),
                }
            )
        )


@app.get("/healthz")
def health():
    return {"status": "ok"}


@app.get("/readyz")
def ready():
    # This application is stateless and has no runtime downstream dependency.
    return {"status": "ready"}


@app.get("/api/info")
def info():
    return {
        "service": "ecs-fargate-platform",
        "version": "1.0.0",
        "environment": os.getenv("APP_ENV", "local"),
        "revision": os.getenv("APP_REVISION", "development"),
        "runtime": "FastAPI",
    }


@app.post("/api/capacity")
def capacity(body: QuoteRequest):
    # Resource arithmetic only; this is not an AWS pricing or valid task-size calculator.
    return {
        "task_count": body.task_count,
        "total_vcpu": body.task_count * body.cpu_units / 1024,
        "total_memory_gib": body.task_count * body.memory_mib / 1024,
        "notice": "Resource totals only. Validate ECS CPU/memory combinations before deployment.",
    }


@app.get("/metrics", include_in_schema=False)
def metrics():
    return Response(generate_latest(registry), media_type="text/plain; version=0.0.4")


@app.get("/", include_in_schema=False)
def homepage():
    return FileResponse(Path(__file__).parent / "static/index.html")


@app.get("/assets/{filename}", include_in_schema=False)
def asset(filename: str):
    if filename not in {"app.js", "style.css"}:
        return Response(status_code=404)
    return FileResponse(Path(__file__).parent / "static" / filename)
