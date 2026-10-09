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
variable "image_uri" {
  type        = string
  description = "Immutable ECR image URL including @sha256 digest."
  validation {
    condition     = can(regex("^[0-9]{12}[.]dkr[.]ecr[.][a-z0-9-]+[.]amazonaws[.]com/[a-z0-9/_-]+@sha256:[a-f0-9]{64}$", var.image_uri))
    error_message = "Use an ECR image with an immutable sha256 digest, not a mutable tag."
  }
}
variable "app_revision" {
  type        = string
  description = "40-character commit SHA associated with the deployed image."
  validation {
    condition     = can(regex("^[a-f0-9]{40}$", var.app_revision))
    error_message = "Use a complete lowercase Git commit SHA."
  }
}
variable "execution_role_arn" {
  type = string
}
variable "task_role_arn" {
  type = string
}
variable "vpc_cidr" {
  type    = string
  default = "10.42.0.0/16"
}
variable "desired_count" {
  type    = number
  default = 1
  validation {
    condition     = contains([1, 2], var.desired_count)
    error_message = "This lab supports one or two tasks."
  }
}
variable "allowed_ingress_cidrs" {
  type        = set(string)
  default     = ["0.0.0.0/0"]
  description = "Who can reach the ALB. Restrict to your IP when possible."
  validation {
    condition     = length(var.allowed_ingress_cidrs) > 0 && alltrue([for c in var.allowed_ingress_cidrs : can(cidrnetmask(c))])
    error_message = "Supply at least one IPv4 CIDR."
  }
}
variable "certificate_arn" {
  type        = string
  default     = ""
  description = "Optional ACM certificate in the deployment region. Without this, demo uses HTTP."
}
variable "public_hostname" {
  type        = string
  default     = ""
  description = "DNS name covered by the ACM certificate; configure its ALB DNS alias externally."
  validation {
    condition     = (var.certificate_arn == "" && var.public_hostname == "") || (var.certificate_arn != "" && can(regex("^[a-zA-Z0-9.-]+$", var.public_hostname)))
    error_message = "Provide both certificate_arn and its public_hostname for HTTPS, or neither for HTTP."
  }
}
variable "alarm_actions" {
  type        = list(string)
  default     = []
  description = "Optional existing SNS topic ARNs. Empty means alarms have no notifications."
}
