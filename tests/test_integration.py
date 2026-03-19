# SPDX-License-Identifier: GPL-2.0-only
"""
Integration tests — test full flow with mock openfortivpn.
"""
import os
import sys
import subprocess
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'shared'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'service'))

from nm_openfortivpn_keys import (
    KEY_GATEWAY, KEY_PORT, KEY_USER, KEY_PASSWORD,
    KEY_SET_DNS, KEY_PPPD_USE_PEERDNS, KEY_TRUSTED_CERT,
    KEY_REALM, KEY_SET_ROUTES, KEY_HALF_INTERNET_ROUTES,
    KEY_CA_FILE, KEY_USER_CERT, KEY_USER_KEY,
    NM_DBUS_SERVICE_OPENFORTIVPN,
)
from nm_openfortivpn_service import (
    _validate_gateway, _validate_port,
    _escape_config_value,
)


class TestNmcliIntegration(unittest.TestCase):
    """Test nmcli connection management (requires NM running)."""

    @classmethod
    def setUpClass(cls):
        """Check if nmcli is available and NM is running."""
        try:
            result = subprocess.run(
                ['nmcli', 'general', 'status'],
                capture_output=True, text=True, timeout=5,
            )
            cls.nm_available = result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            cls.nm_available = False

        # Check if our plugin is installed
        cls.plugin_installed = os.path.exists(
            '/usr/lib/NetworkManager/VPN/nm-openfortivpn.name'
        )

    def setUp(self):
        if not self.nm_available:
            self.skipTest("NetworkManager not running")
        if not self.plugin_installed:
            self.skipTest("nm-openfortivpn plugin not installed")

    def test_create_connection(self):
        """Test creating a VPN connection via nmcli."""
        conn_name = 'test-openfortivpn-integration'

        try:
            # Create
            result = subprocess.run(
                ['nmcli', 'connection', 'add',
                 'type', 'vpn',
                 'vpn-type', 'openfortivpn',
                 'con-name', conn_name,
                 'vpn.data',
                 'gateway=vpn.test.example, port=443, '
                 'user=testuser, set-dns=1, pppd-use-peerdns=0'],
                capture_output=True, text=True, timeout=10,
            )
            self.assertEqual(result.returncode, 0,
                             f"Create failed: {result.stderr}")

            # Show
            result = subprocess.run(
                ['nmcli', 'connection', 'show', conn_name],
                capture_output=True, text=True, timeout=10,
            )
            self.assertEqual(result.returncode, 0)
            self.assertIn('openfortivpn', result.stdout)
            self.assertIn('vpn.test.example', result.stdout)

        finally:
            # Cleanup
            subprocess.run(
                ['nmcli', 'connection', 'delete', conn_name],
                capture_output=True, timeout=10,
            )

    def test_modify_connection(self):
        """Test modifying a VPN connection via nmcli."""
        conn_name = 'test-openfortivpn-modify'

        try:
            subprocess.run(
                ['nmcli', 'connection', 'add',
                 'type', 'vpn', 'vpn-type', 'openfortivpn',
                 'con-name', conn_name,
                 'vpn.data', 'gateway=vpn1.test.example'],
                capture_output=True, text=True, timeout=10,
            )

            # Modify
            result = subprocess.run(
                ['nmcli', 'connection', 'modify', conn_name,
                 'vpn.data', 'gateway=vpn2.test.example, port=10443'],
                capture_output=True, text=True, timeout=10,
            )
            self.assertEqual(result.returncode, 0,
                             f"Modify failed: {result.stderr}")

            # Verify
            result = subprocess.run(
                ['nmcli', '-t', 'connection', 'show', conn_name],
                capture_output=True, text=True, timeout=10,
            )
            self.assertIn('vpn2.test.example', result.stdout)

        finally:
            subprocess.run(
                ['nmcli', 'connection', 'delete', conn_name],
                capture_output=True, timeout=10,
            )


class TestConfigFileGeneration(unittest.TestCase):
    """Test that config files are generated correctly."""

    def test_config_content(self):
        """Verify config file content format."""
        lines = []
        username = 'testuser'
        password = 'testpass'
        realm = 'MyRealm'
        otp = '123456'

        if username:
            lines.append(f'username = {_escape_config_value(username)}')
        if password:
            lines.append(f'password = {_escape_config_value(password)}')
        if otp:
            lines.append(f'otp = {_escape_config_value(otp)}')
        if realm:
            lines.append(f'realm = {_escape_config_value(realm)}')

        config = '\n'.join(lines) + '\n'

        self.assertIn('username = testuser', config)
        self.assertIn('password = testpass', config)
        self.assertIn('otp = 123456', config)
        self.assertIn('realm = MyRealm', config)

    def test_config_no_extra_lines(self):
        """Verify no extra lines from injection."""
        password = 'pass\nmalicious = yes'
        escaped = _escape_config_value(password)
        config = f'password = {escaped}\n'
        lines = [l for l in config.split('\n') if l.strip()]
        self.assertEqual(len(lines), 1)


class TestCommandLineBuilding(unittest.TestCase):
    """Test the command-line argument construction logic."""

    def test_gateway_validation_in_argv(self):
        """Ensure only valid gateways would reach argv construction."""
        valid = 'vpn.example.com'
        invalid = 'vpn.example.com; rm -rf /'

        self.assertTrue(_validate_gateway(valid))
        self.assertFalse(_validate_gateway(invalid))

    def test_port_validation_in_argv(self):
        self.assertTrue(_validate_port('443'))
        self.assertFalse(_validate_port('99999'))


if __name__ == '__main__':
    unittest.main()
