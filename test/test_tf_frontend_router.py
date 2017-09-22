import os
import re
import shutil
import tempfile
import unittest
from string import ascii_lowercase
from subprocess import check_call, check_output

from hypothesis import example, given
from hypothesis.strategies import fixed_dictionaries, sampled_from, text


def template_to_re(t):
    """
    Takes a template (i.e. what you'd call `.format(...)` on, and
    returns a regex to to match it:
        print(re.match(
            template_to_re("hello {name}"),
            "hello world"
        ).group("name"))
        # prints "world"
    """
    seen = dict()

    def pattern(placeholder, open_curly, close_curly, text):
        if text is not None:
            return re.escape(text)
        elif open_curly is not None:
            return r'\{'
        elif close_curly is not None:
            return r'\}'
        elif seen.get(placeholder):
            return '(?P={})'.format(placeholder)
        else:
            seen[placeholder] = True
            return '(?P<{}>.*?)'.format(placeholder)

    return "".join([
        pattern(*match.groups())
        for match in re.finditer(r'{([\w_]+)}|(\{\{)|(\}\})|([^{}]+)', t)
    ])


class TestTFFrontendRouter(unittest.TestCase):

    def setUp(self):
        self.workdir = tempfile.mkdtemp()
        self.base_path = os.getcwd()
        self.module_path = os.path.join(os.getcwd(), 'test', 'infra')

        check_call(['terraform', 'init', self.module_path], cwd=self.workdir)

    def tearDown(self):
        if os.path.isdir(self.workdir):
            shutil.rmtree(self.workdir)

    def _env_for_check_output(self, fastly_api_key):
        env = os.environ.copy()
        env.update({
            'FASTLY_API_KEY': fastly_api_key
        })
        return env

    def _target_module(self, target):
        submodules = [
            "404_container_definition",
            "haproxy_proxy_container_definition",
            "default_backend_task_definition",
            "default_backend_ecs_service",
            "alb",
            "fastly"
        ]
        return [
            '-target=module.{}.module.{}'.format(target, submodule)
            for submodule in submodules
        ]

    def test_create_correct_number_of_resources(self):
        # When
        output = check_output([
            'terraform',
            'plan',
            '-var', 'env=dev',
            '-var', 'component=foobar',
            '-var', 'team=foobar',
            '-var', 'fastly_domain=externaldomain.com',
            '-var', 'alb_domain=domain.com',
            '-var-file={}/test/platform-config/eu-west-1.json'.format(
                self.base_path
            ),
            '-no-color',
            '-target=module.frontend_router.module.default_backend_ecs_service', # noqa
            '-target=module.frontend_router.module.404_container_definition', # noqa
            '-target=module.frontend_router.module.haproxy_proxy_container_definition', # noqa
            '-target=module.frontend_router.module.default_backend_task_definition', # noqa
            '-target=module.frontend_router.module.default_backend_ecs_service', # noqa
            '-target=module.frontend_router.module.alb.aws_alb.alb', # noqa
            '-target=module.frontend_router.module.fastly', # noqa
        ] + [self.module_path], env=self._env_for_check_output(
            'qwerty'
        ), cwd=self.workdir).decode('utf-8')

        # Then
        assert """
Plan: 13 to add, 0 to change, 0 to destroy.
        """.strip() in output

    @given(fixed_dictionaries({
        'environment': text(alphabet=ascii_lowercase, min_size=1),
        'component': text(alphabet=ascii_lowercase+'-', min_size=1).filter(lambda c: len(c.replace('-', ''))),
        'team': text(alphabet=ascii_lowercase+'-', min_size=1).filter(lambda c: len(c.replace('-', ''))),
    }))
    @example({
        'environment': 'live',
        'component': 'a'*21,
        'team': 'kubric',
    })
    def test_create_default_404_service_target_group(self, fixtures):
        # When
        env = fixtures['environment']
        component = fixtures['component']
        team = fixtures['team']
        output = check_output([
            'terraform',
            'plan',
            '-var', 'env={}'.format(env),
            '-var', 'component={}'.format(component),
            '-var', 'team={}'.format(team),
            '-var', 'fastly_domain=externaldomain.com',
            '-var', 'alb_domain=domain.com',
            '-var-file={}/test/platform-config/eu-west-1.json'.format(
                self.base_path
            ),
            '-no-color',
            '-target=module.frontend_router.module.default_backend_ecs_service', # noqa
        ] + [self.module_path], env=self._env_for_check_output(
            'qwerty'
        ), cwd=self.workdir).decode('utf-8')

        expected_name = re.sub(
            '^-+|-+$', '',
            '{}-{}'.format(env, component)[0:24]
        )

        # Then
        assert re.search(template_to_re("""
  + module.frontend_router.module.default_backend_ecs_service.aws_alb_target_group.target_group
      id:                                        <computed>
      arn:                                       <computed>
      arn_suffix:                                <computed>
      deregistration_delay:                      "10"
      health_check.#:                            "1"
      health_check.{{ident}}.healthy_threshold:          "2"
      health_check.{{ident}}.interval:                   "5"
      health_check.{{ident}}.matcher:                    "200-299"
      health_check.{{ident}}.path:                       "/internal/healthcheck"
      health_check.{{ident}}.port:                       "traffic-port"
      health_check.{{ident}}.protocol:                   "HTTP"
      health_check.{{ident}}.timeout:                    "4"
      health_check.{{ident}}.unhealthy_threshold:        "2"
      name:                                      "{}-default"
      port:                                      "31337"
      protocol:                                  "HTTP"
      stickiness.#:                              <computed>
      vpc_id:                                    "vpc-12345678"
        """.format(expected_name).strip()), output) # noqa

    def test_create_default_404_service_ecs_service(self):
        # When
        output = check_output([
            'terraform',
            'plan',
            '-var', 'env=foo',
            '-var', 'component=foobar',
            '-var', 'team=foobar',
            '-var', 'fastly_domain=externaldomain.com',
            '-var', 'alb_domain=domain.com',
            '-var-file={}/test/platform-config/eu-west-1.json'.format(
                self.base_path
            ),
            '-no-color',
            '-target=module.frontend_router.module.default_backend_ecs_service.aws_ecs_service.service', # noqa
        ] + [self.module_path], env=self._env_for_check_output(
            'qwerty'
        ), cwd=self.workdir).decode('utf-8')

        assert """
  + module.frontend_router.module.default_backend_ecs_service.aws_ecs_service.service
      id:                                        <computed>
      cluster:                                   "default"
      deployment_maximum_percent:                "200"
      deployment_minimum_healthy_percent:        "100"
      desired_count:                             "1"
        """.strip() in output # noqa

        assert """
      name:                                      "foo-foobar-default"
        """.strip() in output # noqa

        assert re.search(template_to_re("""
      placement_strategy.{ident1}.field:       "instanceId"
      placement_strategy.{ident1}.type:        "spread"
        """.strip()), output) # noqa

        assert re.search(template_to_re("""
      placement_strategy.{ident}.field:       "attribute:ecs.availability-zone"
      placement_strategy.{ident}.type:        "spread"
        """.strip()), output) # noqa

    @given(fixed_dictionaries({
        'environment': text(alphabet=ascii_lowercase, min_size=1),
        'component': text(alphabet=ascii_lowercase+'-', min_size=1).filter(lambda c: len(c.replace('-', ''))),
        'team': text(alphabet=ascii_lowercase+'-', min_size=1).filter(lambda c: len(c.replace('-', ''))),
    }))
    @example({
        'environment': 'live',
        'component': 'a'*21,
        'team': 'kubric',
    })
    def test_create_public_alb_in_public_subnets(self, fixtures):
        # Given
        env = fixtures['environment']
        component = fixtures['component']
        team = fixtures['team']

        expected_name = re.sub(
            '^-+|-+$', '',
            '{}-{}'.format(env, component)[0:25]
        )

        # When
        output = check_output([
            'terraform',
            'plan',
            '-var', 'env={}'.format(env),
            '-var', 'component={}'.format(component),
            '-var', 'team={}'.format(team),
            '-var', 'fastly_domain=externaldomain.com',
            '-var', 'alb_domain=domain.com',
            '-var-file={}/test/platform-config/eu-west-1.json'.format(
                self.base_path
            ),
            '-no-color',
            '-target=module.frontend_router.module.alb.aws_alb.alb', # noqa
        ] + [self.module_path], env=self._env_for_check_output(
            'qwerty'
        ), cwd=self.workdir).decode('utf-8')

        # Then
        assert re.search(template_to_re("""
+ module.frontend_router.module.alb.aws_alb.alb
      id:                                    <computed>
      access_logs.#:                         "1"
      access_logs.0.enabled:                 "false"
      arn:                                   <computed>
      arn_suffix:                            <computed>
      dns_name:                              <computed>
      enable_deletion_protection:            "false"
      idle_timeout:                          "60"
      internal:                              "false"
      ip_address_type:                       <computed>
      name:                                  "{}-router"
      security_groups.#:                     <computed>
      subnets.#:                             "3"
      subnets.{{ident1}}:                    "subnet-55555555"
      subnets.{{ident2}}:                    "subnet-33333333"
      subnets.{{ident3}}:                    "subnet-44444444"
      tags.%:                                "3"
      tags.component:                        "{}"
      tags.environment:                      "{}"
      tags.team:                             "{}"
      vpc_id:                                <computed>
      zone_id:                               <computed>
        """.format(expected_name, component, env, team).strip()), output) # noqa

    def test_create_public_alb_listener(self):
        # When
        output = check_output([
            'terraform',
            'plan',
            '-var', 'env=foo',
            '-var', 'component=foobar',
            '-var', 'team=foobar',
            '-var', 'fastly_domain=externaldomain.com',
            '-var', 'alb_domain=domain.com',
            '-var-file={}/test/platform-config/eu-west-1.json'.format(
                self.base_path
            ),
            '-target=module.frontend_router.module.alb.aws_alb_listener.https',
            '-no-color',
            self.module_path
        ], env=self._env_for_check_output(
            'qwerty'
        ), cwd=self.workdir).decode('utf-8')

        # Then
        assert """
  + module.frontend_router.module.alb.aws_alb_listener.https
      id:                                    <computed>
      arn:                                   <computed>
      certificate_arn:                       "${module.aws_acm_certificate_arn.arn}"
      default_action.#:                      "1"
      default_action.0.target_group_arn:     "${var.default_target_group_arn}"
      default_action.0.type:                 "forward"
      load_balancer_arn:                     "${aws_alb.alb.arn}"
      port:                                  "443"
      protocol:                              "HTTPS"
      ssl_policy:                            <computed>
        """.strip() in output # noqa

    def test_create_public_alb_security_group(self):
        # When
        output = check_output([
            'terraform',
            'plan',
            '-var', 'env=foo',
            '-var', 'component=foobar',
            '-var', 'team=foobar',
            '-var', 'fastly_domain=externaldomain.com',
            '-var', 'alb_domain=domain.com',
            '-var-file={}/test/platform-config/eu-west-1.json'.format(
                self.base_path
            ),
            '-no-color',
            '-target=module.frontend_router.module.alb.aws_security_group.default', # noqa
        ] + [self.module_path], env=self._env_for_check_output(
            'qwerty'
        ), cwd=self.workdir).decode('utf-8')

        # Then
        assert re.search(template_to_re("""
  + module.frontend_router.module.alb.aws_security_group.default
      id:                                    <computed>
      description:                           "Managed by Terraform"
      egress.#:                              "1"
      egress.{ident1}.cidr_blocks.#:        "1"
      egress.{ident1}.cidr_blocks.0:        "0.0.0.0/0"
      egress.{ident1}.from_port:            "0"
      egress.{ident1}.ipv6_cidr_blocks.#:   "0"
      egress.{ident1}.prefix_list_ids.#:    "0"
      egress.{ident1}.protocol:             "-1"
      egress.{ident1}.security_groups.#:    "0"
      egress.{ident1}.self:                 "false"
      egress.{ident1}.to_port:              "0"
      ingress.#:                             "1"
      ingress.{ident2}.cidr_blocks.#:      "1"
      ingress.{ident2}.cidr_blocks.0:      "0.0.0.0/0"
      ingress.{ident2}.from_port:          "443"
      ingress.{ident2}.ipv6_cidr_blocks.#: "0"
      ingress.{ident2}.protocol:           "tcp"
      ingress.{ident2}.security_groups.#:  "0"
      ingress.{ident2}.self:               "false"
      ingress.{ident2}.to_port:            "443"
      name:                                  <computed>
      owner_id:                              <computed>
      vpc_id:                                "vpc-12345678"

        """.strip()), output) # noqa

    def test_create_fastly_config(self):
        # When
        output = check_output([
            'terraform',
            'plan',
            '-var', 'env=foo',
            '-var', 'component=foobar',
            '-var', 'team=foobar',
            '-var', 'fastly_domain=externaldomain.com',
            '-var', 'alb_domain=domain.com',
            '-var-file={}/test/platform-config/eu-west-1.json'.format(
                self.base_path
            ),
            '-no-color',
            '-target=module.frontend_router.module.fastly', # noqa
        ] + [self.module_path], env=self._env_for_check_output(
            'qwerty'
        ), cwd=self.workdir).decode('utf-8')

        # Then
        assert re.search(template_to_re("""
  + module.frontend_router.module.fastly.fastly_service_v1.fastly
        """.strip()), output) # noqa

        assert re.search(template_to_re("""
      default_host:                                 "foo-externaldomain.com"
      default_ttl:                                  "60"
      domain.#:                                     "1"
      domain.{ident}.comment:                    ""
      domain.{ident}.name:                       "foo-externaldomain.com"
        """.strip()), output) # noqa

    def test_create_fastly_config_backend(self):
        # When
        output = check_output([
            'terraform',
            'plan',
            '-var', 'env=foo',
            '-var', 'component=foobar',
            '-var', 'team=foobar',
            '-var', 'fastly_domain=externaldomain.com',
            '-var', 'alb_domain=domain.com',
            '-var-file={}/test/platform-config/eu-west-1.json'.format(
                self.base_path
            ),
            '-no-color',
            '-target=module.frontend_router.module.fastly', # noqa
        ] + [self.module_path], env=self._env_for_check_output(
            'qwerty'
        ), cwd=self.workdir).decode('utf-8')

        # Then
        assert re.search(template_to_re("""
      backend.~{ident}.healthcheck:              ""
      backend.~{ident}.max_conn:                 "200"
      backend.~{ident}.name:                     "default backend"
      backend.~{ident}.port:                     "443"
      backend.~{ident}.request_condition:        ""
      backend.~{ident}.shield:                   ""
      backend.~{ident}.ssl_ca_cert:              ""
      backend.~{ident}.ssl_cert_hostname:        ""
      backend.~{ident}.ssl_check_cert:           "true"
      backend.~{ident}.ssl_hostname:             ""
      backend.~{ident}.ssl_sni_hostname:         ""
      backend.~{ident}.weight:                   "100"
        """.strip()), output) # noqa

    def test_create_fastly_config_all_urls_condition(self):
        # When
        output = check_output([
            'terraform',
            'plan',
            '-var', 'env=foo',
            '-var', 'component=foobar',
            '-var', 'team=foobar',
            '-var', 'fastly_domain=externaldomain.com',
            '-var', 'alb_domain=domain.com',
            '-var-file={}/test/platform-config/eu-west-1.json'.format(
                self.base_path
            ),
            '-no-color',
            '-target=module.frontend_router.module.fastly', # noqa
        ] + [self.module_path], env=self._env_for_check_output(
            'qwerty'
        ), cwd=self.workdir).decode('utf-8')

        # Then
        assert re.search(template_to_re("""
      condition.{ident}.name:                     "all_urls"
      condition.{ident}.priority:                 "10"
      condition.{ident}.statement:                "req.url ~ \\".*\\""
      condition.{ident}.type:                     "REQUEST"
        """.strip()), output) # noqa

    def test_create_fastly_config_response_503_condition(self):
        # When
        output = check_output([
            'terraform',
            'plan',
            '-var', 'env=foo',
            '-var', 'component=foobar',
            '-var', 'team=foobar',
            '-var', 'fastly_domain=externaldomain.com',
            '-var', 'alb_domain=domain.com',
            '-var-file={}/test/platform-config/eu-west-1.json'.format(
                self.base_path
            ),
            '-no-color',
            '-target=module.frontend_router.module.fastly', # noqa
        ] + [self.module_path], env=self._env_for_check_output(
            'qwerty'
        ), cwd=self.workdir).decode('utf-8')

        # Then
        assert re.search(template_to_re("""
      condition.{ident}.name:                    "response-503-condition"
      condition.{ident}.priority:                "5"
      condition.{ident}.statement:               "beresp.status == 503"
      condition.{ident}.type:                    "CACHE"
        """.strip()), output) # noqa

    def test_create_fastly_config_response_503_definition(self):
        # When
        output = check_output([
            'terraform',
            'plan',
            '-var', 'env=foo',
            '-var', 'component=foobar',
            '-var', 'team=foobar',
            '-var', 'fastly_domain=externaldomain.com',
            '-var', 'alb_domain=domain.com',
            '-var-file={}/test/platform-config/eu-west-1.json'.format(
                self.base_path
            ),
            '-no-color',
            '-target=module.frontend_router.module.fastly', # noqa
        ] + [self.module_path], env=self._env_for_check_output(
            'qwerty'
        ), cwd=self.workdir).decode('utf-8')

        # Then
        assert re.search(template_to_re("""
      response_object.{ident}.cache_condition:   "response-503-condition"
      response_object.{ident}.content:           "<!DOCTYPE html>
        """.strip()), output) # noqa

        assert re.search(template_to_re("""
      <title>Service Unavailable</title>
        """.strip()), output) # noqa

        assert re.search(template_to_re("""
      response_object.{ident}.content_type:      "text/html"
      response_object.{ident}.name:              "error-response-503"
      response_object.{ident}.request_condition: ""
      response_object.{ident}.response:          "Service Unavailable"
      response_object.{ident}.status:            "503"
        """.strip()), output) # noqa

    def test_create_fastly_config_default_caching_ssl_setting(self):
        # When
        output = check_output([
            'terraform',
            'plan',
            '-var', 'env=foo',
            '-var', 'component=foobar',
            '-var', 'team=foobar',
            '-var', 'fastly_domain=externaldomain.com',
            '-var', 'alb_domain=domain.com',
            '-var-file={}/test/platform-config/eu-west-1.json'.format(
                self.base_path
            ),
            '-no-color',
            '-target=module.frontend_router.module.fastly', # noqa
        ] + [self.module_path], env=self._env_for_check_output(
            'qwerty'
        ), cwd=self.workdir).decode('utf-8')

        # Then
        assert re.search(template_to_re("""
      request_setting.{ident}.action:            ""
      request_setting.{ident}.bypass_busy_wait:  ""
      request_setting.{ident}.default_host:      ""
      request_setting.{ident}.force_miss:        "false"
      request_setting.{ident}.force_ssl:         "true"
      request_setting.{ident}.geo_headers:       ""
      request_setting.{ident}.hash_keys:         ""
      request_setting.{ident}.max_stale_age:     "60"
      request_setting.{ident}.name:              "disable caching"
      request_setting.{ident}.request_condition: "all_urls"
      request_setting.{ident}.timer_support:     ""
      request_setting.{ident}.xff:               "append"
        """.strip()), output) # noqa

    def test_create_fastly_config_headers_obfuscation(self):
        # When
        output = check_output([
            'terraform',
            'plan',
            '-var', 'env=foo',
            '-var', 'component=foobar',
            '-var', 'team=foobar',
            '-var', 'fastly_domain=externaldomain.com',
            '-var', 'alb_domain=domain.com',
            '-var-file={}/test/platform-config/eu-west-1.json'.format(
                self.base_path
            ),
            '-no-color',
            '-target=module.frontend_router_timeouts.module.fastly.fastly_service_v1.fastly', # noqa
        ] + [self.module_path], env=self._env_for_check_output(
            'qwerty'
        ), cwd=self.workdir).decode('utf-8')

        # Then
        assert re.search(template_to_re("""
      header.{ident}.action:                      "delete"
      header.{ident}.cache_condition:             ""
      header.{ident}.destination:                 "http.X-Powered-By"
      header.{ident}.ignore_if_set:               "false"
      header.{ident}.name:                        "Remove X-Powered-By header"
      header.{ident}.priority:                    "100"
      header.{ident}.regex:                       <computed>
      header.{ident}.request_condition:           ""
      header.{ident}.response_condition:          ""
      header.{ident}.source:                      <computed>
      header.{ident}.substitution:                <computed>
      header.{ident}.type:                        "cache"
        """.strip()), output) # noqa

        assert re.search(template_to_re("""
      header.{ident}.action:                      "set"
      header.{ident}.cache_condition:             ""
      header.{ident}.destination:                 "http.Server"
      header.{ident}.ignore_if_set:               "false"
      header.{ident}.name:                        "Obfuscate Server header"
      header.{ident}.priority:                    "100"
      header.{ident}.regex:                       <computed>
      header.{ident}.request_condition:           ""
      header.{ident}.response_condition:          ""
      header.{ident}.source:                      "\\"LHC\\""
      header.{ident}.substitution:                <computed>
      header.{ident}.type:                        "cache"
        """.strip()), output) # noqa

    def test_create_fastly_config_override_robots_txt_condition(self):
        # When
        output = check_output([
            'terraform',
            'plan',
            '-var', 'env=foo',
            '-var', 'component=foobar',
            '-var', 'team=foobar',
            '-var', 'fastly_domain=externaldomain.com',
            '-var', 'alb_domain=domain.com',
            '-var-file={}/test/platform-config/eu-west-1.json'.format(
                self.base_path
            ),
            '-no-color',
            '-target=module.frontend_router.module.fastly', # noqa
        ] + [self.module_path], env=self._env_for_check_output(
            'qwerty'
        ), cwd=self.workdir).decode('utf-8')

        # Then
        assert re.search(template_to_re("""
      condition.{ident}.name:                     "override-robots.txt-condition"
      condition.{ident}.priority:                 "5"
      condition.{ident}.statement:                "req.url ~ \\"^/robots.txt\\""
      condition.{ident}.type:                     "REQUEST"
        """.strip()), output) # noqa

    def test_create_fastly_config_response_502_condition(self):
        # When
        output = check_output([
            'terraform',
            'plan',
            '-var', 'env=foo',
            '-var', 'component=foobar',
            '-var', 'team=foobar',
            '-var', 'fastly_domain=externaldomain.com',
            '-var', 'alb_domain=domain.com',
            '-var-file={}/test/platform-config/eu-west-1.json'.format(
                self.base_path
            ),
            '-no-color',
            '-target=module.frontend_router.module.fastly', # noqa
        ] + [self.module_path], env=self._env_for_check_output(
            'qwerty'
        ), cwd=self.workdir).decode('utf-8')

        # Then
        assert re.search(template_to_re("""
      condition.{ident}.name:                    "response-502-condition"
      condition.{ident}.priority:                "5"
      condition.{ident}.statement:               "beresp.status == 502"
      condition.{ident}.type:                    "CACHE"
        """.strip()), output) # noqa

    def test_create_fastly_config_response_502_definition(self):
        # When
        output = check_output([
            'terraform',
            'plan',
            '-var', 'env=foo',
            '-var', 'component=foobar',
            '-var', 'team=foobar',
            '-var', 'fastly_domain=externaldomain.com',
            '-var', 'alb_domain=domain.com',
            '-var-file={}/test/platform-config/eu-west-1.json'.format(
                self.base_path
            ),
            '-no-color',
            '-target=module.frontend_router.module.fastly', # noqa
        ] + [self.module_path], env=self._env_for_check_output(
            'qwerty'
        ), cwd=self.workdir).decode('utf-8')

        # Then
        assert re.search(template_to_re("""
      response_object.{ident}.cache_condition:   "response-502-condition"
      response_object.{ident}.content:           "<!DOCTYPE html>
        """.strip()), output) # noqa

        assert re.search(template_to_re("""
      <h1>Service Unavailable</h1>
        """.strip()), output) # noqa

        assert re.search(template_to_re("""
      response_object.{ident}.content_type:      "text/html"
      response_object.{ident}.name:              "error-response-502"
      response_object.{ident}.request_condition: ""
      response_object.{ident}.response:          "Bad Gateway"
      response_object.{ident}.status:            "502"
        """.strip()), output) # noqa

    def test_create_fastly_config_gzip_configuration(self):
        # When
        output = check_output([
            'terraform',
            'plan',
            '-var', 'env=foo',
            '-var', 'component=foobar',
            '-var', 'team=foobar',
            '-var', 'fastly_domain=externaldomain.com',
            '-var', 'alb_domain=domain.com',
            '-var-file={}/test/platform-config/eu-west-1.json'.format(
                self.base_path
            ),
            '-no-color',
            '-target=module.frontend_router.module.fastly', # noqa
        ] + [self.module_path], env=self._env_for_check_output(
            'qwerty'
        ), cwd=self.workdir).decode('utf-8')

        # Then
        assert re.search(template_to_re("""
      gzip.#:                                       "1"
      gzip.{ident}.cache_condition:              ""
      gzip.{ident}.content_types.#:              "3"
      gzip.{ident}.content_types.2372034088:     "application/json"
      gzip.{ident}.content_types.366283795:      "text/css"
      gzip.{ident}.content_types.4008173114:     "text/html"
      gzip.{ident}.extensions.#:                 "2"
      gzip.{ident}.extensions.253252853:         "js"
      gzip.{ident}.extensions.3950613225:        "css"
      gzip.{ident}.name:                         "file extensions and content types"
        """.strip()), output) # noqa

    def test_create_fastly_config_disable_fastly_caching(self):
        # When
        output = check_output([
            'terraform',
            'plan',
            '-var', 'env=foo',
            '-var', 'component=foobar',
            '-var', 'team=foobar',
            '-var', 'fastly_domain=externaldomain.com',
            '-var', 'alb_domain=domain.com',
            '-var-file={}/test/platform-config/eu-west-1.json'.format(
                self.base_path
            ),
            '-no-color',
            '-target=module.frontend_router_disable_fastly_caching.module.fastly', # noqa
        ] + [self.module_path], env=self._env_for_check_output(
            'qwerty'
        ), cwd=self.workdir).decode('utf-8')

        # Then
        assert """
  + module.frontend_router_disable_fastly_caching.module.fastly.fastly_service_v1.fastly
        """.strip() in output # noqa

        assert re.search(template_to_re("""
      request_setting.#:                            "1"
      request_setting.{ident}.action:            ""
      request_setting.{ident}.bypass_busy_wait:  ""
      request_setting.{ident}.default_host:      ""
      request_setting.{ident}.force_miss:        "true"
      request_setting.{ident}.force_ssl:         "true"
      request_setting.{ident}.geo_headers:       ""
      request_setting.{ident}.hash_keys:         ""
      request_setting.{ident}.max_stale_age:     "60"
      request_setting.{ident}.name:              "disable caching"
      request_setting.{ident}.request_condition: "all_urls"
      request_setting.{ident}.timer_support:     ""
      request_setting.{ident}.xff:               "append"
        """.strip()), output) # noqa

    def test_custom_timeouts(self):
        # When
        output = check_output([
              'terraform',
              'plan',
              '-var', 'env=foo',
              '-var', 'component=foobar',
              '-var', 'team=foobar',
              '-var', 'fastly_domain=externaldomain.com',
              '-var', 'alb_domain=domain.com',
              '-var', 'connect_timeout=12345',
              '-var', 'first_byte_timeout=54321',
              '-var', 'between_bytes_timeout=31337',
              '-var-file={}/test/platform-config/eu-west-1.json'.format(
                  self.base_path
              ),
            '-no-color',
            '-target=module.frontend_router_timeouts.module.fastly.fastly_service_v1.fastly', # noqa
        ] + [self.module_path], env=self._env_for_check_output(
            'qwerty'
        ), cwd=self.workdir).decode('utf-8')

        # Then
        assert """
  + module.frontend_router_timeouts.module.fastly.fastly_service_v1.fastly
        """.strip() in output # noqa

        assert re.search(template_to_re("""
      backend.~{ident}.between_bytes_timeout:     "31337"
      backend.~{ident}.connect_timeout:           "12345"
      backend.~{ident}.error_threshold:           "0"
      backend.~{ident}.first_byte_timeout:        "54321"
        """.strip()), output) # noqa

    def test_fastly_logging_config(self):
        # Given

        # When
        output = check_output([
            'terraform',
            'plan',
            '-var', 'env=dev',
            '-var', 'component=foobar',
            '-var', 'team=foobar',
            '-var', 'fastly_domain=externaldomain.com',
            '-var', 'alb_domain=domain.com',
            '-var-file={}/test/platform-config/eu-west-1.json'.format(
                self.base_path
            ),
            '-no-color',
            '-target=module.frontend_router_timeouts.module.fastly.fastly_service_v1.fastly', # noqa
        ] + [self.module_path], env=self._env_for_check_output(
            'qwerty'
        ), cwd=self.workdir).decode('utf-8')

        # Then
        assert re.search(template_to_re("""
      logentries.#:                                  "1"
      logentries.~{ident}.format:                 "%h %l %u %t %r %>s"
      logentries.~{ident}.name:                   "dev-externaldomain.com"
      logentries.~{ident}.port:                   "20000"
      logentries.~{ident}.response_condition:     ""
        """.strip()), output) # noqa

        assert """
  + module.frontend_router_timeouts.module.fastly.logentries_log.logs
      id:                                            <computed>
        """.strip() in output # noqa

        assert """
      name:                                          "dev-externaldomain.com"
      retention_period:                              "ACCOUNT_DEFAULT"
      source:                                        "token"
      token:                                         <computed>
        """.strip() in output # noqa
