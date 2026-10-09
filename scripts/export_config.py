"""Export non-secret bootstrap outputs; never read or write AWS credentials."""

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def export():
    result = subprocess.run(
        ["terraform", f"-chdir={ROOT / 'infra/bootstrap'}", "output", "-json"],
        check=True,
        capture_output=True,
        text=True,
    )
    outputs = {key: entry["value"] for key, entry in json.loads(result.stdout).items()}
    backend = {
        "bucket": outputs["state_bucket"],
        "key": "workload/terraform.tfstate",
        "region": outputs["aws_region"],
        "encrypt": True,
        "use_lockfile": True,
    }
    config = {
        "aws_region": outputs["aws_region"],
        "project_name": outputs["project_name"],
        "execution_role_arn": outputs["execution_role_arn"],
        "task_role_arn": outputs["task_role_arn"],
    }
    for filename, _values in [("backend.hcl", backend), ("terraform.tfvars", config)]:
        path = ROOT / "infra/workload" / filename
        if path.exists():
            raise FileExistsError(f"Refusing to overwrite existing configuration: {path}")
    for filename, values in [("backend.hcl", backend), ("terraform.tfvars", config)]:
        (ROOT / "infra/workload" / filename).write_text(
            "".join(f"{key} = {json.dumps(value)}\n" for key, value in values.items())
        )
    variables = {
        "AWS_REGION": outputs["aws_region"],
        "AWS_DEPLOY_ROLE_ARN": outputs["aws_deploy_role_arn"],
        "TF_STATE_BUCKET": outputs["state_bucket"],
        "ECR_REPOSITORY": outputs["ecr_repository"],
        "PROJECT_NAME": outputs["project_name"],
        "EXECUTION_ROLE_ARN": outputs["execution_role_arn"],
        "TASK_ROLE_ARN": outputs["task_role_arn"],
    }
    (ROOT / "verification").mkdir(exist_ok=True)
    (ROOT / "verification/github-variables.json").write_text(json.dumps(variables, indent=2) + "\n")
    print(
        "Created local workload configuration and verification/github-variables.json. No credentials exported."
    )


if __name__ == "__main__":
    export()
