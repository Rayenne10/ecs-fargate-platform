"""Exercise a real local HTTP server in the same process/network environment."""

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def fetch(base, endpoint, data=None):
    request = urllib.request.Request(
        base + endpoint,
        data=json.dumps(data).encode() if data is not None else None,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        return response.read()


def smoke():
    base = "http://127.0.0.1:18780"
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "18780",
            "--no-access-log",
        ],
        cwd=ROOT,
        env={**os.environ, "APP_ENV": "local-verification", "APP_REVISION": "local-smoke"},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        for _attempt in range(50):
            if process.poll() is not None:
                raise RuntimeError("HTTP server exited during startup")
            try:
                if json.loads(fetch(base, "/readyz"))["status"] == "ready":
                    break
            except urllib.error.URLError:
                time.sleep(0.1)
        assert json.loads(fetch(base, "/api/info"))["revision"] == "local-smoke"
        result = json.loads(fetch(base, "/api/capacity", {"task_count": 2}))
        assert result["total_vcpu"] == 0.5 and result["total_memory_gib"] == 1
        assert b"From commit" in fetch(base, "/")
        assert b"platform_http_requests_total" in fetch(base, "/metrics")
        report = {
            "mode": "local-HTTP",
            "readiness": True,
            "release_metadata": True,
            "capacity_api": True,
            "homepage": True,
            "metrics": True,
            "aws_deployment": False,
        }
        (ROOT / "verification").mkdir(exist_ok=True)
        (ROOT / "verification/http-smoke.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report, indent=2))
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


if __name__ == "__main__":
    smoke()
