variable "aws_region" {
  type    = string
  default = "eu-west-3"
}
variable "project_name" {
  type    = string
  default = "fargate-demo"
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,19}$", var.project_name))
    error_message = "Use a 3-20 character lowercase project name."
  }
}
variable "state_bucket_name" {
  type        = string
  description = "Globally unique state bucket name, e.g. rayenne-fargate-state-ACCOUNT."
}
variable "github_oidc_subject" {
  type        = string
  description = "Exact sub claim from the aws-demo environment. New repositories can include immutable owner/repo IDs."
  validation {
    condition     = can(regex("^repo:[^:*]+/[^:*]+:environment:aws-demo$", var.github_oidc_subject))
    error_message = "Provide the exact repo subject ending :environment:aws-demo, without wildcards."
  }
}
variable "existing_oidc_provider_arn" {
  type        = string
  default     = ""
  description = "Reuse the account's GitHub OIDC provider if it already exists."
}
variable "create_ecs_service_linked_role" {
  type        = bool
  default     = false
  description = "Set true only if AWSServiceRoleForECS does not already exist in the account."
}
