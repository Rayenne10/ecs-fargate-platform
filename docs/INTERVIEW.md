# Explain the project in an interview

## 60-second pitch

“This project automates deployment of a stateless FastAPI service on AWS ECS Fargate. Terraform provisions the VPC, load balancer, task/service configuration and logging. A separate bootstrap creates ECR, locked S3 state and IAM/OIDC foundations. GitHub Actions checks the application and infrastructure, builds an immutable image, and uses short-lived OIDC credentials to apply the new image through Terraform. It verifies both the actual ECS revision and the revision served through the ALB. The default architecture is a small demo with an explicitly documented networking and cost tradeoff.”

Only add “I deployed it successfully” after your own real AWS verification. State which actions you personally reviewed, ran, or changed in this AI-assisted implementation.

## Questions and answers

**Why Fargate?** It runs container tasks without managing EC2 hosts. You still own the image, network design, IAM, resource sizing, deployment behavior and application operations.

**ECS versus EKS?** ECS is an AWS-native orchestrator and Fargate is a compute option. EKS provides managed Kubernetes. This small application does not need a Kubernetes control plane; ECS makes a compact AWS deployment example.

**Why an ALB?** It provides the client entry point, HTTP/HTTPS listener, health checks and routing to task IPs that can change between releases. awsvpc/Fargate requires IP targets, not instance targets.

**Why Terraform for releases too?** Having one owner for the service/task-definition revision avoids drift between an out-of-band CI rollout and the next infrastructure apply. Deployments take Terraform's planning/state overhead, but the ownership is explicit.

**How does OIDC work?** GitHub requests a signed token. AWS STS validates it against the provider/trust policy and returns temporary credentials. The trust matches the exact subject and sts.amazonaws.com audience. New repo subjects may include immutable IDs; inspect the real token claims instead of guessing.

**Task role versus execution role?** The execution role lets ECS pull this repository's image and publish this app's logs. The application task role is available to the running app but has no permissions because the demo calls no AWS API. CI gets a third, distinct deployment role.

**How is state protected?** S3 versioning, server-side encryption, blocked public access, TLS-only policy and explicit state/lock permissions. use_lockfile=true enables locking. Bootstrap state remains local and needs secure preservation.

**Why not mutable latest tags?** Digest-pinned task definitions identify exact image content. Immutable commit tags prevent replacement; repeated runs reuse a release. Changing the source without changing the immutable release is not allowed.

**How does rollback work?** The ECS circuit breaker can return to the last healthy completed deployment. Intentional rollback chooses an existing previous image digest and applies it using current infrastructure. The first deployment lacks a previous completed release.

**Why verify after Terraform says stable?** Stability can follow an automatic rollback. The checker requires the intended task definition and served app revision, so an old healthy version is not mistaken for a successful new release.

**Are tasks private?** No: the demo uses public subnets/IPs for outbound connectivity, but task ingress is restricted to the ALB SG. This avoids NAT infrastructure for the lab. A production alternative is private subnets with deliberate NAT or VPC endpoint connectivity.

**Is it highly available?** The ALB/subnets span two zones, but one default task is not redundant running capacity. Two tasks improve capacity redundancy; it does not replace a full reliability analysis, scaling policy or load tests.

**What did you test?** Refer to VERIFICATION.md: API tests, script failure behavior, Terraform validation/mock plans, and any actual CI/container/browser runs. Mock provider plans do not prove AWS permissions or service integration.

**What would you improve?** First complete real deployment, failed-release and cleanup experiments. Then evaluate private networking, scoped resource IAM, autoscaling, TLS/DNS automation, and operational alerts against concrete needs.

## A five-minute demo

1. Show the API workspace and revision.
2. Trace commit → ECR digest → Terraform task definition → ECS → ALB response.
3. Show OIDC trust and distinct IAM roles; explain no long-lived CI access keys.
4. Show CI, a real deployment receipt if available, and JSON logs.
5. Explain networking tradeoffs, rollback verification and cleanup.

## CV wording

Before cloud verification: “Implemented Terraform infrastructure and an OIDC-authenticated GitHub Actions pipeline for a containerized FastAPI service on ECS Fargate, with ALB routing, ECR, IAM and CloudWatch logging.”

After successful AWS verification: “Provisioned and deployed...” becomes defensible. Do not invent uptime, savings, users or availability figures.
