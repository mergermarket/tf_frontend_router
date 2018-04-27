# required
variable "fastly_domain" {
  description = ""
  type        = "string"
}

variable "env" {
  description = "Environment name"
}

variable "team" {
  description = "Team that owns the service"
}

variable "component" {
  description = "Component name"
}

variable "platform_config" {
  description = "Platform configuration"
  type        = "map"
  default     = {}
}

variable "alb_domain" {
  description = ""
  type        = "string"
}

# optional
variable "bare_redirect_domain_name" {
  type        = "string"
  default     = ""
  description = "If set then an additional service will be created to redirect the zone apex (bare domain) to the domain - i.e. add the www."
}

variable "backend_ip" {
  description = "Backend to route all requests by default to; default: 404 (see README)"
  type        = "string"
  default     = "404"
}

variable "backend_port" {
  description = "Backend port to use; default: 80"
  type        = "string"
  default     = "80"
}

variable "ssl_cert_check" {
  description = "Check the backend cert is valid"
  type        = "string"
  default     = "true"
}

variable "ssl_cert_hostname" {
  description = "The hostname to validate the certificate presented by the backend against"
  type        = "string"
  default     = ""
}

variable "force_ssl" {
  type        = "string"
  description = "Whether or not to force SSL (redirect requests to HTTP to HTTPS)"
  default     = "true"
}

variable "fastly_caching" {
  description = "Whether to enable / forcefully disable caching on Fastly (default: true)"
  type        = "string"
  default     = "true"
}

variable "connect_timeout" {
  type        = "string"
  description = ""
  default     = 5000
}

variable "first_byte_timeout" {
  type        = "string"
  description = ""
  default     = 60000
}

variable "between_bytes_timeout" {
  type        = "string"
  description = ""
  default     = 30000
}

variable "default_target_group_deregistration_delay" {
  description = "The amount time for Elastic Load Balancing to wait before changing the state of a deregistering target from draining to unused. The range is 0-3600 seconds."
  type        = "string"
  default     = "10"
}

variable "default_target_group_health_check_interval" {
  description = "The approximate amount of time, in seconds, between health checks of an individual target. Minimum value 5 seconds, Maximum value 300 seconds."
  type        = "string"
  default     = "5"
}

variable "default_target_group_health_check_path" {
  description = "The destination for the health check request."
  type        = "string"
  default     = "/internal/healthcheck"
}

variable "default_target_group_health_check_timeout" {
  description = "The amount of time, in seconds, during which no response means a failed health check."
  type        = "string"
  default     = "4"
}

variable "default_target_group_health_check_healthy_threshold" {
  description = "The number of consecutive health checks successes required before considering an unhealthy target healthy."
  type        = "string"
  default     = "2"
}

variable "default_target_group_health_check_unhealthy_threshold" {
  description = "The number of consecutive health check failures required before considering the target unhealthy."
  type        = "string"
  default     = "2"
}

variable "default_target_group_health_check_matcher" {
  description = "The HTTP codes to use when checking for a successful response from a target. You can specify multiple values (for example, \"200,202\") or a range of values (for example, \"200-299\")."
  type        = "string"
  default     = "200-299"
}

variable "custom_vcl_backends" {
  type        = "string"
  description = "Custom VCL to add at the top level (e.g. for defining backends)"
  default     = ""
}

variable "custom_vcl_recv" {
  type        = "string"
  description = "Custom VCL to add to the vcl_recv sub after the Fastly hook - this will run regardless of whether running on a shield node"
  default     = ""
}

variable "custom_vcl_recv_shield_only" {
  type        = "string"
  description = "Custom VCL to add to the vcl_recv sub after the Fastly hook, only on shield nodes"
  default     = ""
}

variable "custom_vcl_recv_no_shield" {
  type        = "string"
  description = "Custom VCL to add to the vcl_recv sub after the Fastly hook, but not on shield nodes"
  default     = ""
}

variable "default_target_group_target_type" {
  description = "The type of target that you must specify when registering targets with the default target group. The possible values are instance (targets are specified by instance ID) or ip (targets are specified by IP address). The default is instance."
  type        = "string"
  default     = "instance"
}

variable "custom_vcl_error" {
  type        = "string"
  description = "Custom VCL to add to the vcl_error sub after the Fastly hook"
  default     = ""
}

variable "bypass_busy_wait" {
  type = "string"
  description = "Disable collapsed forwarding, so you don't wait for other objects to origin."
  default = "false"
}

variable "proxy_error_response" {
  type        = "string"
  description = "The html error document to send for a proxy error - 502/503 from backend, or no response from backend at all."

  default = <<EOF
<!DOCTYPE html>
<html>
  <head>
    <title>Service Unavailable</title>
  </head>
  <body>
    <h1>Service Unavailable</h1>
    <p>
      The site you requested is currently unavailable.
    </p>
  </body>
</html>
EOF
}

variable "ecs_cluster" {
  type        = "string"
  description = "The ecs cluster where the services will run (for the security group)."
  default     = "default"
}

variable "shield" {
  type        = "string"
  description = "PoP to use as an origin shield (e.g. london-uk for Slough)."
  default     = ""
}
