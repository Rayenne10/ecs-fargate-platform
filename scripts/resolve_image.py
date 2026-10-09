"""Resolve an immutable ECR release without hiding AWS errors."""

import argparse
import json
import re
import subprocess
import sys


def resolve(repository, revision, region, required=False):
    if not re.fullmatch(r"[a-f0-9]{40}", revision):
        raise ValueError("Expected a complete commit SHA")
    result = subprocess.run(
        [
            "aws",
            "ecr",
            "describe-images",
            "--repository-name",
            repository,
            "--image-ids",
            f"imageTag=sha-{revision}",
            "--region",
            region,
            "--output",
            "json",
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if result.returncode:
        if "ImageNotFoundException" in result.stderr and not required:
            return {"exists": False, "digest": ""}
        raise RuntimeError("ECR lookup failed; verify image availability and AWS permissions")
    digest = json.loads(result.stdout)["imageDetails"][0]["imageDigest"]
    if not re.fullmatch(r"sha256:[a-f0-9]{64}", digest):
        raise ValueError("Unexpected ECR image digest")
    return {"exists": True, "digest": digest}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--region", required=True)
    parser.add_argument("--required", action="store_true")
    args = parser.parse_args()
    try:
        image = resolve(args.repository, args.revision, args.region, args.required)
        print("exists=" + str(image["exists"]).lower())
        print("digest=" + image["digest"])
    except (ValueError, RuntimeError, subprocess.TimeoutExpired, KeyError, IndexError) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1) from error
