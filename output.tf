output "alb_dns_name" {
  value = "${module.alb.alb_dns_name}"
}

output "alb_listener_arn" {
  value = "${module.alb.alb_listener_arn}"
}
