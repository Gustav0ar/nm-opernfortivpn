# SPDX-License-Identifier: GPL-2.0-only
"""
Security-focused tests for nm-openfortivpn.
"""
import os
import stat
import tempfile
import unittest
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'shared'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'service'))

from nm_openfortivpn_service import (
    _validate_gateway, _validate_port, _validate_file_path,
    _validate_trusted_cert, _validate_realm, _escape_config_value,
    RUNTIME_DIR,
)


class TestNoCommandInjection(unittest.TestCase):
    """Verify that user input cannot lead to command injection."""

    INJECTION_PAYLOADS = [
        '; rm -rf /',
        '| cat /etc/shadow',
        '$(whoami)',
        '`id`',
        '\n--extra-arg',
        "'; DROP TABLE--",
        '&& curl evil.com',
        '> /etc/crontab',
        '\x00null_byte',
        '../../etc/passwd',
    ]

    def test_gateway_rejects_injection(self):
        for payload in self.INJECTION_PAYLOADS:
            self.assertFalse(
                _validate_gateway(payload),
                f"Gateway should reject: {payload!r}"
            )

    def test_realm_rejects_injection(self):
        for payload in self.INJECTION_PAYLOADS:
            self.assertFalse(
                _validate_realm(payload),
                f"Realm should reject: {payload!r}"
            )

    def test_cert_rejects_injection(self):
        for payload in self.INJECTION_PAYLOADS:
            self.assertFalse(
                _validate_trusted_cert(payload),
                f"Trusted cert should reject: {payload!r}"
            )


class TestConfigFileInjection(unittest.TestCase):
    """Verify config file injection prevention."""

    def test_newline_injection_in_password(self):
        """A password with newlines should not create extra config lines."""
        result = _escape_config_value("mypass\nmalicious_key = evil_value")
        self.assertNotIn('\n', result)
        self.assertEqual(result, "mypassmalicious_key = evil_value")

    def test_cr_injection_in_password(self):
        result = _escape_config_value("mypass\rmalicious")
        self.assertNotIn('\r', result)

    def test_crlf_injection(self):
        result = _escape_config_value("mypass\r\nmalicious = yes")
        self.assertNotIn('\r', result)
        self.assertNotIn('\n', result)


class TestFilePathSecurity(unittest.TestCase):
    """Verify file path validation security."""

    def test_rejects_path_traversal(self):
        """Relative paths that could traverse are rejected."""
        self.assertFalse(_validate_file_path('../../../etc/shadow'))

    def test_rejects_null_byte(self):
        self.assertFalse(_validate_file_path('/etc/\x00shadow'))

    def test_rejects_relative(self):
        self.assertFalse(_validate_file_path('relative/cert.pem'))

    def test_rejects_empty(self):
        self.assertFalse(_validate_file_path(''))


class TestRuntimeDirectory(unittest.TestCase):
    """Verify RUNTIME_DIR is on tmpfs."""

    def test_runtime_dir_on_run(self):
        """Config files should be in /run (tmpfs)."""
        self.assertTrue(RUNTIME_DIR.startswith('/run/'),
                        f"RUNTIME_DIR should be under /run, got: {RUNTIME_DIR}")


if __name__ == '__main__':
    unittest.main()
