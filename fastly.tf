module "fastly" {
  source = "github.com/mergermarket/tf_fastly_frontend"

  domain_name     = "${var.dns_domain}"
  backend_address = "${module.alb.alb_dns_name}"
  env             = "${var.env}"
}
