terraform {
  required_version = ">= 1.13.5, < 2.0.0"
  backend "s3" {}
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
data "aws_availability_zones" "available" { state = "available" }
locals {
  azs    = slice(data.aws_availability_zones.available.names, 0, 2)
  labels = { application = var.project_name }
}
