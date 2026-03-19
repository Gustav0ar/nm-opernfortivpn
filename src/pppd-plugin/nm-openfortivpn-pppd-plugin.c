/* SPDX-License-Identifier: GPL-2.0-only
 *
 * nm-openfortivpn-pppd-plugin.c — pppd plugin for nm-openfortivpn
 *
 * Loaded by pppd when openfortivpn uses --pppd-plugin.
 * Sends IP4 configuration back to the NM service daemon via D-Bus
 * once the PPP link is established.
 *
 * Compatible with pppd 2.5.x API.
 * Memory safety: all GLib/D-Bus objects properly unreffed in cleanup.
 */

#include <arpa/inet.h>
#include <sys/types.h>

#ifndef __u_char_defined
typedef unsigned char u_char;
typedef unsigned short u_short;
#endif

#if __has_include(<pppd/pppdconf.h>)
#include <pppd/pppdconf.h>
#define NM_PPPD_HAS_25_API 1
#else
#include <pppd/patchlevel.h>
#define PPPD_VERSION VERSION
#define NM_PPPD_HAS_25_API 0
#endif

#include <pppd/pppd.h>
#include <pppd/fsm.h>
#include <pppd/ipcp.h>

#include <gio/gio.h>

#include "nm-openfortivpn-keys.h"

/* pppd plugin API version */
char pppd_version[] = PPPD_VERSION;

static GDBusConnection *dbus_conn = NULL;

static void
plugin_cleanup(void)
{
    g_clear_object(&dbus_conn);
}

static GDBusConnection *
get_bus(void)
{
    GError *err = NULL;

    if (!dbus_conn) {
        dbus_conn = g_bus_get_sync(G_BUS_TYPE_SYSTEM, NULL, &err);
        if (!dbus_conn) {
            error("nm-openfortivpn-pppd: D-Bus connect failed: %s",
                  err ? err->message : "unknown");
            g_clear_error(&err);
        }
    }
    return dbus_conn;
}

static GVariant *
build_ip4_config(void)
{
    GVariantBuilder builder;

    g_variant_builder_init(&builder, G_VARIANT_TYPE("a{sv}"));

    /* Tunnel device name */
#if NM_PPPD_HAS_25_API
    const char *dev = ppp_ifname();
#else
    const char *dev = ifname;
#endif
    if (dev && dev[0] != '\0') {
        g_variant_builder_add(&builder, "{sv}",
                              "tundev",
                              g_variant_new_string(dev));
    }

    /* Local IP address */
    if (ipcp_gotoptions[0].ouraddr != 0) {
        g_variant_builder_add(&builder, "{sv}",
                              "address",
                              g_variant_new_uint32(ipcp_gotoptions[0].ouraddr));
    }

    /* Peer/gateway IP */
    if (ipcp_hisoptions[0].hisaddr != 0) {
        g_variant_builder_add(&builder, "{sv}",
                              "gateway",
                              g_variant_new_uint32(ipcp_hisoptions[0].hisaddr));
    }

    /* Netmask — pppd point-to-point, typically /32 */
    g_variant_builder_add(&builder, "{sv}",
                          "prefix",
                          g_variant_new_uint32(32));

    /* DNS servers (from peer if available) */
    if (ipcp_gotoptions[0].dnsaddr[0] != 0) {
        GVariantBuilder dns_builder;
        g_variant_builder_init(&dns_builder, G_VARIANT_TYPE("au"));
        g_variant_builder_add(&dns_builder, "u",
                              ipcp_gotoptions[0].dnsaddr[0]);
        if (ipcp_gotoptions[0].dnsaddr[1] != 0) {
            g_variant_builder_add(&dns_builder, "u",
                                  ipcp_gotoptions[0].dnsaddr[1]);
        }
        g_variant_builder_add(&builder, "{sv}",
                              "dns",
                              g_variant_builder_end(&dns_builder));
    }

    /* MTU */
#if NM_PPPD_HAS_25_API
    int mtu = ppp_get_mtu(0);
#else
    int mtu = netif_get_mtu(0);
#endif
    if (mtu > 0) {
        g_variant_builder_add(&builder, "{sv}",
                              "mtu",
                              g_variant_new_uint32((guint32)mtu));
    }

    return g_variant_builder_end(&builder);
}

static void
nm_send_ip4_config(void)
{
    GDBusConnection *bus = get_bus();
    GError *err = NULL;
    GVariant *config;

    if (!bus)
        return;

    config = build_ip4_config();

    g_dbus_connection_call_sync(
        bus,
        NM_DBUS_SERVICE_OPENFORTIVPN,
        NM_DBUS_PATH_OPENFORTIVPN,
        NM_DBUS_INTERFACE_OPENFORTIVPN_PPP,
        "SetIp4Config",
        g_variant_new("(@a{sv})", config),
        NULL,
        G_DBUS_CALL_FLAGS_NONE,
        -1,
        NULL,
        &err
    );

    if (err) {
        warn("nm-openfortivpn-pppd: SetIp4Config failed: %s", err->message);
        g_error_free(err);
    } else {
        notice("nm-openfortivpn-pppd: IP4 config sent");
    }
}

static void
nm_send_state(guint32 state)
{
    GDBusConnection *bus = get_bus();
    GError *err = NULL;

    if (!bus)
        return;

    g_dbus_connection_call_sync(
        bus,
        NM_DBUS_SERVICE_OPENFORTIVPN,
        NM_DBUS_PATH_OPENFORTIVPN,
        NM_DBUS_INTERFACE_OPENFORTIVPN_PPP,
        "SetState",
        g_variant_new("(u)", state),
        NULL,
        G_DBUS_CALL_FLAGS_NONE,
        -1,
        NULL,
        &err
    );

    if (err) {
        warn("nm-openfortivpn-pppd: SetState failed: %s", err->message);
        g_error_free(err);
    }
}

static void
nm_ip_up_cb(void *opaque, int arg)
{
    (void)opaque;
    (void)arg;
    notice("nm-openfortivpn-pppd: ip-up");
    nm_send_ip4_config();
}

static void
nm_ip_down_cb(void *opaque, int arg)
{
    (void)opaque;
    (void)arg;
    notice("nm-openfortivpn-pppd: ip-down");
    nm_send_state(1); /* NM_PPP_STATUS_DEAD */
    plugin_cleanup();
}

static void
nm_exit_cb(void *opaque, int arg)
{
    (void)opaque;
    (void)arg;
    plugin_cleanup();
}

void
plugin_init(void)
{
    notice("nm-openfortivpn-pppd: init");
#if NM_PPPD_HAS_25_API
    ppp_add_notify(NF_IP_UP, nm_ip_up_cb, NULL);
    ppp_add_notify(NF_IP_DOWN, nm_ip_down_cb, NULL);
    ppp_add_notify(NF_EXIT, nm_exit_cb, NULL);
#else
    add_notifier(&ip_up_notifier, nm_ip_up_cb, NULL);
    add_notifier(&ip_down_notifier, nm_ip_down_cb, NULL);
    add_notifier(&exitnotify, nm_exit_cb, NULL);
#endif
}
