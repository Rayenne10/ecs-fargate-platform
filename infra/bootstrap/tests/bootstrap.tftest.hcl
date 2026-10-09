mock_provider "aws" {
  mock_data "aws_iam_policy_document" {
    defaults = { json = "{\"Version\":\"2012-10-17\",\"Statement\":[]}" }
  }
  mock_data "aws_caller_identity" { defaults = { account_id = "123456789012" } }
  mock_data "aws_partition" { defaults = { partition = "aws" } }
}
variables {
  state_bucket_name   = "test-fargate-state-123456789012"
  github_oidc_subject = "repo:Rayenne10@62967449/ecs-fargate-platform@12345:environment:aws-demo"
}
run "bootstrap_plan" {
  command = plan
  assert {
    condition     = aws_ecr_repository.app.image_tag_mutability == "IMMUTABLE" && aws_ecr_repository.app.image_scanning_configuration[0].scan_on_push
    error_message = "Repository must scan pushes and reject tag replacement."
  }
  assert {
    condition     = aws_s3_bucket_versioning.state.versioning_configuration[0].status == "Enabled" && aws_s3_bucket_public_access_block.state.block_public_policy
    error_message = "State requires versioning and public-access blocking."
  }
}
run "reuse_existing_oidc" {
  command = plan
  variables { existing_oidc_provider_arn = "arn:aws:iam::123456789012:oidc-provider/token.actions.githubusercontent.com" }
  assert {
    condition     = length(aws_iam_openid_connect_provider.github) == 0
    error_message = "Do not create a duplicate account-wide OIDC provider."
  }
}
run "reject_wildcard_trust" {
  command = plan
  variables { github_oidc_subject = "repo:Rayenne10/*:environment:aws-demo" }
  expect_failures = [var.github_oidc_subject]
}

run "create_missing_service_roles" {
  command = plan
  variables {
    create_ecs_service_linked_role = true
    create_elb_service_linked_role = true
  }
  assert {
    condition     = length(aws_iam_service_linked_role.ecs) == 1 && length(aws_iam_service_linked_role.elb) == 1
    error_message = "New accounts require both ECS and load-balancing service-linked roles."
  }
}
run "reuse_existing_service_roles" {
  command = plan
  assert {
    condition     = length(aws_iam_service_linked_role.ecs) == 0 && length(aws_iam_service_linked_role.elb) == 0
    error_message = "Existing account-wide roles must not be created again."
  }
}

