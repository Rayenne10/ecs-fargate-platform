# Verification status

Recorded 9 October 2026. The AWS portfolio deployment was completed, verified, and then destroyed to avoid ongoing workload charges.

## Executed AWS evidence

- [Successful deployment](https://github.com/Rayenne10/ecs-fargate-platform/actions/runs/37910617377): commit `9c343818bcae4ae912d6211487b3c9708da9b3d2`, region `eu-west-3`.
- The workflow applied Terraform and verified the intended ECS task definition, completed rollout, and served application revision through the ALB.
- [Deployment receipt](https://github.com/Rayenne10/ecs-fargate-platform/actions/runs/37910617377/artifacts/11606586761): artifact `deployment-receipt-37910617377`. GitHub artifact retention is finite; retain a downloaded copy.
- CloudWatch logs were inspected: dashboard, release metadata, static assets and readiness returned HTTP 200. One unmatched request returned 404; no exceptions appeared in the supplied log sample.
- AWS console evidence shows one running task, zero pending tasks, successful deployment, and one healthy ALB target.
- [Successful workload destruction](https://github.com/Rayenne10/ecs-fargate-platform/actions/runs/37914438840): `0 added, 0 changed, 23 destroyed`.

The former application URL is historical evidence, not a currently hosted demo. S3 state, ECR images, bootstrap IAM roles and the OIDC provider remain. S3/ECR storage can still incur charges.

## Checks and limits

| Check | Status | Evidence / limitation |
| --- | --- | --- |
| Python checks and tests | Passed in deployment CI | Python 3.11 and 3.12, Ruff, 19 tests, real local HTTP smoke |
| Terraform validate/mock plans | Passed in deployment CI | Both bootstrap and workload; mocks alone do not prove cloud IAM permissions |
| Browser checks | Passed in deployment CI | Rendering, resource calculation, JavaScript errors and mobile overflow |
| Container checks | Passed in deployment CI | Multi-stage image, non-root/read-only runtime, health and API smoke |
| AWS OIDC and immutable image push | Verified | GitHub assumed the deployment role and pushed a SHA-tagged ECR release |
| ECS/ALB deployment | Verified | Exact task definition and HTTP revision checked by receipt verifier |
| CloudWatch request logging | Verified | Real deployed requests observed in log stream |
| Workload destruction | Verified | 23 resources destroyed in linked workflow |
| Previous-release rollback | Implemented, not exercised on AWS | Do not claim a tested rollback experiment |
| HTTPS/custom domain | Optional, not exercised | This deployment used public HTTP |
| High availability/load testing | Not established | One task; no load or failover experiment |
| Production operation | Not claimed | Short-lived portfolio lab |

## Fixes found during real deployment

A fresh account needed the Elastic Load Balancing service-linked role as well as the ECS role. Bootstrap now offers opt-in creation for each absent role, while preserving existing account-wide roles. The AWS provider's rollout waiter needed `ecs:ListServiceDeployments` and `ecs:DescribeServiceDeployments`; both are now present in the regional deployment policy.

Repository refinements after the verified cloud release are checked by the CI badge. They have not been redeployed to AWS; no new cloud resources were created for documentation updates.

## Screenshots

Original deployment screenshots are retained in [screenshots/](screenshots/). These are dated deployment evidence, not proof of current availability.

## Accurate portfolio claim

“Provisioned and verified a containerized FastAPI service on AWS ECS Fargate using Terraform, ALB, ECR, IAM and CloudWatch; automated image delivery and deployment through GitHub Actions OIDC.”

Keep claims about tested rollback, cost savings, load performance or production resilience separate from this evidence.

