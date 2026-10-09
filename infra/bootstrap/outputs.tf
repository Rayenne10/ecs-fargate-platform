output "state_bucket" { value = aws_s3_bucket.state.id }
output "ecr_repository" { value = aws_ecr_repository.app.name }
output "ecr_repository_url" { value = aws_ecr_repository.app.repository_url }
output "aws_deploy_role_arn" { value = aws_iam_role.deploy.arn }
output "execution_role_arn" { value = aws_iam_role.execution.arn }
output "task_role_arn" { value = aws_iam_role.task.arn }
output "aws_region" { value = var.aws_region }
output "project_name" { value = var.project_name }
