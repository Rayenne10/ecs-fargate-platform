# Setup: from repository to a verified AWS release

## 1. Prerequisites and local run

Install Docker Desktop, Git, Python 3.11+, AWS CLI v2 (2.32.0+ for browser login), and Terraform 1.13.5 or another version allowed by `versions.tf`. Windows Git Bash is supported for these commands; use `python`/`python.exe` as configured locally. Clone the repository and run `docker compose up --build -d` before provisioning anything. If port 8000 is already occupied, run `APP_PORT=8001 docker compose up --build -d` and open `http://localhost:8001`; the container still listens on 8000.

Use a dedicated AWS lab account if possible. The CI deployment role is region-restricted but can manage regional networking/ECS/ELB resources, not just perfectly isolated project resources. Read `infra/bootstrap/deploy-policy.tf` before granting it in a shared account.

Authenticate locally using your normal AWS CLI profile or IAM Identity Center session. Verify the intended account:

```sh
aws sts get-caller-identity
```

For browser-based console login, use a separate sign-in profile and a credential-process profile that Terraform can consume:

```sh
aws configure set region eu-west-3 --profile fargate-signin
aws login --profile fargate-signin
aws configure set credential_process "aws configure export-credentials --profile fargate-signin --format process" --profile fargate-terraform
aws configure set region eu-west-3 --profile fargate-terraform
export AWS_PROFILE=fargate-terraform
aws sts get-caller-identity
```

Re-run `aws login --profile fargate-signin` when the browser session expires. Set `AWS_PROFILE` again in each new terminal.

Keep credentials out of Git, Terraform variables, and chat. Terraform automatically uses the CLI/environment credential chain. Bootstrap needs appropriate S3, ECR, IAM/OIDC permissions; routine CI does not receive permission to create IAM roles.

## 2. GitHub environment and actual OIDC subject

Create a GitHub environment named **aws-demo**. Restrict its deployment branches to `main`; configure a required reviewer if supported by your account/repository settings and desired workflow. The AWS trust policy binds to this exact environment subject, so branch controls on the environment matter.

Run **Actions → Inspect OIDC subject → Run workflow** on main. Copy only the printed `sub` claim into bootstrap variables. The script does not print the JWT. Newly created repositories can use immutable owner/repository IDs in the subject, so do not copy a legacy example blindly.

If `token.actions.githubusercontent.com` already exists as an IAM OIDC provider in this account, supply its ARN via `existing_oidc_provider_arn`; do not create a duplicate account-wide provider.

## 3. Bootstrap persistent foundations

Check both account-wide service-linked roles before bootstrap:

```sh
aws iam get-role --role-name AWSServiceRoleForECS
aws iam get-role --role-name AWSServiceRoleForElasticLoadBalancing
```

For a `NoSuchEntity` result, set the corresponding bootstrap variable to true: `create_ecs_service_linked_role` for ECS and `create_elb_service_linked_role` for Elastic Load Balancing. An access-denied error does not establish absence. Leave each flag false when its role already exists, including roles created manually during an earlier attempt. Shared existing roles remain outside this stack. CI cannot create IAM roles; the local operator handles this initial setup.

```sh
cp infra/bootstrap/terraform.tfvars.example infra/bootstrap/terraform.tfvars
terraform -chdir=infra/bootstrap init -lockfile=readonly
terraform -chdir=infra/bootstrap plan -out=bootstrap.tfplan
# Read the plan before executing this provisioning step:
terraform -chdir=infra/bootstrap apply bootstrap.tfplan
```

Edit the copied variables first: unique bucket name, project name, region, exact OIDC subject, and optional existing provider. The bucket and ECR repository are created here, before the first image exists. Preserve this local bootstrap state securely; it is not uploaded by CI and must not be committed. The workload uses remote S3 state.

The default project name is `fargate-demo` and region is `eu-west-3`. These must match workload variables and the GitHub values below. All examples target the commercial AWS partition.

## 4. Export non-secret configuration

```sh
python scripts/export_config.py
```

This reads bootstrap outputs and writes ignored local files: `infra/workload/backend.hcl`, `infra/workload/terraform.tfvars`, and `verification/github-variables.json`. The workload variables initially omit the release image/revision; supply them through `TF_VAR_image_uri` and `TF_VAR_app_revision` or use the deployment workflow.

In the GitHub **aws-demo** environment, add the values in `verification/github-variables.json` as **variables**, not AWS access-key secrets:

| Variable | Value |
| --- | --- |
| AWS_REGION | Bootstrap region |
| AWS_DEPLOY_ROLE_ARN | Bootstrap deployment role ARN |
| TF_STATE_BUCKET | Bootstrap S3 state bucket |
| ECR_REPOSITORY | Bootstrap repository name, without registry hostname |
| PROJECT_NAME | Bootstrap project name |
| EXECUTION_ROLE_ARN | Bootstrap execution role ARN |
| TASK_ROLE_ARN | Bootstrap task role ARN |
| ALLOWED_INGRESS_CIDRS | Optional JSON array; default `["0.0.0.0/0"]` |
| CERTIFICATE_ARN / PUBLIC_HOSTNAME | Optional matching ACM certificate and DNS name; both or neither |

Set **ENABLE_AUTO_DEPLOY** as a **repository variable** only when you want every main push to deploy. It is checked before the environment job starts and must not be set only as an environment variable.

By default the ALB demo is publicly reachable over HTTP. Restrict ingress for a personal demo if appropriate, but GitHub-hosted runners also need access for HTTP verification. Their outbound IPs are not a single stable address. A restricted runner/network or a different validation approach is needed if you block them.

For TLS, supply an issued ACM certificate in the deployment region and a hostname it covers; point that hostname to the output ALB DNS name through your own DNS provider. DNS/certificate issuance is not provisioned by this lab. HTTPS verification uses the custom hostname, not the ALB DNS name, to avoid a certificate mismatch.

## 5. Preview, then apply

Run **Actions → Deploy or manage AWS demo** on main with `operation=plan`. CI executes first. The workflow may build and push an ECR image during this preview; it does not apply workload resources. ECR storage is therefore a small persistent side effect of previewing a new release.

Read the displayed plan. Run again with `operation=apply` to apply a freshly computed saved plan. Each run plans and applies its own exact plan; the first preview file is not reused across runs.

The release image is tagged `sha-COMMIT` and the task definition uses `repository@sha256:DIGEST`. Re-running a release reuses its immutable ECR image. The app reports the same commit through `/api/info`.

Terraform waits for ECS steady state. The follow-up verifier checks the service's actual task definition and completed rollout, then reads the app revision through the ALB. A successful run uploads a JSON deployment receipt. Save it as your real deployment evidence.

## 6. Inspect the running system

```sh
aws ecs describe-services --cluster fargate-demo --services fargate-demo --region eu-west-3
MSYS_NO_PATHCONV=1 aws logs tail /ecs/fargate-demo --follow --region eu-west-3
```

The `MSYS_NO_PATHCONV` setting prevents Windows Git Bash from rewriting the log-group path.

Use the workflow receipt URL to inspect the workspace and `/api/info`. ECS/ALB health and logs are useful together: a running task alone does not prove the service is reachable.

If a deployment fails partway through, Terraform retains created resources in remote state. Fix the cause, then run a new plan/apply. Do not delete state or create duplicate resources. If a repository fix changed the bootstrap policy, pull it locally and plan/apply bootstrap first.

## 7. Rollback and cleanup

Follow [OPERATIONS.md](OPERATIONS.md). Disable auto-deployment before cleanup, otherwise a subsequent main push can recreate the workload. Persistent bootstrap resources intentionally remain for state recovery and repeat releases.

## Official references

- [GitHub OIDC with AWS](https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-aws)
- [Terraform S3 backend and lockfile permissions](https://developer.hashicorp.com/terraform/language/backend/s3)
- [Fargate outbound networking](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/networking-outbound.html)
- [ECS with ALB/IP target groups](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/alb.html)

