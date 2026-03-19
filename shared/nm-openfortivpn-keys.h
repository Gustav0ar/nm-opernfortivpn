/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef NM_OPENFORTIVPN_KEYS_H
#define NM_OPENFORTIVPN_KEYS_H

#define NM_DBUS_SERVICE_OPENFORTIVPN     "org.freedesktop.NetworkManager.openfortivpn"
#define NM_DBUS_PATH_OPENFORTIVPN        "/org/freedesktop/NetworkManager/openfortivpn"
#define NM_DBUS_INTERFACE_OPENFORTIVPN_PPP "org.freedesktop.NetworkManager.openfortivpn.ppp"

#define NM_OPENFORTIVPN_KEY_GATEWAY             "gateway"
#define NM_OPENFORTIVPN_KEY_PORT                "port"
#define NM_OPENFORTIVPN_KEY_USER                "user"
#define NM_OPENFORTIVPN_KEY_PASSWORD            "password"
#define NM_OPENFORTIVPN_KEY_OTP                 "otp"
#define NM_OPENFORTIVPN_KEY_REALM               "realm"
#define NM_OPENFORTIVPN_KEY_TRUSTED_CERT        "trusted-cert"
#define NM_OPENFORTIVPN_KEY_CA_FILE             "ca-file"
#define NM_OPENFORTIVPN_KEY_USER_CERT           "user-cert"
#define NM_OPENFORTIVPN_KEY_USER_KEY            "user-key"
#define NM_OPENFORTIVPN_KEY_SET_DNS             "set-dns"
#define NM_OPENFORTIVPN_KEY_PPPD_USE_PEERDNS    "pppd-use-peerdns"
#define NM_OPENFORTIVPN_KEY_SET_ROUTES          "set-routes"
#define NM_OPENFORTIVPN_KEY_HALF_INTERNET_ROUTES "half-internet-routes"
#define NM_OPENFORTIVPN_KEY_PPPD_LOG            "pppd-log"
#define NM_OPENFORTIVPN_KEY_PERSISTENT          "persistent"

/* Hints for cert trust workflow */
#define NM_OPENFORTIVPN_HINT_UNTRUSTED_CERT_HASH "untrusted-cert-hash"
#define NM_OPENFORTIVPN_HINT_UNTRUSTED_CERT_HOST "untrusted-cert-host"

#endif /* NM_OPENFORTIVPN_KEYS_H */
