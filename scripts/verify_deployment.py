"""Check the actual ECS revision and the served app revision after Terraform apply."""

import argparse
import json
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path


def assert_service(service, expected_task_definition):
    if service.get("taskDefinition") != expected_task_definition:
        raise ValueError(
            "Service uses a different task definition; deployment may have rolled back"
        )
    deployments = service.get("deployments", [])
    if len(deployments) != 1 or deployments[0].get("rolloutState") != "COMPLETED":
        raise ValueError("Expected a single completed ECS deployment")
    if service.get("runningCount", 0) < service.get("desiredCount", 1) or service.get(
        "pendingCount", 0
    ):
        raise ValueError("Service does not have its expected running capacity")


def fetch_info(url):
    with urllib.request.urlopen(url.rstrip("/") + "/api/info", timeout=10) as response:
        return json.load(response)


def verify(url, revision, cluster, service_name, task_definition, region, output):
    result = subprocess.run(
        [
            "aws",
            "ecs",
            "describe-services",
            "--cluster",
            cluster,
            "--services",
            service_name,
            "--region",
            region,
            "--output",
            "json",
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    )
    services = json.loads(result.stdout)
    if services.get("failures") or len(services.get("services", [])) != 1:
        raise ValueError("ECS service lookup failed")
    assert_service(services["services"][0], task_definition)
    for attempt in range(12):
        try:
            info = fetch_info(url)
            if info.get("revision") == revision and info.get("environment") == "aws-demo":
                receipt = {
                    "verified_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "region": region,
                    "cluster": cluster,
                    "service": service_name,
                    "task_definition": task_definition,
                    "url": url,
                    "revision": revision,
                    "http_verified": True,
                }
                Path(output).parent.mkdir(parents=True, exist_ok=True)
                Path(output).write_text(json.dumps(receipt, indent=2) + "\n")
                print(json.dumps(receipt, indent=2))
                return receipt
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            pass
        if attempt < 11:
            time.sleep(5)
    raise ValueError("ALB response did not confirm the expected application revision")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    for name in ["url", "revision", "cluster", "service", "task-definition", "region"]:
        p.add_argument("--" + name, required=True)
    p.add_argument("--output", default="verification/deployment.json")
    a = p.parse_args()
    verify(a.url, a.revision, a.cluster, a.service, a.task_definition, a.region, a.output)
