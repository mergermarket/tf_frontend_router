import os
import shutil
import tempfile
import unittest
from string import ascii_lowercase
from subprocess import check_call, check_output

from hypothesis import given
from hypothesis.strategies import sampled_from, text


class TestTFFrontendRouter(unittest.TestCase):

    def setUp(self):
        self.workdir = tempfile.mkdtemp()
        self.base_path = os.getcwd()
        self.module_path = os.path.join(os.getcwd(), 'test', 'infra')

        check_call(['terraform', 'get', self.module_path], cwd=self.workdir)

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
            '-var', 'aws_region=eu-west-1',
            '-var', 'fastly_domain=externaldomain.com',
            '-var', 'alb_domain=domain.com',
            '-var-file={}/test/platform-config/eu-west-1.json'.format(
                self.base_path
            ),
            '-no-color'
        ] + self._target_module('frontend_router') + [
            self.module_path
        ], env=self._env_for_check_output('qwerty'), cwd=self.workdir).decode(
            'utf-8'
        )

        # Then
        assert """
Plan: 10 to add, 0 to change, 0 to destroy.
        """.strip() in output

    def test_create_default_404_service_target_group(self):
        # When
        output = check_output([
            'terraform',
            'plan',
            '-var', 'env=foo',
            '-var', 'component=foobar',
            '-var', 'team=foobar',
            '-var', 'aws_region=eu-west-1',
            '-var', 'fastly_domain=externaldomain.com',
            '-var', 'alb_domain=domain.com',
            '-var-file={}/test/platform-config/eu-west-1.json'.format(
                self.base_path
            ),
            '-no-color'
        ] + self._target_module('frontend_router') + [
            self.module_path
        ], env=self._env_for_check_output('qwerty'), cwd=self.workdir).decode(
            'utf-8'
        )

        # Then
        assert """
+ module.frontend_router.default_backend_ecs_service.aws_alb_target_group.target_group
    arn:                                "<computed>"
    arn_suffix:                         "<computed>"
    deregistration_delay:               "10"
    health_check.#:                     "1"
    health_check.0.healthy_threshold:   "2"
    health_check.0.interval:            "5"
    health_check.0.matcher:             "200-299"
    health_check.0.path:                "/internal/healthcheck"
    health_check.0.port:                "traffic-port"
    health_check.0.protocol:            "HTTP"
    health_check.0.timeout:             "4"
    health_check.0.unhealthy_threshold: "2"
    name:                               "foo-foobar-default"
    port:                               "31337"
    protocol:                           "HTTP"
    stickiness.#:                       "<computed>"
    vpc_id:                             "vpc-12345678"
        """.strip() in output # noqa

    def test_create_default_404_service_ecs_service(self):
        # When
        output = check_output([
            'terraform',
            'plan',
            '-var', 'env=foo',
            '-var', 'component=foobar',
            '-var', 'team=foobar',
            '-var', 'aws_region=eu-west-1',
            '-var', 'fastly_domain=externaldomain.com',
            '-var', 'alb_domain=domain.com',
            '-var-file={}/test/platform-config/eu-west-1.json'.format(
                self.base_path
            ),
            '-no-color'
        ] + self._target_module('frontend_router') + [
            self.module_path
        ], env=self._env_for_check_output('qwerty'), cwd=self.workdir).decode(
            'utf-8'
        )

        assert """
+ module.frontend_router.default_backend_ecs_service.aws_ecs_service.service
    cluster:                                    "default"
    deployment_maximum_percent:                 "200"
    deployment_minimum_healthy_percent:         "100"
    desired_count:                              "1"
    iam_role:                                   "${aws_iam_role.role.arn}"
    load_balancer.#:                            "1"
    load_balancer.~2788651468.container_name:   "app"
    load_balancer.~2788651468.container_port:   "8000"
    load_balancer.~2788651468.elb_name:         ""
    load_balancer.~2788651468.target_group_arn: "${aws_alb_target_group.target_group.arn}"
    name:                                       "foo-foobar-default"
    placement_strategy.#:                       "2"
    placement_strategy.2093792364.field:        "attribute:ecs.availability-zone"
    placement_strategy.2093792364.type:         "spread"
    placement_strategy.3946258308.field:        "instanceId"
    placement_strategy.3946258308.type:         "spread"
    task_definition:                            "${var.task_definition}"
        """.strip() in output # noqa

    def test_create_public_alb_in_public_subnets(self):
        # When
        output = check_output([
            'terraform',
            'plan',
            '-var', 'env=foo',
            '-var', 'component=foobar',
            '-var', 'team=foobar',
            '-var', 'aws_region=eu-west-1',
            '-var', 'fastly_domain=externaldomain.com',
            '-var', 'alb_domain=domain.com',
            '-var-file={}/test/platform-config/eu-west-1.json'.format(
                self.base_path
            ),
            '-no-color'
        ] + self._target_module('frontend_router') + [
            self.module_path
        ], env=self._env_for_check_output('qwerty'), cwd=self.workdir).decode(
            'utf-8'
        )

        # Then
        assert """
+ module.frontend_router.alb.aws_alb.alb
    arn:                        "<computed>"
    arn_suffix:                 "<computed>"
    dns_name:                   "<computed>"
    enable_deletion_protection: "false"
    idle_timeout:               "60"
    internal:                   "false"
    ip_address_type:            "<computed>"
    name:                       "foo-foobar-router"
    security_groups.#:          "<computed>"
    subnets.#:                  "1"
    subnets.939944885:          "subnet-33333333,subnet-44444444,subnet-55555555"
    vpc_id:                     "<computed>"
    zone_id:                    "<computed>"
        """.strip() in output # noqa

    def test_create_public_alb_listener(self):
        # When
        output = check_output([
            'terraform',
            'plan',
            '-var', 'env=foo',
            '-var', 'component=foobar',
            '-var', 'team=foobar',
            '-var', 'aws_region=eu-west-1',
            '-var', 'fastly_domain=externaldomain.com',
            '-var', 'alb_domain=domain.com',
            '-var-file={}/test/platform-config/eu-west-1.json'.format(
                self.base_path
            ),
            '-no-color'
        ] + self._target_module('frontend_router') + [
            self.module_path
        ], env=self._env_for_check_output('qwerty'), cwd=self.workdir).decode(
            'utf-8'
        )

        # Then
        assert """
+ module.frontend_router.alb.aws_alb_listener.https
    arn:                               "<computed>"
    certificate_arn:                   "arn:aws:acm:us-east-1:123456789012:certificate/12345678-1234-1234-1234-123456789012"
    default_action.#:                  "1"
    default_action.0.target_group_arn: "${var.default_target_group_arn}"
    default_action.0.type:             "forward"
    load_balancer_arn:                 "${aws_alb.alb.arn}"
    port:                              "443"
    protocol:                          "HTTPS"
    ssl_policy:                        "<computed>"
        """.strip() in output # noqa

    def test_create_public_alb_security_group(self):
        # When
        output = check_output([
            'terraform',
            'plan',
            '-var', 'env=foo',
            '-var', 'component=foobar',
            '-var', 'team=foobar',
            '-var', 'aws_region=eu-west-1',
            '-var', 'fastly_domain=externaldomain.com',
            '-var', 'alb_domain=domain.com',
            '-var-file={}/test/platform-config/eu-west-1.json'.format(
                self.base_path
            ),
            '-no-color'
        ] + self._target_module('frontend_router') + [
            self.module_path
        ], env=self._env_for_check_output('qwerty'), cwd=self.workdir).decode(
            'utf-8'
        )

        # Then
        assert """
+ module.frontend_router.alb.aws_security_group.default
    description:                           "Managed by Terraform"
    egress.#:                              "1"
    egress.482069346.cidr_blocks.#:        "1"
    egress.482069346.cidr_blocks.0:        "0.0.0.0/0"
    egress.482069346.from_port:            "0"
    egress.482069346.ipv6_cidr_blocks.#:   "0"
    egress.482069346.prefix_list_ids.#:    "0"
    egress.482069346.protocol:             "-1"
    egress.482069346.security_groups.#:    "0"
    egress.482069346.self:                 "false"
    egress.482069346.to_port:              "0"
    ingress.#:                             "1"
    ingress.2617001939.cidr_blocks.#:      "1"
    ingress.2617001939.cidr_blocks.0:      "0.0.0.0/0"
    ingress.2617001939.from_port:          "443"
    ingress.2617001939.ipv6_cidr_blocks.#: "0"
    ingress.2617001939.protocol:           "tcp"
    ingress.2617001939.security_groups.#:  "0"
    ingress.2617001939.self:               "false"
    ingress.2617001939.to_port:            "443"
    name:                                  "<computed>"
    owner_id:                              "<computed>"
    vpc_id:                                "vpc-12345678"
        """.strip() in output # noqa

    def test_create_fastly_config(self):
        # When
        output = check_output([
            'terraform',
            'plan',
            '-var', 'env=foo',
            '-var', 'component=foobar',
            '-var', 'team=foobar',
            '-var', 'aws_region=eu-west-1',
            '-var', 'fastly_domain=externaldomain.com',
            '-var', 'alb_domain=domain.com',
            '-var-file={}/test/platform-config/eu-west-1.json'.format(
                self.base_path
            ),
            '-no-color'
        ] + self._target_module('frontend_router') + [
            self.module_path
        ], env=self._env_for_check_output('qwerty'), cwd=self.workdir).decode(
            'utf-8'
        )

        # Then
        assert """
+ module.frontend_router.fastly.fastly_service_v1.fastly
    active_version:                               "<computed>"
    backend.#:                                    "1"
    backend.~1395854901.address:                  "${var.backend_address}"
    backend.~1395854901.auto_loadbalance:         "true"
    backend.~1395854901.between_bytes_timeout:    "30000"
    backend.~1395854901.connect_timeout:          "5000"
    backend.~1395854901.error_threshold:          "0"
    backend.~1395854901.first_byte_timeout:       "60000"
    backend.~1395854901.healthcheck:              ""
    backend.~1395854901.max_conn:                 "200"
    backend.~1395854901.name:                     "default backend"
    backend.~1395854901.port:                     "443"
    backend.~1395854901.request_condition:        ""
    backend.~1395854901.shield:                   ""
    backend.~1395854901.ssl_cert_hostname:        ""
    backend.~1395854901.ssl_check_cert:           "true"
    backend.~1395854901.ssl_hostname:             ""
    backend.~1395854901.ssl_sni_hostname:         ""
    backend.~1395854901.weight:                   "100"
    condition.#:                                  "2"
    condition.212367000.name:                     "all_urls"
    condition.212367000.priority:                 "10"
    condition.212367000.statement:                "req.url ~ \\".*\\""
    condition.212367000.type:                     "REQUEST"
    condition.820439921.name:                     "override-robots.txt-condition"
    condition.820439921.priority:                 "5"
    condition.820439921.statement:                "req.url ~ \\"^/robots.txt\\""
    condition.820439921.type:                     "REQUEST"
    default_host:                                 "foo-www.externaldomain.com"
    default_ttl:                                  "60"
    domain.#:                                     "2"
    domain.1864502246.comment:                    ""
    domain.1864502246.name:                       "foo-www.externaldomain.com"
    domain.4243527184.comment:                    ""
    domain.4243527184.name:                       "foo.externaldomain.com"
    force_destroy:                                "true"
    gzip.#:                                       "1"
    gzip.2425354137.cache_condition:              ""
    gzip.2425354137.content_types.#:              "3"
    gzip.2425354137.content_types.2372034088:     "application/json"
    gzip.2425354137.content_types.366283795:      "text/css"
    gzip.2425354137.content_types.4008173114:     "text/html"
    gzip.2425354137.extensions.#:                 "2"
    gzip.2425354137.extensions.253252853:         "js"
    gzip.2425354137.extensions.3950613225:        "css"
    gzip.2425354137.name:                         "file extensions and content types"
    header.#:                                     "2"
    header.2180504608.action:                     "delete"
    header.2180504608.cache_condition:            ""
    header.2180504608.destination:                "http.X-Powered-By"
    header.2180504608.ignore_if_set:              "false"
    header.2180504608.name:                       "Remove X-Powered-By header"
    header.2180504608.priority:                   "100"
    header.2180504608.regex:                      "<computed>"
    header.2180504608.request_condition:          ""
    header.2180504608.response_condition:         ""
    header.2180504608.source:                     "<computed>"
    header.2180504608.substitution:               "<computed>"
    header.2180504608.type:                       "cache"
    header.3700817666.action:                     "set"
    header.3700817666.cache_condition:            ""
    header.3700817666.destination:                "http.Server"
    header.3700817666.ignore_if_set:              "false"
    header.3700817666.name:                       "Obfuscate Server header"
    header.3700817666.priority:                   "100"
    header.3700817666.regex:                      "<computed>"
    header.3700817666.request_condition:          ""
    header.3700817666.response_condition:         ""
    header.3700817666.source:                     "\\"LHC\\""
    header.3700817666.substitution:               "<computed>"
    header.3700817666.type:                       "cache"
    name:                                         "foo-externaldomain.com"
    request_setting.#:                            "1"
    request_setting.4061384956.action:            ""
    request_setting.4061384956.bypass_busy_wait:  ""
    request_setting.4061384956.default_host:      ""
    request_setting.4061384956.force_miss:        "false"
    request_setting.4061384956.force_ssl:         "true"
    request_setting.4061384956.geo_headers:       ""
    request_setting.4061384956.hash_keys:         ""
    request_setting.4061384956.max_stale_age:     "60"
    request_setting.4061384956.name:              "disable caching"
    request_setting.4061384956.request_condition: "all_urls"
    request_setting.4061384956.timer_support:     ""
    request_setting.4061384956.xff:               "append"
        """.strip() in output # noqa

    def test_create_fastly_config_disable_fastly_caching(self):
        # When
        output = check_output([
            'terraform',
            'plan',
            '-var', 'env=foo',
            '-var', 'component=foobar',
            '-var', 'team=foobar',
            '-var', 'aws_region=eu-west-1',
            '-var', 'fastly_domain=externaldomain.com',
            '-var', 'alb_domain=domain.com',
            '-var-file={}/test/platform-config/eu-west-1.json'.format(
                self.base_path
            ),
            '-no-color'
        ] + self._target_module('frontend_router_disable_fastly_caching') + [
            self.module_path
        ], env=self._env_for_check_output('qwerty'), cwd=self.workdir).decode(
            'utf-8'
        )

        # Then
        assert """
+ module.frontend_router_disable_fastly_caching.fastly.fastly_service_v1.fastly
        """.strip() in output # noqa

        assert """
    request_setting.#:                            "1"
    request_setting.2432135539.action:            ""
    request_setting.2432135539.bypass_busy_wait:  ""
    request_setting.2432135539.default_host:      ""
    request_setting.2432135539.force_miss:        "true"
    request_setting.2432135539.force_ssl:         "true"
    request_setting.2432135539.geo_headers:       ""
    request_setting.2432135539.hash_keys:         ""
    request_setting.2432135539.max_stale_age:     "60"
    request_setting.2432135539.name:              "disable caching"
    request_setting.2432135539.request_condition: "all_urls"
    request_setting.2432135539.timer_support:     ""
    request_setting.2432135539.xff:               "append"
        """.strip() in output # noqa

    @given(
        env=sampled_from(('ci', 'dev', 'aslive', 'live')),
        component=text(alphabet=ascii_lowercase, min_size=16, max_size=32)
    )
    def test_create_resources_when_long_component_names(self, env, component):
        # Given
        env_component_name = '{}-{}'.format(env, component)

        # When
        output = check_output([
            'terraform',
            'plan',
            '-var', 'env={}'.format(env),
            '-var', 'component={}'.format(component),
            '-var', 'team=foobar',
            '-var', 'aws_region=eu-west-1',
            '-var', 'fastly_domain=externaldomain.com',
            '-var', 'alb_domain=domain.com',
            '-var-file={}/test/platform-config/eu-west-1.json'.format(
                self.base_path
            ),
            '-no-color'
        ] + self._target_module('frontend_router') + [
            self.module_path
        ], env=self._env_for_check_output('qwerty'), cwd=self.workdir).decode(
            'utf-8'
        )

        # Then
        assert """
+ module.frontend_router.alb.aws_alb.alb
    arn:                        "<computed>"
    arn_suffix:                 "<computed>"
    dns_name:                   "<computed>"
    enable_deletion_protection: "false"
    idle_timeout:               "60"
    internal:                   "false"
    ip_address_type:            "<computed>"
    name:                       "{name}-router"
    security_groups.#:          "<computed>"
    subnets.#:                  "1"
    subnets.939944885:          "subnet-33333333,subnet-44444444,subnet-55555555"
    vpc_id:                     "<computed>"
    zone_id:                    "<computed>"
        """.format(name=env_component_name[:23]).strip() in output # noqa

        assert """
+ module.frontend_router.default_backend_ecs_service.aws_alb_target_group.target_group
    arn:                                "<computed>"
    arn_suffix:                         "<computed>"
    deregistration_delay:               "10"
    health_check.#:                     "1"
    health_check.0.healthy_threshold:   "2"
    health_check.0.interval:            "5"
    health_check.0.matcher:             "200-299"
    health_check.0.path:                "/internal/healthcheck"
    health_check.0.port:                "traffic-port"
    health_check.0.protocol:            "HTTP"
    health_check.0.timeout:             "4"
    health_check.0.unhealthy_threshold: "2"
    name:                               "{name}-default"
    port:                               "31337"
    protocol:                           "HTTP"
    stickiness.#:                       "<computed>"
    vpc_id:                             "vpc-12345678"
        """.format(name=env_component_name[:23]).strip() in output # noqa
