Frontend Router terraform module
================================

[![Build Status](https://travis-ci.org/mergermarket/tf_frontend_router.svg?branch=no-default-service)](https://travis-ci.org/mergermarket/tf_frontend_router)

This modules crates components needed to be able to expose your application(s) to the public.

When included and configured this module will:
- create public ALB
- create a HTTPS Listener on default ALB with default rule
- the default rule will be either 404 service (microservice which returns 404 responses to all requests) or haproxy proxy which will proxy all requests to configured `BACKEND_IP`
- output ALB Listener ARN and DNS Record for the ALB - you'll need both to be able to integrate your services with the ALB
- create Fastly configuration and 1:1 map it to the ALB (Fastly will log all requests to Logentries by default)

Finaly product is AWS ALB which you can configure your services to be attached.

**NOTE** - in order to use underlying Fastly dependency (within `tf_fastly_frontend`), you must set `LOGENTRIES_ACCOUNT_KEY` environment variable before you use this module - otherwise `tf_fastly_frontend` module won't be able to create Logentries Logset and will fail.

Module Input Variables
----------------------

- `fastly_domain` - (string) - **REQUIRED** - DNS Domain name to be used as a entry to the service (Fastly will be configured to use it)
- `team` - (string) - **REQUIRED** - Name of Team deploying the ALB - will affect ALBs name
- `env` - (string) - **REQUIRED** - Environment deployed to
- `component` - (string) - **REQUIRED** - component name
- `platform_config` - (map) **REQUIRED** - Mergermarket Platform config dictionary (see tests for example one)
- `alb_domain` - (string) - **REQUIRED** DNS Domain name to be used as a entry to the service (Fastly will be configured to use it)
- `bare_redirect_domain_name` - (string) - If set, a service will be created in live to redirect this bare domain to the prefixed version - for example you might set this value to `my-site.com` in order to redirect users to `www.my-site.com` (default `""`, i.e. will not be used)
- `backend_ip` - (string) - If set to IP - it'll cause a proxying service to be deployed that will proxy - by default - all requests to given IP; this IP should be / can be different per environment and configured via `config` mechanism.  Default `404` - will deploy service that - by default - returns 404s to all requests
- `backend_port` - (string) - Port number the requests to the backend will be sent to (default `80`)
- `fastly_caching` - (bool) - Controls whether to enable / forcefully disable caching (default: true)
- `ssl_cert_check` - (bool) - Check the backend cert is valid - warning disabling this makes you vulnerable to a man-in-the-middle imporsonating your backend (default `true`)
- `ssl_cert_hostname` - (bool) - The hostname to validate the certificate presented by the backend against (default `""`)
- `health_check_interval` - (string) - (default "5") The approximate amount of time, in seconds, between health checks of an individual target. Minimum value 5 seconds, Maximum value 300 seconds.
- `health_check_path` - (string) - The destination for the health check request (default `"/internal/healthcheck"`)
- `health_check_timeout` - (string) - The amount of time, in seconds, during which no response means a failed health check (default `"4"`)
- `health_check_healthy_threshold` - (string) - The number of consecutive health checks successes required before considering an unhealthy target healthy (default `"2"`)
- `health_check_unhealthy_threshold` - (string) - The number of consecutive health check failures required before considering the target unhealthy (default `"2"`)
- `health_check_matcher` - (string) - The HTTP codes to use when checking for a successful response from a target. You can specify multiple values (for example, "200,202") or a range of values (for example, "200-299") (default `"200-299"`) 

Usage
-----
```hcl

# the below platform_config map can be passed as a TF var-file (eg. JSON file)
variable "platform_config" {
  type = "map"
  default  = {
    platform_config: {
      azs: "eu-west-1a,eu-west-1b,eu-west-1c",
      elb_certificates.domain_com: "arn:aws:acm:us-east-1:123456789012:certificate/12345678-1234-1234-1234-123456789012",
      route53_zone_id.domain_com: "AAAAAAAAAAAAA",
      ecs_cluster.default.client_security_group: "sg-00000000",
      ecs_cluster.default.security_group: "sg-11111111",
      vpc: "vpc-12345678",
      public_subnets: "subnet-00000000,subnet-11111111,subnet-22222222",
      logentries_fastly_logset_id: "111-222-333-444-555"
    }
  }
}

module "frontend_router" {
  source = "github.com/mergermarket/tf_frontend_router"

  fastly_domain   = "www.externaldomain.com"
  le_logset_id    = "${lookup(var.platform_config, "logentries_fastly_logset_id")}"
  alb_domain      = "domain.com"
  team            = "humptydumptyteam"
  env             = "ci"
  component       = "wall"
  platform_config = "${var.platform_config}"

  # optional
  # backend_ip              = "1.1.1.1"
  # fastly_caching          = "false"
  bare_redirect_domain_name = "externaldomain.com"
}
```

Outputs
-------
- `alb_dns_name` - The DNS name of the load balancer
- `alb_listener_arn` - The ARN of the load balancer
