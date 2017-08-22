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
  container_port = "80"

  container_env = {
    BACKEND_IP = "${var.backend_ip}"
  }
}

module "default_backend_task_definition" {
  source = "github.com/mergermarket/tf_ecs_task_definition"

  family                = "${join("", slice(split("", format("%s-%s", var.env, var.component)), 0, length(format("%s-%s", var.env, var.component)) > 22 ? 23 : length(format("%s-%s", var.env, var.component))))}-default"
  container_definitions = ["${var.backend_ip == "404" ? module.404_container_definition.rendered : module.haproxy_proxy_container_definition.rendered}"]
}

module "default_backend_ecs_service" {
  source = "github.com/mergermarket/tf_load_balanced_ecs_service"

  name            = "${join("", slice(split("", format("%s-%s", var.env, var.component)), 0, length(format("%s-%s", var.env, var.component)) > 22 ? 23 : length(format("%s-%s", var.env, var.component))))}-default"
  container_name  = "${var.backend_ip == "404" ? "404" : "haproxy"}"
  container_port  = "80"
  vpc_id          = "${var.platform_config["vpc"]}"
  task_definition = "${module.default_backend_task_definition.arn}"
  desired_count   = "${var.env == "live" ? 2 : 1}"
}

module "alb" {
  source = "github.com/mergermarket/tf_alb"

  name                     = "${join("", slice(split("", format("%s-%s", var.env, var.component)), 0, length(format("%s-%s", var.env, var.component)) > 22 ? 23 : length(format("%s-%s", var.env, var.component))))}-router"
  vpc_id                   = "${var.platform_config["vpc"]}"
  subnet_ids               = ["${split(",", var.platform_config["public_subnets"])}"]
  extra_security_groups    = ["${var.platform_config["ecs_cluster.default.client_security_group"]}"]
  internal                 = "false"
  certificate_arn          = "${var.platform_config["elb_certificates.${replace(var.alb_domain, "/\\./", "_")}"]}"
  default_target_group_arn = "${module.default_backend_ecs_service.target_group_arn}"

  tags = {
    component   = "${var.component}"
    environment = "${var.env}"
    team        = "${var.team}"
  }
}
