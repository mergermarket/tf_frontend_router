module "404_container_definition" {
  source = "github.com/mergermarket/tf_ecs_container_definition"

  name           = "404"
  image          = "mergermarket/404"
  cpu            = "16"
  memory         = "16"
  container_port = "80"
}

module "haproxy_proxy_container_definition" {
  source = "github.com/mergermarket/tf_ecs_container_definition"

  name           = "haproxy"
  image          = "mergermarket/haproxy-proxy"
  cpu            = "16"
  memory         = "32"
  container_port = "8000"

  container_env = {
    BACKEND_IP   = "${var.backend_ip}"
    BACKEND_PORT = "${var.backend_port}"
  }
}

module "default_backend_task_definition" {
  source = "github.com/mergermarket/tf_ecs_task_definition"

  family                = "${format("%s-%s", var.env, var.component)}-default"
  container_definitions = ["${var.backend_ip == "404" ? module.404_container_definition.rendered : module.haproxy_proxy_container_definition.rendered}"]
}

module "default_backend_ecs_service" {
  source = "github.com/mergermarket/tf_load_balanced_ecs_service"

  name                             = "${replace(replace(format("%s-%s", var.env, var.component), "/(.{0,24}).*/", "$1"), "/^-+|-+$/", "")}-default"
  container_name                   = "${var.backend_ip == "404" ? "404" : "haproxy"}"
  container_port                   = "${var.backend_ip == "404" ? "80" : "8000"}"
  vpc_id                           = "${var.platform_config["vpc"]}"
  task_definition                  = "${module.default_backend_task_definition.arn}"
  desired_count                    = "${var.env == "live" ? 2 : 1}"
  alb_listener_arn                 = "${module.alb.alb_listener_arn}"
  alb_arn                          = "${module.alb.alb_arn}"
  health_check_path                = "${var.health_check_path}"
  health_check_interval            = "${var.health_check_interval}"
  health_check_timeout             = "${var.health_check_timeout}"
  health_check_healthy_threshold   = "${var.health_check_healthy_threshold}"
  health_check_unhealthy_threshold = "${var.health_check_unhealthy_threshold}"
  health_check_matcher             = "${var.health_check_matcher}"
}

module "alb" {
  source = "github.com/mergermarket/tf_alb.git"

  name                     = "${replace(replace(format("%s-%s", var.env, var.component), "/(.{0,25}).*/", "$1"), "/^-+|-+$/", "")}-router"
  vpc_id                   = "${var.platform_config["vpc"]}"
  subnet_ids               = ["${split(",", var.platform_config["public_subnets"])}"]
  extra_security_groups    = ["${var.platform_config["ecs_cluster.default.client_security_group"]}"]
  internal                 = "false"
  certificate_domain_name  = "${format("*.%s%s", var.env != "live" ? "dev." : "", var.alb_domain)}"
  default_target_group_arn = "${module.default_backend_ecs_service.target_group_arn}"
  access_logs_bucket       = "${lookup(var.platform_config, "elb_access_logs_bucket", "")}"
  access_logs_enabled      = "${"${lookup(var.platform_config, "elb_access_logs_bucket", "")}" == "" ? false : true}"

  tags = {
    component   = "${var.component}"
    environment = "${var.env}"
    team        = "${var.team}"
  }
}

resource "aws_route53_record" "alb_alias" {
  zone_id = "${module.alb.alb_zone_id}"
  name    = "${format("%s-%s%s.%s", var.env, var.component, var.env == "live" ? "" : ".dev", var.alb_domain)}"
  type    = "A"

  alias {
    name                   = "${module.alb.alb_dns_name}"
    zone_id                = "${module.alb.alb_zone_id}"
    evaluate_target_health = true
  }
}
