# SPDX-License-Identifier: GPL-2.0-only
# Shared constants for nm-openfortivpn

NM_DBUS_SERVICE_OPENFORTIVPN = "org.freedesktop.NetworkManager.openfortivpn"
NM_DBUS_PATH_OPENFORTIVPN = "/org/freedesktop/NetworkManager/openfortivpn"
NM_DBUS_INTERFACE_OPENFORTIVPN_PPP = "org.freedesktop.NetworkManager.openfortivpn.ppp"

NM_VPN_SERVICE_TYPE = "org.freedesktop.NetworkManager.openfortivpn"

# Connection data keys
KEY_GATEWAY = "gateway"
KEY_PORT = "port"
KEY_USER = "user"
KEY_REALM = "realm"
KEY_TRUSTED_CERT = "trusted-cert"
KEY_CA_FILE = "ca-file"
KEY_USER_CERT = "user-cert"
KEY_USER_KEY = "user-key"
KEY_SET_DNS = "set-dns"
KEY_PPPD_USE_PEERDNS = "pppd-use-peerdns"
KEY_SET_ROUTES = "set-routes"
KEY_HALF_INTERNET_ROUTES = "half-internet-routes"
KEY_PPPD_LOG = "pppd-log"
KEY_PERSISTENT = "persistent"

# Secret keys
KEY_PASSWORD = "password"
KEY_OTP = "otp"

# Hints for cert trust workflow
HINT_UNTRUSTED_CERT_HASH = "untrusted-cert-hash"
HINT_UNTRUSTED_CERT_HOST = "untrusted-cert-host"

# All valid data keys for validation
VALID_DATA_KEYS = frozenset({
    KEY_GATEWAY, KEY_PORT, KEY_USER, KEY_REALM,
    KEY_TRUSTED_CERT, KEY_CA_FILE, KEY_USER_CERT, KEY_USER_KEY,
    KEY_SET_DNS, KEY_PPPD_USE_PEERDNS, KEY_SET_ROUTES,
    KEY_HALF_INTERNET_ROUTES, KEY_PPPD_LOG, KEY_PERSISTENT,
})

VALID_SECRET_KEYS = frozenset({KEY_PASSWORD, KEY_OTP})

# Boolean data keys (accept "0" or "1" only)
BOOL_KEYS = frozenset({
    KEY_SET_DNS, KEY_PPPD_USE_PEERDNS,
    KEY_SET_ROUTES, KEY_HALF_INTERNET_ROUTES,
})

# File path data keys (must be absolute paths)
FILE_PATH_KEYS = frozenset({
    KEY_CA_FILE, KEY_USER_CERT, KEY_USER_KEY, KEY_PPPD_LOG,
})
