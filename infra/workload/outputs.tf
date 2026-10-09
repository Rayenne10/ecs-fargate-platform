output "alb_url" { value = var.certificate_arn == "" ? "http://${aws_lb.main.dns_name}" : "https://${var.public_hostname}" }
output "alb_dns_name" { value = aws_lb.main.dns_name }
output "ecs_cluster" { value = aws_ecs_cluster.main.name }
output "ecs_service" { value = aws_ecs_service.app.name }
output "task_definition_arn" { value = aws_ecs_task_definition.app.arn }
output "log_group" { value = aws_cloudwatch_log_group.app.name }
output "image_uri" { value = var.image_uri }
output "app_revision" { value = var.app_revision }
