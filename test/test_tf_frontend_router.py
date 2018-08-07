import os
import re
import shutil
import tempfile
import unittest
from string import ascii_lowercase
from subprocess import check_call, check_output

from hypothesis import example, given, settings
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

    @classmethod
    def setup_class(cls):
        cls.workdir = tempfile.mkdtemp()
        cls.base_path = os.getcwd()
        cls.module_path = os.path.join(os.getcwd(), 'test', 'infra')

        check_call(['terraform', 'init', cls.module_path], cwd=cls.workdir)

    @classmethod
    def teardown_class(cls):
        try:
            shutil.rmtree(cls.workdir)
        except Exception as e:
            print('Error removing {}: {}', cls.workdir, e)

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
        ] + [self.module_path], env=self._env_for_check_output(
            'qwerty'
        ), cwd=self.workdir).decode('utf-8')

        # Then
        assert """
Plan: 10 to add, 0 to change, 0 to destroy.
        """.strip() in output

    @settings(max_examples=5)
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
      target_type:                               "instance"
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

    @settings(max_examples=5)
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
      access_logs.0.prefix:                  <computed>
      arn:                                   <computed>
      arn_suffix:                            <computed>
      dns_name:                              <computed>
      enable_deletion_protection:            "false"
      idle_timeout:                          "60"
      internal:                              "false"
      ip_address_type:                       <computed>
      load_balancer_type:                    "application"
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
      egress.{ident1}.description:          ""
      egress.{ident1}.from_port:            "0"
      egress.{ident1}.ipv6_cidr_blocks.#:   "0"
      egress.{ident1}.prefix_list_ids.#:    "0"
      egress.{ident1}.protocol:             "-1"
      egress.{ident1}.security_groups.#:    "0"
      egress.{ident1}.self:                 "false"
      egress.{ident1}.to_port:              "0"
      ingress.#:                             "2"
      ingress.{ident2}.cidr_blocks.#:      "1"
      ingress.{ident2}.cidr_blocks.0:      "0.0.0.0/0"
      ingress.{ident2}.description:        ""
      ingress.{ident2}.from_port:          "80"
      ingress.{ident2}.ipv6_cidr_blocks.#: "0"
      ingress.{ident2}.protocol:           "tcp"
      ingress.{ident2}.security_groups.#:  "0"
      ingress.{ident2}.self:               "false"
      ingress.{ident2}.to_port:            "80"
      ingress.{ident3}.cidr_blocks.#:      "1"
      ingress.{ident3}.cidr_blocks.0:      "0.0.0.0/0"
      ingress.{ident3}.description:        ""
      ingress.{ident3}.from_port:          "443"
      ingress.{ident3}.ipv6_cidr_blocks.#: "0"
      ingress.{ident3}.protocol:           "tcp"
      ingress.{ident3}.security_groups.#:  "0"
      ingress.{ident3}.self:               "false"
      ingress.{ident3}.to_port:            "443"
      name:                                  <computed>
      owner_id:                              <computed>
      revoke_rules_on_delete:                "false"
      vpc_id:                                "vpc-12345678"
        """.strip()), output) # noqa


