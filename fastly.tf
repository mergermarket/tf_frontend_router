module "fastly" {
    source = "git::https://github.com/mergermarket/tf_fastly_frontend.git"

  domain_name               = "${var.fastly_domain}"
  bare_redirect_domain_name = "${var.bare_redirect_domain_name}"
  backend_address           = "${module.alb.alb_dns_name}"
  env                       = "${var.env}"
  caching                   = "${var.fastly_caching}"
  ssl_cert_check            = "${var.ssl_cert_check}"
  ssl_cert_hostname         = "${format("%s-%s%s.%s", var.env, var.component, var.env != "live" ? ".dev" : "", var.alb_domain)}"
  connect_timeout           = "${var.connect_timeout}"
  first_byte_timeout        = "${var.first_byte_timeout}"
  between_bytes_timeout     = "${var.between_bytes_timeout}"
}
