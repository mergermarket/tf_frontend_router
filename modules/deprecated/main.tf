variable "name" {}

variable "vpc_id" {}

resource "aws_alb_target_group" "target_group" {
  name = "${replace(replace(var.name, "/(.{0,24}).*/", "$1"), "/^-+|-+$/", "")}-default"

  # port will be set dynamically, but for some reason AWS requires a value
  port                 = "31337"
  protocol             = "HTTP"
  vpc_id               = "${var.vpc_id}"
  deregistration_delay = "10"

  health_check {
    interval            = "5"
    path                = "/internal/healthcheck"
    timeout             = "4"
    healthy_threshold   = "2"
    unhealthy_threshold = "2"
    matcher             = "200-299"
  }

  lifecycle {
    create_before_destroy = true
  }
}
