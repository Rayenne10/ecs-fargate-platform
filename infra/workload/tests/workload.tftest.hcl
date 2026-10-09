mock_provider "aws" {
  mock_data "aws_availability_zones" { defaults = { names = ["eu-west-3a", "eu-west-3b"] } }
}
variables {
  image_uri          = "123456789012.dkr.ecr.eu-west-3.amazonaws.com/fargate-demo@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  app_revision       = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
  execution_role_arn = "arn:aws:iam::123456789012:role/fargate-demo-execution"
  task_role_arn      = "arn:aws:iam::123456789012:role/fargate-demo-task"
}
run "demo_plan" {
  command = plan
  assert {
    condition     = length(aws_subnet.public) == 2 && aws_lb_target_group.app.target_type == "ip"
    error_message = "Fargate needs two configured subnets and IP targets."
  }
  assert {
    condition     = aws_ecs_service.app.deployment_circuit_breaker[0].rollback && aws_ecs_service.app.network_configuration[0].assign_public_ip
    error_message = "Demo networking and rollback configuration changed."
  }
  assert {
    condition     = jsondecode(aws_ecs_task_definition.app.container_definitions)[0].readonlyRootFilesystem && jsondecode(aws_ecs_task_definition.app.container_definitions)[0].user == "10001:10001"
    error_message = "Task must be non-root with a read-only filesystem."
  }
  assert {
    condition     = aws_vpc_security_group_ingress_rule.task_from_alb.from_port == 8000 && aws_vpc_security_group_ingress_rule.task_from_alb.cidr_ipv4 == null
    error_message = "Task ingress must use an ALB security-group reference, not a public CIDR."
  }
}
run "https_plan" {
  command = plan
  variables {
    certificate_arn = "arn:aws:acm:eu-west-3:123456789012:certificate/test"
    public_hostname = "demo.example.com"
  }
  assert {
    condition     = aws_lb_listener.http.default_action[0].type == "redirect" && length(aws_lb_listener.https) == 1 && output.alb_url == "https://demo.example.com"
    error_message = "HTTPS requires redirect and the certificate's own hostname."
  }
}
run "reject_mutable_image" {
  command = plan
  variables { image_uri = "123456789012.dkr.ecr.eu-west-3.amazonaws.com/fargate-demo:latest" }
  expect_failures = [var.image_uri]
}
run "reject_unmatched_tls" {
  command = plan
  variables { certificate_arn = "arn:aws:acm:eu-west-3:123456789012:certificate/test" }
  expect_failures = [var.public_hostname]
}
