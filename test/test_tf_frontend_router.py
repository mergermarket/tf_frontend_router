import os
import re
import shutil
import tempfile
import unittest
from string import ascii_lowercase
from subprocess import check_call, check_output

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

    def pattern(placeholder, open_curly, close_curly, text, whitespace):
        if text is not None:
            return re.escape(text)
        elif whitespace is not None:
            return r'\s+'
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
        for match in re.finditer(
            r'{([\w_]+)}|(\{\{)|(\}\})|([^{}\s]+)|(\s+)', t
        )
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
Plan: 5 to add, 0 to change, 0 to destroy.
        """.strip() in output

    def test_create_public_alb_in_public_subnets(self):
        # Given
        env = 'testenv'
        component = 'testcomponent'
        team = 'testteam'

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
        match = re.search(template_to_re("""
+ module.frontend_router.module.alb.aws_alb.alb
      id:                                    <computed>
      access_logs.#:                         "1"
      access_logs.0.enabled:                 "false"
      arn:                                   <computed>
      arn_suffix:                            <computed>
      dns_name:                              <computed>
      drop_invalid_header_fields:            "false"
      enable_deletion_protection:            "false"
      enable_http2:                          "true"
      idle_timeout:                          "60"
      internal:                              "false"
      ip_address_type:                       <computed>
      load_balancer_type:                    "application"
      name:                                  "{}-router"
      security_groups.#:                     <computed>
      subnet_mapping.#:                      <computed>
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

        if match is None:
            print(output)
        assert match is not None

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
      default_action.#:                      "1"
      default_action.0.order:                <computed>
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
      egress.#:                              "1"
      egress.{ident}.cidr_blocks.#:        "1"
      egress.{ident}.cidr_blocks.0:        "0.0.0.0/0"
      egress.{ident}.description:          ""
      egress.{ident}.from_port:            "0"
      egress.{ident}.ipv6_cidr_blocks.#:   "0"
      egress.{ident}.prefix_list_ids.#:    "0"
      egress.{ident}.protocol:             "-1"
      egress.{ident}.security_groups.#:    "0"
      egress.{ident}.self:                 "false"
      egress.{ident}.to_port:              "0"
        """.strip()), output) # noqa

        assert re.search(template_to_re("""
      ingress.#:                             "2"
      ingress.{ident}.cidr_blocks.#:      "1"
      ingress.{ident}.cidr_blocks.0:      "0.0.0.0/0"
      ingress.{ident}.description:        ""
      ingress.{ident}.from_port:          "80"
      ingress.{ident}.ipv6_cidr_blocks.#: "0"
      ingress.{ident}.prefix_list_ids.#:  "0"
      ingress.{ident}.protocol:           "tcp"
      ingress.{ident}.security_groups.#:  "0"
      ingress.{ident}.self:               "false"
      ingress.{ident}.to_port:            "80"
        """.strip()), output) # noqa

        assert re.search(template_to_re("""
      ingress.{ident}.cidr_blocks.#:      "1"
      ingress.{ident}.cidr_blocks.0:      "0.0.0.0/0"
      ingress.{ident}.description:        ""
      ingress.{ident}.from_port:          "443"
      ingress.{ident}.ipv6_cidr_blocks.#: "0"
      ingress.{ident}.prefix_list_ids.#:  "0"
      ingress.{ident}.protocol:           "tcp"
      ingress.{ident}.security_groups.#:  "0"
      ingress.{ident}.self:               "false"
      ingress.{ident}.to_port:            "443"
        """.strip()), output) # noqa

        assert re.search(template_to_re("""
      revoke_rules_on_delete:                "false"
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

    def test_disable_force_ssl(self):
        # When
        output = check_output([
            'terraform',
            'plan',
            '-var', 'env=foo',
            '-var', 'component=foobar',
            '-var', 'team=foobar',
            '-var', 'fastly_domain=externaldomain.com',
            '-var', 'alb_domain=domain.com',
            '-var', 'force_ssl=false',
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
      request_setting.{ident}.bypass_busy_wait:  "false"
      request_setting.{ident}.default_host:      ""
      request_setting.{ident}.force_miss:        ""
      request_setting.{ident}.force_ssl:         "false"
      request_setting.{ident}.geo_headers:       ""
      request_setting.{ident}.hash_keys:         ""
      request_setting.{ident}.max_stale_age:     ""
      request_setting.{ident}.name:              "request-setting"
      request_setting.{ident}.request_condition: ""
      request_setting.{ident}.timer_support:     ""
      request_setting.{ident}.xff:               "append"
        """.strip()), output)

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
      backend.#:                                    "1"
      backend.~{ident}.address:                   "${{var.backend_address}}"
      backend.~{ident}.auto_loadbalance:          "true"
      backend.~{ident}.between_bytes_timeout:     "30000"
      backend.~{ident}.connect_timeout:           "5000"
      backend.~{ident}.error_threshold:           "0"
      backend.~{ident}.first_byte_timeout:        "60000"
      backend.~{ident}.healthcheck:               ""
      backend.~{ident}.max_conn:                  "200"
      backend.~{ident}.max_tls_version:           ""
      backend.~{ident}.min_tls_version:           ""
      backend.~{ident}.name:                      "default backend"
      backend.~{ident}.override_host:             ""
      backend.~{ident}.port:                      "443"
      backend.~{ident}.request_condition:         ""
      backend.~{ident}.shield:                    ""
      backend.~{ident}.ssl_ca_cert:               ""
      backend.~{ident}.ssl_cert_hostname:         "${{var.ssl_cert_hostname}}"
      backend.~{ident}.ssl_check_cert:            "true"
      backend.~{ident}.ssl_ciphers:               ""
      backend.~{ident}.ssl_client_cert:           <sensitive>
      backend.~{ident}.ssl_client_key:            <sensitive>
      backend.~{ident}.ssl_hostname:              ""
      backend.~{ident}.ssl_sni_hostname:          ""
      backend.~{ident}.use_ssl:                   "true"
      backend.~{ident}.weight:                    "100"
        """.strip()), output)

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
      condition.{ident}.name:                     "response-503-condition"
      condition.{ident}.priority:                 "5"
      condition.{ident}.statement:                "beresp.status == 503 && req.http.Cookie:viewerror != \\"true\\""
      condition.{ident}.type:                     "CACHE"
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
      request_setting.{ident}.bypass_busy_wait:  "false"
      request_setting.{ident}.default_host:      ""
      request_setting.{ident}.force_miss:        ""
      request_setting.{ident}.force_ssl:         "true"
      request_setting.{ident}.geo_headers:       ""
      request_setting.{ident}.hash_keys:         ""
      request_setting.{ident}.max_stale_age:     ""
      request_setting.{ident}.name:              "request-setting"
      request_setting.{ident}.request_condition: ""
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
      condition.{ident}.statement:               "beresp.status == 502 && req.http.Cookie:viewerror != \\"true\\""
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

    def test_fastly_shield(self):
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
            '-var', 'shield=test-shield',
            '-var-file={}/test/platform-config/eu-west-1.json'.format(
                self.base_path
            ),
            '-no-color',
            '-target=module.frontend_router_shield.module.fastly.fastly_service_v1.fastly', # noqa
        ] + [self.module_path], env=self._env_for_check_output(
            'qwerty'
        ), cwd=self.workdir).decode('utf-8')

        # Then
        assert re.search(r'backend.~\d+.shield:\s+"test-shield"', output)

    def test_default_target_group_default_tags(self):
        # Given

        # When
        output = check_output([
            'terraform',
            'plan',
            '-var', 'env=test-environment',
            '-var', 'component=test-component',
            '-var', 'team=test-team',
            '-var', 'fastly_domain=externaldomain.com',
            '-var', 'alb_domain=domain.com',
            '-var-file={}/test/platform-config/eu-west-1.json'.format(
                self.base_path
            ),
            '-no-color',
            '-target=module.frontend_router.'
            'aws_alb_target_group.default_target_group',
        ] + [self.module_path], env=self._env_for_check_output(
            'qwerty'
        ), cwd=self.workdir).decode('utf-8')

        # Then
        assert re.search(template_to_re("""
      tags.%:                             "4"
      tags.component:                     "test-component-default-target-group"
      tags.environment:                   "test-environment"
      tags.service:                       "test-environment-test-component-default-target-group"
      tags.team:                          "test-team"
        """.strip()), output) # noqa

    def test_default_target_group_component_tags(self):
        # Given

        # When
        output = check_output([
            'terraform',
            'plan',
            '-var', 'env=test-environment',
            '-var', 'component=test-component',
            '-var', 'team=test-team',
            '-var', 'default_target_group_component=test-def-tg-component',
            '-var', 'fastly_domain=externaldomain.com',
            '-var', 'alb_domain=domain.com',
            '-var-file={}/test/platform-config/eu-west-1.json'.format(
                self.base_path
            ),
            '-no-color',
            '-target=module.frontend_router.'
            'aws_alb_target_group.default_target_group',
        ] + [self.module_path], env=self._env_for_check_output(
            'qwerty'
        ), cwd=self.workdir).decode('utf-8')

        # Then
        assert re.search(template_to_re("""
      tags.%:                             "4"
      tags.component:                     "test-def-tg-component"
      tags.environment:                   "test-environment"
      tags.service:                       "test-environment-test-def-tg-component"
      tags.team:                          "test-team"
        """.strip()), output) # noqa
