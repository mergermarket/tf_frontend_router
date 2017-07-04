module "fastly" {
  source = "github.com/mergermarket/tf_fastly_frontend"

  domain_name       = "${var.fastly_domain}"
  backend_address   = "${module.alb.alb_dns_name}"
  env               = "${var.env}"
  caching           = "${var.fastly_caching}"
  ssl_cert_check    = "${var.ssl_cert_check}"
  ssl_cert_hostname = "${var.ssl_cert_hostname}"
}
