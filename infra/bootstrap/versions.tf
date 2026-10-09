terraform {
  required_version = ">= 1.13.5, < 2.0.0"
  required_providers {
    aws = { source = "hashicorp/aws", version = "6.46.0" }
  }
}
provider "aws" {
  region = var.aws_region
  default_tags {
    tags = { Project = var.project_name, ManagedBy = "Terraform" }
  }
}
data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}
locals {
  account_id = data.aws_caller_identity.current.account_id
  partition  = data.aws_partition.current.partition
  oidc_arn   = var.existing_oidc_provider_arn != "" ? var.existing_oidc_provider_arn : aws_iam_openid_connect_provider.github[0].arn
  state_key  = "workload/terraform.tfstate"
}
