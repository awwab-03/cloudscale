variable "region" {
  type    = string
  default = "us-east-1"
}

variable "name_prefix" {
  type    = string
  default = "cloudscale"
}

variable "vpc_cidr" {
  type    = string
  default = "10.20.0.0/16"
}

variable "azs" {
  type    = list(string)
  default = ["us-east-1a", "us-east-1b"]
}

variable "public_subnet_cidrs" {
  type    = list(string)
  default = ["10.20.1.0/24", "10.20.2.0/24"]
}

variable "private_app_subnet_cidrs" {
  type    = list(string)
  default = ["10.20.11.0/24", "10.20.12.0/24"]
}

variable "private_db_subnet_cidrs" {
  type    = list(string)
  default = ["10.20.21.0/24", "10.20.22.0/24"]
}

variable "app_version" {
  description = "Version of s3://<artifacts>/app/app-<version>.zip. Changing it triggers a rolling instance refresh."
  type        = string
  default     = "1.0.1"
}

variable "app_instance_type" {
  type    = string
  default = "t3.micro"
}

variable "nat_instance_type" {
  type    = string
  default = "t4g.micro"
}
