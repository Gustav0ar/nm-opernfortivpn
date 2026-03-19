# SPDX-License-Identifier: GPL-2.0-only
"""
Tests for config file generation and security.
"""
import os
import stat
import tempfile
import unittest
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'shared'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'service'))

from nm_openfortivpn_keys import (
    KEY_GATEWAY, KEY_PORT, KEY_USER, KEY_PASSWORD,
    KEY_SET_DNS, KEY_TRUSTED_CERT, KEY_REALM,
    VALID_DATA_KEYS, VALID_SECRET_KEYS, BOOL_KEYS, FILE_PATH_KEYS,
)
from nm_openfortivpn_service import (
    _validate_gateway, _validate_port, _validate_bool,
    _validate_file_path, _validate_trusted_cert, _validate_persistent,
    _validate_realm, _escape_config_value,
)


class TestValidateGateway(unittest.TestCase):
    def test_valid_hostname(self):
        self.assertTrue(_validate_gateway('vpn.example.com'))

    def test_valid_ip(self):
        self.assertTrue(_validate_gateway('192.168.1.1'))

    def test_valid_with_port(self):
        self.assertTrue(_validate_gateway('vpn.example.com:443'))

    def test_valid_ipv6_short(self):
        # Colons are allowed for IPv6
        self.assertTrue(_validate_gateway('::1'))

    def test_empty(self):
        self.assertFalse(_validate_gateway(''))

    def test_none(self):
        self.assertFalse(_validate_gateway(None))

    def test_shell_injection(self):
        self.assertFalse(_validate_gateway('vpn.example.com; rm -rf /'))

    def test_newline_injection(self):
        self.assertFalse(_validate_gateway('vpn.example.com\nmalicious'))

    def test_space_injection(self):
        self.assertFalse(_validate_gateway('vpn.example.com --extra-arg'))

    def test_backtick_injection(self):
        self.assertFalse(_validate_gateway('`whoami`.evil.com'))

    def test_dollar_injection(self):
        self.assertFalse(_validate_gateway('$(whoami).evil.com'))


class TestValidatePort(unittest.TestCase):
    def test_valid_port(self):
        self.assertTrue(_validate_port('443'))
        self.assertTrue(_validate_port('1'))
        self.assertTrue(_validate_port('65535'))

    def test_invalid_zero(self):
        self.assertFalse(_validate_port('0'))

    def test_invalid_too_high(self):
        self.assertFalse(_validate_port('65536'))

    def test_invalid_negative(self):
        self.assertFalse(_validate_port('-1'))

    def test_invalid_string(self):
        self.assertFalse(_validate_port('abc'))

    def test_none(self):
        self.assertFalse(_validate_port(None))


class TestValidateBool(unittest.TestCase):
    def test_valid(self):
        self.assertTrue(_validate_bool('0'))
        self.assertTrue(_validate_bool('1'))

    def test_invalid(self):
        self.assertFalse(_validate_bool('true'))
        self.assertFalse(_validate_bool('false'))
        self.assertFalse(_validate_bool('yes'))
        self.assertFalse(_validate_bool('2'))
        self.assertFalse(_validate_bool(''))


class TestValidateTrustedCert(unittest.TestCase):
    def test_valid_hex(self):
        self.assertTrue(_validate_trusted_cert('a' * 64))

    def test_valid_with_colons(self):
        cert = ':'.join('ab' for _ in range(32))
        self.assertTrue(_validate_trusted_cert(cert))

    def test_invalid_too_short(self):
        self.assertFalse(_validate_trusted_cert('abcdef'))

    def test_invalid_non_hex(self):
        self.assertFalse(_validate_trusted_cert('g' * 64))

    def test_invalid_none(self):
        self.assertFalse(_validate_trusted_cert(None))

    def test_invalid_empty(self):
        self.assertFalse(_validate_trusted_cert(''))


class TestValidatePersistent(unittest.TestCase):
    def test_valid(self):
        self.assertTrue(_validate_persistent('0'))
        self.assertTrue(_validate_persistent('30'))

    def test_invalid_negative(self):
        self.assertFalse(_validate_persistent('-1'))

    def test_invalid_string(self):
        self.assertFalse(_validate_persistent('abc'))


class TestValidateRealm(unittest.TestCase):
    def test_valid(self):
        self.assertTrue(_validate_realm('MyRealm'))
        self.assertTrue(_validate_realm('my-realm.example'))
        self.assertTrue(_validate_realm('realm_1'))

    def test_invalid_shell(self):
        self.assertFalse(_validate_realm('realm;rm -rf /'))

    def test_invalid_empty(self):
        self.assertFalse(_validate_realm(''))

    def test_invalid_space(self):
        self.assertFalse(_validate_realm('my realm'))


class TestEscapeConfigValue(unittest.TestCase):
    def test_normal(self):
        self.assertEqual(_escape_config_value('password123'), 'password123')

    def test_special_chars(self):
        self.assertEqual(_escape_config_value('p@ss=w0rd!'), 'p@ss=w0rd!')

    def test_newline_injection(self):
        result = _escape_config_value('password\nmalicious = yes')
        self.assertNotIn('\n', result)
        self.assertEqual(result, 'passwordmalicious = yes')

    def test_carriage_return_injection(self):
        result = _escape_config_value('password\rmalicious')
        self.assertNotIn('\r', result)

    def test_none(self):
        self.assertEqual(_escape_config_value(None), '')

    def test_non_string(self):
        self.assertEqual(_escape_config_value(123), '')


class TestValidateFilePath(unittest.TestCase):
    def test_valid_existing(self):
        # /etc/hosts should exist on all Linux
        self.assertTrue(_validate_file_path('/etc/hosts'))

    def test_invalid_relative(self):
        self.assertFalse(_validate_file_path('relative/path'))

    def test_invalid_null_byte(self):
        self.assertFalse(_validate_file_path('/etc/\x00hosts'))

    def test_invalid_nonexistent(self):
        self.assertFalse(_validate_file_path('/nonexistent/file.pem'))

    def test_invalid_empty(self):
        self.assertFalse(_validate_file_path(''))

    def test_invalid_none(self):
        self.assertFalse(_validate_file_path(None))


class TestKeyConstants(unittest.TestCase):
    """Verify consistency of key constants."""

    def test_bool_keys_in_valid_data(self):
        for key in BOOL_KEYS:
            self.assertIn(key, VALID_DATA_KEYS)

    def test_file_path_keys_in_valid_data(self):
        for key in FILE_PATH_KEYS:
            self.assertIn(key, VALID_DATA_KEYS)

    def test_no_overlap_data_secrets(self):
        self.assertEqual(len(VALID_DATA_KEYS & VALID_SECRET_KEYS), 0)


if __name__ == '__main__':
    unittest.main()
