# SPDX-License-Identifier: GPL-2.0-only
"""
NetworkManager VPN Service Plugin for openfortivpn.

Implements NM.VpnServicePlugin to manage openfortivpn connections.
Handles:
  - Secure config file generation (tmpfs, 0600, O_CREAT|O_EXCL)
  - openfortivpn subprocess lifecycle
  - Untrusted certificate detection from stderr
  - D-Bus PPP interface for IP config from pppd plugin
"""

import logging
import os
import re
import signal
import stat

import gi
gi.require_version('NM', '1.0')
gi.require_version('GLib', '2.0')
gi.require_version('Gio', '2.0')
from gi.repository import GLib, GObject, Gio, NM

# Allow running from source tree or installed
import sys
_shared = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'shared')
if os.path.isdir(_shared):
    sys.path.insert(0, _shared)

from nm_openfortivpn_keys import (
    NM_DBUS_SERVICE_OPENFORTIVPN,
    NM_DBUS_PATH_OPENFORTIVPN,
    NM_DBUS_INTERFACE_OPENFORTIVPN_PPP,
    KEY_GATEWAY, KEY_PORT, KEY_USER, KEY_PASSWORD, KEY_OTP,
    KEY_REALM, KEY_TRUSTED_CERT, KEY_CA_FILE, KEY_USER_CERT,
    KEY_USER_KEY, KEY_SET_DNS, KEY_PPPD_USE_PEERDNS,
    KEY_SET_ROUTES, KEY_HALF_INTERNET_ROUTES, KEY_PPPD_LOG,
    KEY_PERSISTENT, HINT_UNTRUSTED_CERT_HASH, HINT_UNTRUSTED_CERT_HOST,
    VALID_DATA_KEYS, VALID_SECRET_KEYS, BOOL_KEYS, FILE_PATH_KEYS,
)

log = logging.getLogger('nm-openfortivpn')

# Runtime directory for temp config files (tmpfs on most systems)
RUNTIME_DIR = '/run/nm-openfortivpn'

# Pattern to extract SHA256 cert hash from openfortivpn stderr
# SHA256 = 32 bytes = 64 hex chars, or 95 chars with colons (xx:xx:...)
# Match at least 64 hex chars (possibly colon-separated)
CERT_HASH_RE = re.compile(
    r'certificate\s+digest\s*(?:is\s*)?:?\s*([0-9a-fA-F:]{64,97})',
    re.IGNORECASE
)
# Also match the simpler format: "SHA256: <hex>"
CERT_HASH_RE2 = re.compile(
    r'SHA256\s*:\s*([0-9a-fA-F:]{64,97})',
    re.IGNORECASE
)
# Match the explicit suggestion format: "--trusted-cert <hex>"
CERT_HASH_RE3 = re.compile(
    r'--trusted-cert\s+([0-9a-fA-F:]{64,97})',
    re.IGNORECASE
)

# PPP D-Bus interface XML for GDBus
PPP_INTERFACE_XML = f'''
<node>
  <interface name="{NM_DBUS_INTERFACE_OPENFORTIVPN_PPP}">
    <method name="SetState">
      <arg type="u" name="state" direction="in"/>
    </method>
    <method name="SetIp4Config">
      <arg type="a{{sv}}" name="config" direction="in"/>
    </method>
  </interface>
</node>
'''


def _validate_gateway(value):
    """Validate gateway (hostname or IP). No path traversal or injection."""
    if not value or not isinstance(value, str):
        return False
    # Allow hostnames, IPs, must not contain shell-unsafe chars
    if re.match(r'^[a-zA-Z0-9._:-]+$', value):
        return True
    return False


def _validate_port(value):
    """Validate port number string."""
    try:
        port = int(value)
        return 1 <= port <= 65535
    except (ValueError, TypeError):
        return False


def _validate_bool(value):
    """Validate boolean string."""
    return value in ('0', '1')


def _validate_file_path(value):
    """Validate file path: must be absolute, no null bytes, must exist."""
    if not value or not isinstance(value, str):
        return False
    if '\x00' in value:
        return False
    if not os.path.isabs(value):
        return False
    # Resolve to prevent path traversal via symlinks
    try:
        resolved = os.path.realpath(value)
        return os.path.isfile(resolved)
    except OSError:
        return False


def _validate_trusted_cert(value):
    """Validate trusted cert SHA256 hash (hex with optional colons)."""
    if not value or not isinstance(value, str):
        return False
    # Strip colons and check it's a 64-char hex string (SHA256)
    clean = value.replace(':', '')
    return bool(re.match(r'^[0-9a-fA-F]{64}$', clean))


def _validate_persistent(value):
    """Validate persistent interval (non-negative integer)."""
    try:
        return int(value) >= 0
    except (ValueError, TypeError):
        return False


def _validate_realm(value):
    """Validate realm string — alphanumeric, dots, dashes, underscores."""
    if not value or not isinstance(value, str):
        return False
    return bool(re.match(r'^[a-zA-Z0-9._-]+$', value))


def _escape_config_value(value):
    """Escape a value for openfortivpn config file.

    The config file format is 'key = value'. Values can contain most
    characters but we need to ensure no newline injection.
    """
    if not isinstance(value, str):
        return ''
    # Remove any newlines or carriage returns to prevent injection
    return value.replace('\n', '').replace('\r', '')


class OpenfortivpnPlugin(NM.VpnServicePlugin):
    """NM VPN Service Plugin that manages openfortivpn connections."""

    def __init__(self):
        super().__init__(
            service_name=NM_DBUS_SERVICE_OPENFORTIVPN,
            watch_peer=False,
        )
        self.init(None)
        self._pid = 0
        self._watch_id = 0
        self._config_path = None
        self._connection = None
        self._interactive = False
        self._ppp_dbus_reg_id = 0
        self._stderr_buf = ''
        self._stderr_channel = None
        self._untrusted_cert_hash = None

        # Register PPP D-Bus interface
        self._setup_ppp_dbus()

        log.debug("Plugin initialized")

    def _setup_ppp_dbus(self):
        """Register D-Bus interface for PPP plugin communication."""
        try:
            introspect = Gio.DBusNodeInfo.new_for_xml(PPP_INTERFACE_XML)
            iface_info = introspect.interfaces[0]

            bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
            self._ppp_dbus_reg_id = bus.register_object(
                NM_DBUS_PATH_OPENFORTIVPN,
                iface_info,
                self._handle_ppp_method_call,
                None,
                None,
            )
            log.debug("PPP D-Bus interface registered at %s", NM_DBUS_PATH_OPENFORTIVPN)
        except Exception as e:
            log.error("Failed to register PPP D-Bus interface: %s", e)

    def _handle_ppp_method_call(self, connection, sender, object_path,
                                 interface_name, method_name, params,
                                 invocation):
        """Handle D-Bus method calls from the PPP plugin."""
        if method_name == 'SetState':
            state = params.unpack()[0]
            log.info("PPP state changed: %d", state)
            # NM_PPP_STATUS_DEAD=1, NM_PPP_STATUS_DISCONNECT=5
            if state in (1, 5):
                try:
                    self.disconnect()
                except GLib.Error:
                    pass
            invocation.return_value(None)

        elif method_name == 'SetIp4Config':
            config_variant = params.get_child_value(0)
            log.info("Received IP4 config from PPP plugin")
            self.set_ip4_config(config_variant)
            invocation.return_value(None)
        else:
            invocation.return_dbus_error(
                'org.freedesktop.DBus.Error.UnknownMethod',
                f'Unknown method: {method_name}'
            )

    def _ensure_runtime_dir(self):
        """Create runtime directory with secure permissions."""
        try:
            os.makedirs(RUNTIME_DIR, mode=0o700, exist_ok=True)
        except OSError as e:
            log.error("Failed to create runtime dir %s: %s", RUNTIME_DIR, e)
            raise

    def _write_config(self, s_vpn, username, password, otp=None, realm=None):
        """Write a temporary config file with secrets.

        Security:
          - Created in /run/ (tmpfs, not persisted to disk)
          - O_CREAT|O_EXCL for atomic creation (no race condition)
          - Mode 0600 (root-only read)
          - Values escaped to prevent newline injection
        """
        self._ensure_runtime_dir()

        conn_uuid = self._connection.get_uuid() if self._connection else 'unknown'
        # Sanitize UUID for filename
        safe_uuid = re.sub(r'[^a-zA-Z0-9-]', '_', conn_uuid)

        config_path = os.path.join(RUNTIME_DIR, f'{safe_uuid}.conf')

        lines = []
        if username:
            lines.append(f'username = {_escape_config_value(username)}')
        if password:
            lines.append(f'password = {_escape_config_value(password)}')
        if otp:
            lines.append(f'otp = {_escape_config_value(otp)}')
        if realm:
            lines.append(f'realm = {_escape_config_value(realm)}')

        config_data = '\n'.join(lines) + '\n'

        try:
            fd = os.open(
                config_path,
                os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
                stat.S_IRUSR | stat.S_IWUSR,  # 0600
            )
            try:
                os.write(fd, config_data.encode('utf-8'))
            finally:
                os.close(fd)
        except OSError as e:
            log.error("Failed to write config file: %s", e)
            raise

        self._config_path = config_path
        log.debug("Config written to %s", config_path)
        return config_path

    def _cleanup_config(self):
        """Remove temporary config file."""
        config_path = self._config_path
        if config_path:
            try:
                os.unlink(config_path)
                log.debug("Removed config %s", config_path)
            except OSError:
                pass
            self._config_path = None

    def _build_argv(self, s_vpn, config_path):
        """Build the openfortivpn command-line arguments.

        Passwords are in the config file, never on the command line.
        """
        argv = ['openfortivpn']

        # Gateway (host:port)
        gateway = s_vpn.get_data_item(KEY_GATEWAY)
        port = s_vpn.get_data_item(KEY_PORT)
        if gateway:
            if port and _validate_port(port):
                argv.append(f'{gateway}:{port}')
            else:
                argv.append(gateway)

        # Config file with secrets
        argv.extend(['-c', config_path])

        # Trusted certificate
        trusted = s_vpn.get_data_item(KEY_TRUSTED_CERT)
        if trusted and _validate_trusted_cert(trusted):
            argv.extend(['--trusted-cert', trusted])

        # Boolean options
        for key, flag in [
            (KEY_SET_DNS, '--set-dns'),
            (KEY_PPPD_USE_PEERDNS, '--pppd-use-peerdns'),
            (KEY_SET_ROUTES, '--set-routes'),
            (KEY_HALF_INTERNET_ROUTES, '--half-internet-routes'),
        ]:
            val = s_vpn.get_data_item(key)
            if val is not None and _validate_bool(val):
                argv.extend([flag, val])

        # File path options
        for key, flag in [
            (KEY_CA_FILE, '--ca-file'),
            (KEY_USER_CERT, '--user-cert'),
            (KEY_USER_KEY, '--user-key'),
            (KEY_PPPD_LOG, '--pppd-log'),
        ]:
            val = s_vpn.get_data_item(key)
            if val:
                # For pppd-log, don't require existence
                if key == KEY_PPPD_LOG:
                    if val and os.path.isabs(val) and '\x00' not in val:
                        argv.extend([flag, val])
                elif _validate_file_path(val):
                    argv.extend([flag, val])

        # Persistent
        persistent = s_vpn.get_data_item(KEY_PERSISTENT)
        if persistent is not None and _validate_persistent(persistent):
            argv.extend(['--persistent', persistent])

        # PPP plugin for IP config callback
        pppd_plugin = self._find_pppd_plugin()
        if pppd_plugin:
            argv.extend(['--pppd-plugin', pppd_plugin])

        # Verbose output for cert hash parsing
        argv.append('-v')

        return argv

    def _find_pppd_plugin(self):
        """Find the installed nm-openfortivpn-pppd-plugin.so."""
        candidates = [
            # Installed locations
            '/usr/lib/pppd/2.5.2/nm-openfortivpn-pppd-plugin.so',
            '/usr/lib/pppd/2.5.1/nm-openfortivpn-pppd-plugin.so',
            '/usr/lib/pppd/2.5.0/nm-openfortivpn-pppd-plugin.so',
            '/usr/lib/pppd/2.4.9/nm-openfortivpn-pppd-plugin.so',
            '/usr/lib64/pppd/2.5.2/nm-openfortivpn-pppd-plugin.so',
            # Build directory
            os.path.join(os.path.dirname(__file__), '..', '..', 'build',
                         'src', 'pppd-plugin', 'nm-openfortivpn-pppd-plugin.so'),
        ]
        for path in candidates:
            if os.path.isfile(path):
                return path
        log.warning("PPP plugin not found, IP configuration may not work")
        return None

    def _on_openfortivpn_stderr(self, channel, condition, *_data):
        """Read stderr from openfortivpn to detect cert errors."""
        if condition & GLib.IOCondition.HUP:
            self._check_cert_hash()
            self._stderr_channel = None
            return False

        try:
            data = channel.read()
            if data:
                text = data if isinstance(data, str) else data.decode('utf-8', errors='replace')
                self._stderr_buf += text
                # Log stderr lines
                for line in text.splitlines():
                    if line.strip():
                        log.debug("openfortivpn: %s", line.strip())
        except Exception as e:
            log.debug("stderr read error: %s", e)
            return False

        return True

    def _check_cert_hash(self):
        """Check if stderr contains an untrusted cert hash."""
        for pattern in (CERT_HASH_RE, CERT_HASH_RE2, CERT_HASH_RE3):
            match = pattern.search(self._stderr_buf)
            if match:
                self._untrusted_cert_hash = match.group(1).strip()
                log.info("Detected untrusted cert hash: %s", self._untrusted_cert_hash)
                return

    def _on_child_exit(self, pid, status, *_data):
        """Handle openfortivpn process exit."""
        self._watch_id = 0
        self._pid = 0

        exit_code = os.waitstatus_to_exitcode(status) if hasattr(os, 'waitstatus_to_exitcode') else (status >> 8)

        log.info("openfortivpn exited with code %d", exit_code)
        self._cleanup_config()

        if self._stderr_channel:
            # Read any remaining stderr
            try:
                remaining = self._stderr_channel.read()
                if remaining:
                    text = remaining if isinstance(remaining, str) else remaining.decode('utf-8', errors='replace')
                    self._stderr_buf += text
            except Exception:
                pass
            self._stderr_channel = None

        self._check_cert_hash()

        if exit_code != 0:
            if self._untrusted_cert_hash:
                # Signal that we need cert trust — NM will invoke auth-dialog
                log.info("Connection failed due to untrusted cert, requesting secrets")
                try:
                    self.secrets_required(
                        "VPN gateway certificate is not trusted",
                        [HINT_UNTRUSTED_CERT_HASH]
                    )
                except Exception as e:
                    log.error("Failed to request secrets: %s", e)
                    self.failure(NM.VpnPluginFailure.CONNECT_FAILED)
            else:
                self.failure(NM.VpnPluginFailure.CONNECT_FAILED)

    def do_connect(self, connection):
        """Start an openfortivpn connection."""
        log.info("Connect requested")
        self._interactive = False
        return self._start_connection(connection)

    def do_connect_interactive(self, connection, details):
        """Start an interactive openfortivpn connection."""
        log.info("Interactive connect requested")
        self._interactive = True
        return self._start_connection(connection)

    def _start_connection(self, connection):
        """Common connection logic."""
        self._cleanup()

        s_vpn = connection.get_setting_vpn()
        if not s_vpn:
            raise GLib.Error(
                message="Connection has no VPN setting",
                domain=GLib.quark_from_string("NM_VPN_PLUGIN_ERROR"),
                code=NM.VpnPluginError.INVALID_CONNECTION,
            )

        self._connection = connection
        self._stderr_buf = ''
        self._untrusted_cert_hash = None

        # Get credentials
        username = s_vpn.get_data_item(KEY_USER) or ''
        password = s_vpn.get_secret(KEY_PASSWORD) or ''
        otp = s_vpn.get_secret(KEY_OTP) or ''
        realm = s_vpn.get_data_item(KEY_REALM) or ''

        # Validate gateway
        gateway = s_vpn.get_data_item(KEY_GATEWAY)
        if not gateway or not _validate_gateway(gateway):
            raise GLib.Error(
                message="Missing or invalid VPN gateway",
                domain=GLib.quark_from_string("NM_VPN_PLUGIN_ERROR"),
                code=NM.VpnPluginError.INVALID_CONNECTION,
            )

        # Write secure config file
        config_path = self._write_config(
            s_vpn, username, password,
            otp=otp if otp else None,
            realm=realm if realm else None,
        )

        # Build command
        argv = self._build_argv(s_vpn, config_path)
        log.info("Starting: %s", ' '.join(
            a if a != config_path else '<config>' for a in argv
        ))

        # Spawn openfortivpn
        try:
            pid, _stdin, _stdout, stderr_fd = GLib.spawn_async(
                argv=argv,
                flags=(GLib.SpawnFlags.DO_NOT_REAP_CHILD |
                       GLib.SpawnFlags.SEARCH_PATH),
                standard_input=False,
                standard_output=False,
                standard_error=True,
            )
        except GLib.Error as e:
            self._cleanup_config()
            raise GLib.Error(
                message=f"Failed to start openfortivpn: {e.message}",
                domain=GLib.quark_from_string("NM_VPN_PLUGIN_ERROR"),
                code=NM.VpnPluginError.LAUNCH_FAILED,
            )

        self._pid = pid
        log.info("openfortivpn started (pid=%d)", pid)

        # Watch for process exit
        self._watch_id = GLib.child_watch_add(
            GLib.PRIORITY_DEFAULT, pid, self._on_child_exit
        )

        # Monitor stderr for cert hash
        if stderr_fd >= 0:
            channel = GLib.IOChannel.unix_new(stderr_fd)
            channel.set_flags(GLib.IOFlags.NONBLOCK)
            channel.set_close_on_unref(True)
            GLib.io_add_watch(
                channel,
                GLib.PRIORITY_DEFAULT,
                GLib.IOCondition.IN | GLib.IOCondition.HUP | GLib.IOCondition.ERR,
                self._on_openfortivpn_stderr,
            )
            self._stderr_channel = channel

        return True

    def do_need_secrets(self, connection):
        """Check if secrets are needed for this connection."""
        s_vpn = connection.get_setting_vpn()
        if not s_vpn:
            return NM.SETTING_VPN_SETTING_NAME

        # Check certificate-based auth (no password needed)
        user_cert = s_vpn.get_data_item(KEY_USER_CERT)
        if user_cert:
            return None  # Cert auth, no password needed

        # Check if password is available
        flags = NM.SettingSecretFlags.NONE
        try:
            _ok, flags = NM.Setting.get_secret_flags(s_vpn, KEY_PASSWORD)
        except Exception:
            pass

        if not (flags & NM.SettingSecretFlags.NOT_REQUIRED):
            password = s_vpn.get_secret(KEY_PASSWORD)
            if not password:
                return NM.SETTING_VPN_SETTING_NAME

        return None

    def do_disconnect(self):
        """Disconnect the VPN."""
        log.info("Disconnect requested")
        self._cleanup()
        return True

    def do_new_secrets(self, connection):
        """Handle new secrets (e.g., after cert trust)."""
        log.info("New secrets received")
        s_vpn = connection.get_setting_vpn()
        if not s_vpn:
            return False

        # Check if this is a cert trust response
        trusted_cert = s_vpn.get_secret(HINT_UNTRUSTED_CERT_HASH)
        if trusted_cert and _validate_trusted_cert(trusted_cert):
            log.info("User trusted cert: %s", trusted_cert)
            # The cert hash will be passed as trusted-cert on next connect
            # NM will retry the connection with the updated secrets

        self._connection = connection
        return True

    def _cleanup(self):
        """Kill subprocess and clean up resources."""
        if self._pid:
            log.info("Killing openfortivpn (pid=%d)", self._pid)
            try:
                os.kill(self._pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            # Give it a moment, then force kill
            GLib.timeout_add(2000, self._force_kill)

        if self._watch_id:
            GLib.source_remove(self._watch_id)
            self._watch_id = 0

        self._cleanup_config()
        self._connection = None
        self._stderr_buf = ''
        if self._stderr_channel:
            try:
                self._stderr_channel.shutdown(True)
            except GLib.Error:
                pass
            self._stderr_channel = None

    def _force_kill(self):
        """Force kill openfortivpn if still running."""
        if self._pid:
            try:
                os.kill(self._pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            self._pid = 0
        return False  # Don't repeat
