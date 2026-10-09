resource "aws_cloudwatch_log_group" "app" {
  name              = "/ecs/${var.project_name}"
  retention_in_days = 7
}
resource "aws_ecs_cluster" "main" {
  name = var.project_name
  setting {
    name  = "containerInsights"
    value = "disabled"
  }
}
resource "aws_ecs_task_definition" "app" {
  family                   = var.project_name
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = var.execution_role_arn
  task_role_arn            = var.task_role_arn
  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }
  container_definitions = jsonencode([{
    name            = "api", image = var.image_uri, essential = true,
    user            = "10001:10001", readonlyRootFilesystem = true,
    portMappings    = [{ containerPort = 8000, hostPort = 8000, protocol = "tcp" }],
    environment     = [{ name = "APP_ENV", value = "aws-demo" }, { name = "APP_REVISION", value = var.app_revision }],
    linuxParameters = { capabilities = { drop = ["ALL"] } },
    healthCheck = {
      command  = ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/readyz', timeout=2)"],
      interval = 30, timeout = 5, retries = 3, startPeriod = 20
    },
    logConfiguration = { logDriver = "awslogs", options = { awslogs-group = aws_cloudwatch_log_group.app.name, awslogs-region = var.aws_region, awslogs-stream-prefix = "api", mode = "non-blocking", max-buffer-size = "4m" } }
  }])
}
resource "aws_ecs_service" "app" {
  name                               = var.project_name
  cluster                            = aws_ecs_cluster.main.id
  task_definition                    = aws_ecs_task_definition.app.arn
  desired_count                      = var.desired_count
  launch_type                        = "FARGATE"
  platform_version                   = "1.4.0"
  deployment_minimum_healthy_percent = 100
  deployment_maximum_percent         = 200
  health_check_grace_period_seconds  = 60
  wait_for_steady_state              = true
  enable_execute_command             = false
  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }
  network_configuration {
    subnets          = aws_subnet.public[*].id
    security_groups  = [aws_security_group.task.id]
    assign_public_ip = true
  }
  load_balancer {
    target_group_arn = aws_lb_target_group.app.arn
    container_name   = "api"
    container_port   = 8000
  }
  timeouts {
    create = "20m"
    update = "20m"
    delete = "20m"
  }
  depends_on = [aws_lb_listener.http, aws_lb_listener.https, aws_route.internet, aws_route_table_association.public, aws_vpc_security_group_ingress_rule.task_from_alb, aws_vpc_security_group_egress_rule.task_https, aws_vpc_security_group_egress_rule.alb_to_task]
}
