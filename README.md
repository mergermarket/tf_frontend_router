Frontend Router terraform module
================================

This modules crates components needed to be able to expose your application(s) to the public.

When included and configured this module will:
- create public ALB
- create a HTTPS Listener on default ALB with default rule
- the default rule will be either 404 service (microservice which returns 404 responses to all requests) or haproxy proxy which will proxy all requests to configured `BACKEND_IP`
- output ALB Listener ARN and DNS Record for the ALB - you'll need both to be able to integrate your services with the ALB
- create Fastly configuration and 1:1 map it to the ALB

Finaly product is AWS ALB which you can configure your services to be attached.

Module Input Variables
----------------------

- `dns_domain` - (string) - **REQUIRED** - DNS Domain name to be used as a entry to the service (Fastly will be configured to use it)
- `team` - (string) - **REQUIRED** - Name of Team deploying the ALB - will affect ALBs name
- `env` - (string) - **REQUIRED** - Environment deployed to
- `component` - (string) - **REQUIRED** - component name
- `platform_config` - (map) **REQUIRED** - Mergermarket Platform config dictionary (see tests for example one)
- `backend_ip` - (string) - If set to IP - it'll cause a proxying service to be deployed that will proxy - by default - all requests to given IP; this IP should be / can be different per environment and configured via `config` mechanism.  Default `404` - will deploy service that - by default - returns 404s to all requests

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
      public_subnets: "subnet-00000000,subnet-11111111,subnet-22222222"
    }
  }
}

module "frontend_router" {
  source = "../.."

  dns_domain      = "domain.com"
  team            = "humptydumptyteam"
  env             = "ci"
  component       = "wall"
  platform_config = "${var.platform_config}"

  # optional
  # backend_ip = "1.1.1.1"
}
```

Outputs
-------
- `alb_dns_name` - The DNS name of the load balancer
- `alb_listener_arn` - The ARN of the load balancer
