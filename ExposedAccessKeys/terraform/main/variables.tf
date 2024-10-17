variable "region" {
  description = "AWS Region"
  default = "eu-west-1"
}

variable "email" {
  type  = string
  description = "Email address for security notification"
}