import json
import subprocess
from unittest.mock import patch

import pytest

from scripts.resolve_image import resolve
from scripts.verify_deployment import assert_service, verify


def test_image_lookup_distinguishes_missing_from_permissions():
    missing = subprocess.CompletedProcess([], 1, "", "ImageNotFoundException")
    with patch("scripts.resolve_image.subprocess.run", return_value=missing):
        assert resolve("demo", "a" * 40, "eu-west-3")["exists"] is False
        with pytest.raises(RuntimeError):
            resolve("demo", "a" * 40, "eu-west-3", required=True)
    denied = subprocess.CompletedProcess([], 1, "", "AccessDeniedException")
    with patch("scripts.resolve_image.subprocess.run", return_value=denied):
        with pytest.raises(RuntimeError):
            resolve("demo", "a" * 40, "eu-west-3")


def test_valid_digest_and_bad_revision():
    output = json.dumps({"imageDetails": [{"imageDigest": "sha256:" + "b" * 64}]})
    with patch(
        "scripts.resolve_image.subprocess.run",
        return_value=subprocess.CompletedProcess([], 0, output, ""),
    ):
        assert resolve("demo", "a" * 40, "eu-west-3")["digest"] == "sha256:" + "b" * 64
    with pytest.raises(ValueError):
        resolve("demo", "main;whoami", "eu-west-3")


def test_completed_rollout_is_verified():
    assert_service(
        {
            "taskDefinition": "expected",
            "deployments": [{"rolloutState": "COMPLETED"}],
            "runningCount": 1,
            "desiredCount": 1,
            "pendingCount": 0,
        },
        "expected",
    )


@pytest.mark.parametrize(
    "service",
    [
        {"taskDefinition": "previous"},
        {"taskDefinition": "expected", "deployments": [{"rolloutState": "IN_PROGRESS"}]},
        {
            "taskDefinition": "expected",
            "deployments": [{"rolloutState": "COMPLETED"}],
            "runningCount": 0,
            "desiredCount": 1,
        },
    ],
)
def test_stable_does_not_hide_failed_or_rolled_back_revision(service):
    with pytest.raises(ValueError):
        assert_service(service, "expected")


def test_verified_receipt_requires_ecs_and_http_revision(tmp_path):
    result = subprocess.CompletedProcess(
        [],
        0,
        json.dumps(
            {
                "services": [
                    {
                        "taskDefinition": "expected",
                        "deployments": [{"rolloutState": "COMPLETED"}],
                        "runningCount": 1,
                        "desiredCount": 1,
                        "pendingCount": 0,
                    }
                ]
            }
        ),
        "",
    )
    with (
        patch("scripts.verify_deployment.subprocess.run", return_value=result),
        patch(
            "scripts.verify_deployment.fetch_info",
            return_value={"revision": "a" * 40, "environment": "aws-demo"},
        ),
    ):
        receipt = verify(
            "http://demo",
            "a" * 40,
            "cluster",
            "service",
            "expected",
            "eu-west-3",
            tmp_path / "receipt.json",
        )
    assert receipt["http_verified"] is True
    assert json.loads((tmp_path / "receipt.json").read_text())["revision"] == "a" * 40


def test_wrong_http_revision_does_not_create_receipt(tmp_path):
    result = subprocess.CompletedProcess(
        [],
        0,
        json.dumps(
            {
                "services": [
                    {
                        "taskDefinition": "expected",
                        "deployments": [{"rolloutState": "COMPLETED"}],
                        "runningCount": 1,
                        "desiredCount": 1,
                        "pendingCount": 0,
                    }
                ]
            }
        ),
        "",
    )
    with (
        patch("scripts.verify_deployment.subprocess.run", return_value=result),
        patch(
            "scripts.verify_deployment.fetch_info",
            return_value={"revision": "wrong", "environment": "aws-demo"},
        ),
        patch("scripts.verify_deployment.time.sleep"),
    ):
        with pytest.raises(ValueError, match="ALB response"):
            verify(
                "http://demo",
                "a" * 40,
                "cluster",
                "service",
                "expected",
                "eu-west-3",
                tmp_path / "receipt.json",
            )
    assert not (tmp_path / "receipt.json").exists()
