module "fastly" {
  source = "git::https://github.com/mergermarket/tf_fastly_frontend.git"

  domain_name           = "${var.fastly_domain}"
  backend_address       = "${module.alb.alb_dns_name}"
  env                   = "${var.env}"
  caching               = "${var.fastly_caching}"
  ssl_cert_check        = "${var.ssl_cert_check}"
  ssl_cert_hostname     = "${var.ssl_cert_hostname}"
  connect_timeout       = "${var.connect_timeout}"
  first_byte_timeout    = "${var.first_byte_timeout}"
  between_bytes_timeout = "${var.between_bytes_timeout}"
}
