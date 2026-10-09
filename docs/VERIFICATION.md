# Verification status

Recorded 9 October 2026. These statuses distinguish implemented code from executed checks.

| Check | Status | Evidence / limitation |
| --- | --- | --- |
| Python tests | Passed | 19 tests on Python 3.12; API validation, request IDs, metrics/log privacy, ECR lookup failures, rollout rejection, and receipt behavior |
| Python lint/format | Passed | Ruff checks and formatting |
| Actual local HTTP service | Passed | Uvicorn subprocess: readyz, release metadata, capacity calculation, homepage and metrics |
| JavaScript syntax | Passed | Node syntax checks for UI, OIDC inspection and browser runner |
| Workflow YAML / shell syntax | Passed | Workflow files parsed; bash run blocks syntax-checked. This does not validate all GitHub Actions semantics. |
| Terraform formatting/syntax parsing | Passed | terraform fmt -check -recursive infra |
| Provider dependency acquisition | Passed | AWS 6.46.0 release archive matched published SHA256; Terraform-generated lock files retained for Linux and Windows |
| Terraform full validate/mock plans | Blocked locally | Provider RPC requires Unix sockets, which this execution environment prohibits. CI contains validate and mock-provider test jobs. Their results are pending. |
| Browser execution | Blocked locally | Browser download did not yield a usable archive in this environment. CI contains Playwright verification; not claimed passed. |
| Docker build/container smoke | Pending | Docker is unavailable here. CI includes a real image build and hardened container smoke test. |
| GitHub CI run | Pending | Publish to a repository before running the workflow. |
| AWS bootstrap / ECS rollout | Not run | No AWS account session was supplied; no AWS resources created. |
| Real rollback / destruction | Not run | Requires an actual deployed workload and a controlled experiment. |

## What the test suite proves

Application behavior and delivery-script error handling are exercised locally. Delivery tests mock the AWS CLI and HTTP result; they do not establish that IAM permissions or AWS APIs work. Terraform mock tests are implemented for both stacks but still need execution in an environment supporting provider RPC. Formatting success is not a substitute for provider validation or an actual cloud plan.

## Next evidence to collect

1. Publish and run CI; fix any provider/schema, container or browser failures.
2. Review the bootstrap plan in your AWS account and create foundations.
3. Run the deployment workflow; retain its verified ECS/HTTP receipt.
4. Inspect actual logs/targets/tasks, perform a previous-image rollback, then destroy the workload and verify cleanup.

Only after step 3 should the CV say the service was actually provisioned/deployed on AWS. Do not claim live availability, cost savings, production resilience or high availability from mock tests.
