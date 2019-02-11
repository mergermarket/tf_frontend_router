module "default_backend_ecs_service" {
  source = "modules/deprecated"

  name   = "${format("%s-%s-404", var.env, var.component)}"
  vpc_id = "${var.platform_config["vpc"]}"
}

module "alb" {
  source = "github.com/mergermarket/tf_alb.git"

  name                     = "${replace(replace(format("%s-%s", var.env, var.component), "/(.{0,25}).*/", "$1"), "/^-+|-+$/", "")}-router"
  vpc_id                   = "${var.platform_config["vpc"]}"
  subnet_ids               = ["${split(",", var.platform_config["public_subnets"])}"]
  extra_security_groups    = ["${var.platform_config["ecs_cluster.${var.ecs_cluster}.client_security_group"]}"]
  internal                 = "false"
  certificate_domain_name  = "${format("*.%s%s", var.env != "live" ? "dev." : "", var.alb_domain)}"
  default_target_group_arn = "${aws_alb_target_group.default_target_group.arn}"
  access_logs_bucket       = "${lookup(var.platform_config, "elb_access_logs_bucket", "")}"
  access_logs_enabled      = "${"${lookup(var.platform_config, "elb_access_logs_bucket", "")}" == "" ? false : true}"
  idle_timeout             = "${var.idle_timeout}"
  run_data                 = "${var.run_data}"

  tags = {
    component   = "${var.component}"
    environment = "${var.env}"
    team        = "${var.team}"
  }
}

module "dns_record" {
  source = "github.com/mergermarket/tf_route53_dns"

  domain      = "${var.alb_domain}"
  name        = "${var.component}"
  env         = "${var.env}"
  target      = "${module.alb.alb_dns_name}"
  alb_zone_id = "${module.alb.alb_zone_id}"
  alias       = "1"
}

locals {
  default_target_group_component = "${var.default_target_group_component != "" ? var.default_target_group_component : "${var.component}-default-target-group"}"
}

resource "aws_alb_target_group" "default_target_group" {
  name = "${replace(replace("${var.env}-default-${var.component}", "/(.{0,32}).*/", "$1"), "/^-+|-+$/", "")}"

  # port will be set dynamically, but for some reason AWS requires a value
  port                 = "31337"
  protocol             = "HTTP"
  vpc_id               = "${var.platform_config["vpc"]}"
  deregistration_delay = "${var.default_target_group_deregistration_delay}"
  target_type          = "${var.default_target_group_target_type}"

  health_check {
    interval            = "${var.default_target_group_health_check_interval}"
    path                = "${var.default_target_group_health_check_path}"
    timeout             = "${var.default_target_group_health_check_timeout}"
    healthy_threshold   = "${var.default_target_group_health_check_healthy_threshold}"
    unhealthy_threshold = "${var.default_target_group_health_check_unhealthy_threshold}"
    matcher             = "${var.default_target_group_health_check_matcher}"
  }

  tags {
    component   = "${local.default_target_group_component}"
    environment = "${var.env}"
    service     = "${var.env}-${local.default_target_group_component}"
    team        = "${var.team}"
  }
}
