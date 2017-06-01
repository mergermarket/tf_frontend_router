# configure provider to not try too hard talking to AWS API
provider "aws" {
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_get_ec2_platforms      = true
  skip_region_validation      = true
  skip_requesting_account_id  = true
  max_retries                 = 1
  access_key                  = "a"
  secret_key                  = "a"
  region                      = "eu-west-1"
}

module "frontend_router" {
  source = "../.."

  dns_domain      = "${var.dns_domain}"
  team            = "${var.team}"
  env             = "${var.env}"
  component       = "${var.component}"
  platform_config = "${var.platform_config}"

  # optional
  # backend_ip = "1.1.1.1"
}

# variables
variable "dns_domain" {}

variable "team" {}

variable "env" {}

variable "component" {}

variable "backend_ip" {
	default = "404"
}

variable "platform_config" {
  type = "map"
}

