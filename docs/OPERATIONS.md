# Operations, rollback and cleanup

## Normal releases

CI validates the application, configuration and container. After one successful manual AWS release, optionally set repository variable `ENABLE_AUTO_DEPLOY=true`. Each main push then runs checks and deploys through the protected aws-demo environment. A workflow concurrency group and S3 lockfile reduce overlapping mutations. Neither is an excuse to run unmanaged Terraform processes against the same state.

Terraform owns the ECS service and task definition, including image revisions. The workflow does not call a second, competing task-definition renderer or `aws ecs update-service` after apply. This avoids the common pattern where a later Terraform apply silently resets a CI-created release.

## Rolling update behavior

The service uses a 100% minimum healthy percentage and 200% maximum. For one desired task, a healthy old task can remain while a new task starts. Temporary extra capacity can incur charges. Container readiness and ALB health checks must pass. A deployment circuit breaker requests rollback to the last completed deployment on failure. The very first deployment has no previous healthy release to return to.

Terraform's steady-state wait alone is insufficient: ECS can become stable after rollback. `verify_deployment.py` also requires the intended task definition, a completed rollout, expected running count, and an ALB-served matching app revision. If rollback or verification fails, the workflow fails. Examine actual ECS state and refresh/re-plan before retrying; do not assume the requested image is active.

## Intentional release rollback

Run the deployment workflow with `operation=rollback` and the full commit SHA of an existing ECR `sha-COMMIT` release. It resolves that digest and applies current main-branch infrastructure with the previous application image/revision. It does not rebuild old source or rewind networking configuration. Immutable tagged releases are not pruned by the provided untagged-image lifecycle rule, so manage retained tagged storage intentionally.

## Useful diagnostics

| Symptom | Check |
| --- | --- |
| OIDC AccessDenied | Actual subject, audience, environment name/branch restriction, role ARN, existing provider |
| Cannot write state lock | Exact `workload/terraform.tfstate.tflock` permissions, correct bucket/region, concurrent runs |
| Cannot pull image | ECR digest exists, execution-role access, assigned public IP, route to internet gateway, HTTPS egress |
| ALB target unhealthy | Task port 8000, SG source/egress rules, readyz response, log group |
| Rollout reverted | Circuit-breaker events and service task definition; inspect receipt/failed verifier |
| TLS failure | ACM region/issued status, hostname coverage, DNS alias, PUBLIC_HOSTNAME |
| HTTP check blocked | ALLOWED_INGRESS_CIDRS must permit the verifier's network |
| App revision wrong | Actual task definition digest/environment, concurrent rollout, retry after convergence |

JSON request logs include route template, method, status, duration, and request ID, rather than arbitrary paths, query strings, or request bodies. CloudWatch retains logs for seven days. Prometheus-format metrics are served by the application, but no scraper is deployed. ECS CPU and ALB 5xx CloudWatch alarms are provisioned; they only notify if existing SNS action ARNs are configured.

## Destroy the chargeable workload

1. Set repository variable `ENABLE_AUTO_DEPLOY=false` before cleanup.
2. Run deployment workflow on main with `operation=destroy`.
3. Inspect its destroy plan and result. It reads the current image/revision from state to satisfy variable requirements.
4. Verify ECS tasks, ALB, network resources, alarms and workload log group are removed.

The bootstrap ECR repository, state bucket, roles and OIDC provider remain. ECR image storage and S3 storage can still incur charges; destroying the compute/ALB does not mean the entire account has zero cost. No exact price is promised. Use AWS Billing/Cost Explorer for actual charges.

## Local recovery or destroy

If the GitHub role configuration is broken, use your authorized local AWS profile:

```sh
terraform -chdir=infra/workload init -backend-config=backend.hcl -lockfile=readonly
export TF_VAR_image_uri="$(terraform -chdir=infra/workload output -raw image_uri)"
export TF_VAR_app_revision="$(terraform -chdir=infra/workload output -raw app_revision)"
terraform -chdir=infra/workload plan -destroy -out=destroy.tfplan
terraform -chdir=infra/workload apply destroy.tfplan
```

Keep the other workload variables exported/copied from bootstrap. If state recovery is needed, preserve the current state and inspect S3 versions before restoring. Do not blindly force-unlock a lock that may belong to a running apply.

## Remove bootstrap resources only when finished

Bootstrap removal is intentionally separate and manual. The state bucket has prevent_destroy and is not force-deleted; ECR is not force-deleted. First destroy the workload, archive needed state/receipts, review all bucket versions and images, and only then explicitly adjust the bootstrap protection and remove retained contents before a reviewed bootstrap destroy. Do not delete an OIDC provider shared by other projects. An existing provider supplied by ARN is not owned by this stack.

## Demo tradeoffs

- Public task IPs, ALB-only inbound application access; no NAT gateway. Private-subnet connectivity is a separate production design.
- One default task is affordable lab capacity, not multi-AZ high availability.
- Plain HTTP default is suitable for the nonsensitive demo only; optional ACM/DNS configuration enables HTTPS.
- No autoscaling, WAF, database, application authentication, secrets ingestion, or tracing backend is provisioned.
- Regional deployment-role permissions are broader than project-only tenant isolation. Use a dedicated account and refine with evaluated IAM controls before shared production use.
