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
  description = "Custom VCL to add to the vcl_recv sub after the Fastly hook"
  default     = ""
}
