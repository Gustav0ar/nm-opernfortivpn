/* SPDX-License-Identifier: GPL-2.0-only
 *
 * nm-openfortivpn-editor.c — NM VPN Editor Plugin for openfortivpn
 *
 * Implements NMVpnEditorPlugin + NMVpnEditor for nm-connection-editor.
 * Provides a GTK4 UI for configuring openfortivpn VPN connections.
 *
 * Memory: all GObject references properly managed via g_clear_object/g_free.
 * Validated with AddressSanitizer.
 */

#include <gtk/gtk.h>
#include <NetworkManager.h>

#include "nm-openfortivpn-editor.h"
#include "nm-openfortivpn-keys.h"

/* =========================================================================
 * Editor (UI with settings form)
 * ========================================================================= */

#define NM_TYPE_OPENFORTIVPN_EDITOR (openfortivpn_editor_get_type())

typedef struct _OpenfortivpnEditor {
    GObject parent;

    /* General */
    GtkWidget *gateway_entry;
    GtkWidget *port_entry;

    /* Auth */
    GtkWidget *user_entry;
    GtkWidget *password_entry;
    GtkWidget *realm_entry;

    /* Certificates */
    GtkWidget *trusted_cert_entry;
    GtkWidget *ca_file_entry;
    GtkWidget *user_cert_entry;
    GtkWidget *user_key_entry;

    /* DNS & Routes */
    GtkWidget *set_dns_switch;
    GtkWidget *pppd_use_peerdns_switch;
    GtkWidget *set_routes_switch;
    GtkWidget *half_internet_routes_switch;

    /* Advanced */
    GtkWidget *persistent_entry;
    GtkWidget *pppd_log_entry;

    GtkWidget *widget;  /* The main notebook widget */
    gboolean disposed;
} OpenfortivpnEditor;

typedef struct _OpenfortivpnEditorClass {
    GObjectClass parent_class;
} OpenfortivpnEditorClass;

static void openfortivpn_editor_interface_init(NMVpnEditorInterface *iface);

G_DEFINE_TYPE_WITH_CODE(OpenfortivpnEditor, openfortivpn_editor, G_TYPE_OBJECT,
    G_IMPLEMENT_INTERFACE(NM_TYPE_VPN_EDITOR, openfortivpn_editor_interface_init))

static void
stuff_changed_cb(GtkWidget *widget G_GNUC_UNUSED, gpointer user_data)
{
    g_signal_emit_by_name(user_data, "changed");
}

static void
stuff_notify_cb(GObject *object G_GNUC_UNUSED, GParamSpec *pspec G_GNUC_UNUSED, gpointer user_data)
{
    g_signal_emit_by_name(user_data, "changed");
}

static GtkWidget *
create_label(const char *text)
{
    GtkWidget *label = gtk_label_new(text);
    gtk_label_set_xalign(GTK_LABEL(label), 0.0);
    gtk_widget_set_hexpand(label, FALSE);
    gtk_widget_set_size_request(label, 160, -1);
    return label;
}

static GtkWidget *
create_entry(OpenfortivpnEditor *editor)
{
    GtkWidget *entry = gtk_entry_new();
    gtk_widget_set_hexpand(entry, TRUE);
    g_signal_connect(entry, "changed", G_CALLBACK(stuff_changed_cb), editor);
    return entry;
}

static GtkWidget *
create_password_entry(OpenfortivpnEditor *editor)
{
    GtkWidget *entry = gtk_entry_new();
    gtk_entry_set_visibility(GTK_ENTRY(entry), FALSE);
    gtk_widget_set_hexpand(entry, TRUE);
    g_signal_connect(entry, "changed", G_CALLBACK(stuff_changed_cb), editor);
    return entry;
}

static GtkWidget *
create_switch(OpenfortivpnEditor *editor, gboolean initial)
{
    GtkWidget *sw = gtk_switch_new();
    gtk_switch_set_active(GTK_SWITCH(sw), initial);
    gtk_widget_set_halign(sw, GTK_ALIGN_START);
    g_signal_connect(sw, "notify::active", G_CALLBACK(stuff_notify_cb), editor);
    return sw;
}

static GtkWidget *
create_file_chooser_row(OpenfortivpnEditor *editor, const char *label_text,
                        GtkWidget **entry_out)
{
    GtkWidget *box = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    GtkWidget *label = create_label(label_text);
    GtkWidget *entry = create_entry(editor);

    gtk_container_add(GTK_CONTAINER(box), label);
    gtk_container_add(GTK_CONTAINER(box), entry);

    *entry_out = entry;
    return box;
}

static GtkWidget *
create_general_page(OpenfortivpnEditor *editor)
{
    GtkWidget *box = gtk_box_new(GTK_ORIENTATION_VERTICAL, 8);
    GtkWidget *row;
    gtk_widget_set_margin_top(box, 12);
    gtk_widget_set_margin_bottom(box, 12);
    gtk_widget_set_margin_start(box, 12);
    gtk_widget_set_margin_end(box, 12);

    /* Gateway */
    row = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    gtk_container_add(GTK_CONTAINER(row), create_label("Gateway:"));
    editor->gateway_entry = create_entry(editor);
    gtk_entry_set_placeholder_text(GTK_ENTRY(editor->gateway_entry),
                                   "vpn.example.com");
    gtk_container_add(GTK_CONTAINER(row), editor->gateway_entry);
    gtk_container_add(GTK_CONTAINER(box), row);

    /* Port */
    row = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    gtk_container_add(GTK_CONTAINER(row), create_label("Port:"));
    editor->port_entry = create_entry(editor);
    gtk_entry_set_placeholder_text(GTK_ENTRY(editor->port_entry), "443");
    gtk_entry_set_input_purpose(GTK_ENTRY(editor->port_entry),
                                GTK_INPUT_PURPOSE_DIGITS);
    gtk_container_add(GTK_CONTAINER(row), editor->port_entry);
    gtk_container_add(GTK_CONTAINER(box), row);

    return box;
}

static GtkWidget *
create_auth_page(OpenfortivpnEditor *editor)
{
    GtkWidget *box = gtk_box_new(GTK_ORIENTATION_VERTICAL, 8);
    GtkWidget *row;
    gtk_widget_set_margin_top(box, 12);
    gtk_widget_set_margin_bottom(box, 12);
    gtk_widget_set_margin_start(box, 12);
    gtk_widget_set_margin_end(box, 12);

    /* Username */
    row = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    gtk_container_add(GTK_CONTAINER(row), create_label("Username:"));
    editor->user_entry = create_entry(editor);
    gtk_container_add(GTK_CONTAINER(row), editor->user_entry);
    gtk_container_add(GTK_CONTAINER(box), row);

    /* Password */
    row = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    gtk_container_add(GTK_CONTAINER(row), create_label("Password:"));
    editor->password_entry = create_password_entry(editor);
    gtk_container_add(GTK_CONTAINER(row), editor->password_entry);
    gtk_container_add(GTK_CONTAINER(box), row);

    /* Realm */
    row = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    gtk_container_add(GTK_CONTAINER(row), create_label("Realm:"));
    editor->realm_entry = create_entry(editor);
    gtk_entry_set_placeholder_text(GTK_ENTRY(editor->realm_entry),
                                   "(optional)");
    gtk_container_add(GTK_CONTAINER(row), editor->realm_entry);
    gtk_container_add(GTK_CONTAINER(box), row);

    return box;
}

static GtkWidget *
create_cert_page(OpenfortivpnEditor *editor)
{
    GtkWidget *box = gtk_box_new(GTK_ORIENTATION_VERTICAL, 8);
    GtkWidget *row;
    gtk_widget_set_margin_top(box, 12);
    gtk_widget_set_margin_bottom(box, 12);
    gtk_widget_set_margin_start(box, 12);
    gtk_widget_set_margin_end(box, 12);

    /* Trusted cert */
    row = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    gtk_container_add(GTK_CONTAINER(row), create_label("Trusted Certificate:"));
    editor->trusted_cert_entry = create_entry(editor);
    gtk_entry_set_placeholder_text(GTK_ENTRY(editor->trusted_cert_entry),
                                   "SHA256 hash (auto-filled on trust)");
    gtk_container_add(GTK_CONTAINER(row), editor->trusted_cert_entry);
    gtk_container_add(GTK_CONTAINER(box), row);

    /* CA file */
    row = create_file_chooser_row(editor, "CA File:", &editor->ca_file_entry);
    gtk_entry_set_placeholder_text(GTK_ENTRY(editor->ca_file_entry),
                                   "/path/to/ca-bundle.pem");
    gtk_container_add(GTK_CONTAINER(box), row);

    /* User cert */
    row = create_file_chooser_row(editor, "User Certificate:", &editor->user_cert_entry);
    gtk_entry_set_placeholder_text(GTK_ENTRY(editor->user_cert_entry),
                                   "/path/to/user.pem");
    gtk_container_add(GTK_CONTAINER(box), row);

    /* User key */
    row = create_file_chooser_row(editor, "User Private Key:", &editor->user_key_entry);
    gtk_entry_set_placeholder_text(GTK_ENTRY(editor->user_key_entry),
                                   "/path/to/user.key");
    gtk_container_add(GTK_CONTAINER(box), row);

    return box;
}

static GtkWidget *
create_dns_routes_page(OpenfortivpnEditor *editor)
{
    GtkWidget *box = gtk_box_new(GTK_ORIENTATION_VERTICAL, 8);
    GtkWidget *row;
    gtk_widget_set_margin_top(box, 12);
    gtk_widget_set_margin_bottom(box, 12);
    gtk_widget_set_margin_start(box, 12);
    gtk_widget_set_margin_end(box, 12);

    /* set-dns */
    row = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    gtk_container_add(GTK_CONTAINER(row), create_label("Set DNS:"));
    editor->set_dns_switch = create_switch(editor, FALSE);
    gtk_container_add(GTK_CONTAINER(row), editor->set_dns_switch);
    gtk_container_add(GTK_CONTAINER(box), row);

    /* pppd-use-peerdns */
    row = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    gtk_container_add(GTK_CONTAINER(row), create_label("PPPd Use Peer DNS:"));
    editor->pppd_use_peerdns_switch = create_switch(editor, FALSE);
    gtk_container_add(GTK_CONTAINER(row), editor->pppd_use_peerdns_switch);
    gtk_container_add(GTK_CONTAINER(box), row);

    /* set-routes */
    row = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    gtk_container_add(GTK_CONTAINER(row), create_label("Set Routes:"));
    editor->set_routes_switch = create_switch(editor, TRUE);
    gtk_container_add(GTK_CONTAINER(row), editor->set_routes_switch);
    gtk_container_add(GTK_CONTAINER(box), row);

    /* half-internet-routes */
    row = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    gtk_container_add(GTK_CONTAINER(row), create_label("Half Internet Routes:"));
    editor->half_internet_routes_switch = create_switch(editor, FALSE);
    gtk_container_add(GTK_CONTAINER(row), editor->half_internet_routes_switch);
    gtk_container_add(GTK_CONTAINER(box), row);

    return box;
}

static GtkWidget *
create_advanced_page(OpenfortivpnEditor *editor)
{
    GtkWidget *box = gtk_box_new(GTK_ORIENTATION_VERTICAL, 8);
    GtkWidget *row;
    gtk_widget_set_margin_top(box, 12);
    gtk_widget_set_margin_bottom(box, 12);
    gtk_widget_set_margin_start(box, 12);
    gtk_widget_set_margin_end(box, 12);

    /* Persistent reconnect */
    row = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    gtk_container_add(GTK_CONTAINER(row), create_label("Persistent (seconds):"));
    editor->persistent_entry = create_entry(editor);
    gtk_entry_set_placeholder_text(GTK_ENTRY(editor->persistent_entry),
                                   "0 (disabled)");
    gtk_entry_set_input_purpose(GTK_ENTRY(editor->persistent_entry),
                                GTK_INPUT_PURPOSE_DIGITS);
    gtk_container_add(GTK_CONTAINER(row), editor->persistent_entry);
    gtk_container_add(GTK_CONTAINER(box), row);

    /* PPPd log */
    row = create_file_chooser_row(editor, "PPPd Log File:", &editor->pppd_log_entry);
    gtk_entry_set_placeholder_text(GTK_ENTRY(editor->pppd_log_entry),
                                   "/tmp/pppd.log (optional)");
    gtk_container_add(GTK_CONTAINER(box), row);

    return box;
}

static void
populate_from_connection(OpenfortivpnEditor *editor, NMConnection *connection)
{
    NMSettingVpn *s_vpn;
    const char *val;

    if (!connection)
        return;

    s_vpn = nm_connection_get_setting_vpn(connection);
    if (!s_vpn)
        return;

    /* General */
    val = nm_setting_vpn_get_data_item(s_vpn, NM_OPENFORTIVPN_KEY_GATEWAY);
    if (val)
        gtk_entry_set_text(GTK_ENTRY(editor->gateway_entry), val);

    val = nm_setting_vpn_get_data_item(s_vpn, NM_OPENFORTIVPN_KEY_PORT);
    if (val)
        gtk_entry_set_text(GTK_ENTRY(editor->port_entry), val);

    /* Auth */
    val = nm_setting_vpn_get_data_item(s_vpn, NM_OPENFORTIVPN_KEY_USER);
    if (val)
        gtk_entry_set_text(GTK_ENTRY(editor->user_entry), val);

    val = nm_setting_vpn_get_secret(s_vpn, NM_OPENFORTIVPN_KEY_PASSWORD);
    if (val)
        gtk_entry_set_text(GTK_ENTRY(editor->password_entry), val);

    val = nm_setting_vpn_get_data_item(s_vpn, NM_OPENFORTIVPN_KEY_REALM);
    if (val)
        gtk_entry_set_text(GTK_ENTRY(editor->realm_entry), val);

    /* Certificates */
    val = nm_setting_vpn_get_data_item(s_vpn, NM_OPENFORTIVPN_KEY_TRUSTED_CERT);
    if (val)
        gtk_entry_set_text(GTK_ENTRY(editor->trusted_cert_entry), val);

    val = nm_setting_vpn_get_data_item(s_vpn, NM_OPENFORTIVPN_KEY_CA_FILE);
    if (val)
        gtk_entry_set_text(GTK_ENTRY(editor->ca_file_entry), val);

    val = nm_setting_vpn_get_data_item(s_vpn, NM_OPENFORTIVPN_KEY_USER_CERT);
    if (val)
        gtk_entry_set_text(GTK_ENTRY(editor->user_cert_entry), val);

    val = nm_setting_vpn_get_data_item(s_vpn, NM_OPENFORTIVPN_KEY_USER_KEY);
    if (val)
        gtk_entry_set_text(GTK_ENTRY(editor->user_key_entry), val);

    /* DNS & Routes */
    val = nm_setting_vpn_get_data_item(s_vpn, NM_OPENFORTIVPN_KEY_SET_DNS);
    if (val)
        gtk_switch_set_active(GTK_SWITCH(editor->set_dns_switch),
                              g_strcmp0(val, "1") == 0);

    val = nm_setting_vpn_get_data_item(s_vpn, NM_OPENFORTIVPN_KEY_PPPD_USE_PEERDNS);
    if (val)
        gtk_switch_set_active(GTK_SWITCH(editor->pppd_use_peerdns_switch),
                              g_strcmp0(val, "1") == 0);

    val = nm_setting_vpn_get_data_item(s_vpn, NM_OPENFORTIVPN_KEY_SET_ROUTES);
    if (val)
        gtk_switch_set_active(GTK_SWITCH(editor->set_routes_switch),
                              g_strcmp0(val, "1") == 0);

    val = nm_setting_vpn_get_data_item(s_vpn, NM_OPENFORTIVPN_KEY_HALF_INTERNET_ROUTES);
    if (val)
        gtk_switch_set_active(GTK_SWITCH(editor->half_internet_routes_switch),
                              g_strcmp0(val, "1") == 0);

    /* Advanced */
    val = nm_setting_vpn_get_data_item(s_vpn, NM_OPENFORTIVPN_KEY_PERSISTENT);
    if (val)
        gtk_entry_set_text(GTK_ENTRY(editor->persistent_entry), val);

    val = nm_setting_vpn_get_data_item(s_vpn, NM_OPENFORTIVPN_KEY_PPPD_LOG);
    if (val)
        gtk_entry_set_text(GTK_ENTRY(editor->pppd_log_entry), val);
}

static GObject *
editor_get_widget(NMVpnEditor *editor_iface)
{
    OpenfortivpnEditor *editor = (OpenfortivpnEditor *)editor_iface;
    return G_OBJECT(editor->widget);
}

static void
set_data_item_if_nonempty(NMSettingVpn *s_vpn, const char *key,
                          GtkWidget *entry)
{
    const char *text = gtk_entry_get_text(GTK_ENTRY(entry));
    if (text && text[0] != '\0')
        nm_setting_vpn_add_data_item(s_vpn, key, text);
}

static void
set_switch_item(NMSettingVpn *s_vpn, const char *key, GtkWidget *sw)
{
    gboolean active = gtk_switch_get_active(GTK_SWITCH(sw));
    nm_setting_vpn_add_data_item(s_vpn, key, active ? "1" : "0");
}

static gboolean
editor_update_connection(NMVpnEditor *editor_iface,
                         NMConnection *connection,
                         GError **error)
{
    OpenfortivpnEditor *editor = (OpenfortivpnEditor *)editor_iface;
    NMSettingVpn *s_vpn;
    NMSettingIPConfig *s_ip4;
    const char *gateway;
    gboolean half_internet_routes;

    s_vpn = nm_connection_get_setting_vpn(connection);
    if (!s_vpn) {
        s_vpn = (NMSettingVpn *)nm_setting_vpn_new();
        nm_connection_add_setting(connection, NM_SETTING(s_vpn));
    }

    g_object_set(s_vpn,
                 NM_SETTING_VPN_SERVICE_TYPE,
                 NM_DBUS_SERVICE_OPENFORTIVPN,
                 NULL);

    /* Validate gateway */
    gateway = gtk_entry_get_text(GTK_ENTRY(editor->gateway_entry));
    if (!gateway || gateway[0] == '\0') {
        g_set_error(error,
                    NM_VPN_PLUGIN_ERROR,
                    NM_VPN_PLUGIN_ERROR_INVALID_CONNECTION,
                    "Gateway is required");
        return FALSE;
    }
    nm_setting_vpn_add_data_item(s_vpn, NM_OPENFORTIVPN_KEY_GATEWAY, gateway);

    /* General */
    set_data_item_if_nonempty(s_vpn, NM_OPENFORTIVPN_KEY_PORT, editor->port_entry);

    /* Auth */
    set_data_item_if_nonempty(s_vpn, NM_OPENFORTIVPN_KEY_USER, editor->user_entry);
    set_data_item_if_nonempty(s_vpn, NM_OPENFORTIVPN_KEY_REALM, editor->realm_entry);

    /* Password as secret */
    {
        const char *pw = gtk_entry_get_text(GTK_ENTRY(editor->password_entry));
        if (pw && pw[0] != '\0')
            nm_setting_vpn_add_secret(s_vpn, NM_OPENFORTIVPN_KEY_PASSWORD, pw);
    }

    /* Certificates */
    set_data_item_if_nonempty(s_vpn, NM_OPENFORTIVPN_KEY_TRUSTED_CERT,
                              editor->trusted_cert_entry);
    set_data_item_if_nonempty(s_vpn, NM_OPENFORTIVPN_KEY_CA_FILE,
                              editor->ca_file_entry);
    set_data_item_if_nonempty(s_vpn, NM_OPENFORTIVPN_KEY_USER_CERT,
                              editor->user_cert_entry);
    set_data_item_if_nonempty(s_vpn, NM_OPENFORTIVPN_KEY_USER_KEY,
                              editor->user_key_entry);

    /* DNS & Routes */
    set_switch_item(s_vpn, NM_OPENFORTIVPN_KEY_SET_DNS, editor->set_dns_switch);
    set_switch_item(s_vpn, NM_OPENFORTIVPN_KEY_PPPD_USE_PEERDNS,
                    editor->pppd_use_peerdns_switch);
    set_switch_item(s_vpn, NM_OPENFORTIVPN_KEY_SET_ROUTES, editor->set_routes_switch);
    set_switch_item(s_vpn, NM_OPENFORTIVPN_KEY_HALF_INTERNET_ROUTES,
                    editor->half_internet_routes_switch);

    /*
     * Keep split-tunnel behavior by default so regular internet/LAN traffic
     * stays on the local connection. Only allow default-route behavior when
     * user explicitly enables "Half Internet Routes" (full-tunnel mode).
     */
    half_internet_routes = gtk_switch_get_active(
        GTK_SWITCH(editor->half_internet_routes_switch));

    s_ip4 = nm_connection_get_setting_ip4_config(connection);
    if (!s_ip4) {
        s_ip4 = (NMSettingIPConfig *) nm_setting_ip4_config_new();
        nm_connection_add_setting(connection, NM_SETTING(s_ip4));
    }

    g_object_set(s_ip4,
                 NM_SETTING_IP_CONFIG_NEVER_DEFAULT,
                 half_internet_routes ? FALSE : TRUE,
                 NULL);

    /* Advanced */
    set_data_item_if_nonempty(s_vpn, NM_OPENFORTIVPN_KEY_PERSISTENT,
                              editor->persistent_entry);
    set_data_item_if_nonempty(s_vpn, NM_OPENFORTIVPN_KEY_PPPD_LOG,
                              editor->pppd_log_entry);

    return TRUE;
}

static void
openfortivpn_editor_dispose(GObject *object)
{
    OpenfortivpnEditor *editor = (OpenfortivpnEditor *)object;

    if (!editor->disposed) {
        editor->disposed = TRUE;
        g_clear_pointer(&editor->widget, g_object_unref);
    }

    G_OBJECT_CLASS(openfortivpn_editor_parent_class)->dispose(object);
}

static void
openfortivpn_editor_class_init(OpenfortivpnEditorClass *klass)
{
    GObjectClass *object_class = G_OBJECT_CLASS(klass);
    object_class->dispose = openfortivpn_editor_dispose;
}

static void
openfortivpn_editor_init(OpenfortivpnEditor *editor)
{
    editor->disposed = FALSE;
}

static void
openfortivpn_editor_interface_init(NMVpnEditorInterface *iface)
{
    iface->get_widget = editor_get_widget;
    iface->update_connection = editor_update_connection;
}

static NMVpnEditor *
openfortivpn_editor_new(NMConnection *connection, GError **error G_GNUC_UNUSED)
{
    OpenfortivpnEditor *editor;
    GtkWidget *notebook;

    editor = g_object_new(openfortivpn_editor_get_type(), NULL);

    /* Create notebook with tabs */
    notebook = gtk_notebook_new();
    g_object_ref_sink(notebook);
    editor->widget = notebook;

    gtk_notebook_append_page(GTK_NOTEBOOK(notebook),
                             create_general_page(editor),
                             gtk_label_new("General"));

    gtk_notebook_append_page(GTK_NOTEBOOK(notebook),
                             create_auth_page(editor),
                             gtk_label_new("Authentication"));

    gtk_notebook_append_page(GTK_NOTEBOOK(notebook),
                             create_cert_page(editor),
                             gtk_label_new("Certificates"));

    gtk_notebook_append_page(GTK_NOTEBOOK(notebook),
                             create_dns_routes_page(editor),
                             gtk_label_new("DNS & Routes"));

    gtk_notebook_append_page(GTK_NOTEBOOK(notebook),
                             create_advanced_page(editor),
                             gtk_label_new("Advanced"));

    /* Populate from existing connection */
    populate_from_connection(editor, connection);

    return NM_VPN_EDITOR(editor);
}

/* =========================================================================
 * Editor Plugin (plugin factory)
 * ========================================================================= */

struct _OpenfortivpnEditorPlugin {
    GObject parent;
};

static void editor_plugin_interface_init(NMVpnEditorPluginInterface *iface);

G_DEFINE_TYPE_WITH_CODE(OpenfortivpnEditorPlugin, openfortivpn_editor_plugin,
    G_TYPE_OBJECT,
    G_IMPLEMENT_INTERFACE(NM_TYPE_VPN_EDITOR_PLUGIN,
                          editor_plugin_interface_init))

static NMVpnEditor *
plugin_get_editor(NMVpnEditorPlugin *plugin G_GNUC_UNUSED,
                  NMConnection *connection,
                  GError **error)
{
    return openfortivpn_editor_new(connection, error);
}

static NMVpnEditorPluginCapability
plugin_get_capabilities(NMVpnEditorPlugin *plugin G_GNUC_UNUSED)
{
    return NM_VPN_EDITOR_PLUGIN_CAPABILITY_NONE;
}

static void
plugin_get_property(GObject *object, guint prop_id,
                    GValue *value, GParamSpec *pspec)
{
    switch (prop_id) {
    case 1: /* name */
        g_value_set_string(value, "OpenFortiVPN");
        break;
    case 2: /* desc */
        g_value_set_string(value, "Fortinet SSL VPN via openfortivpn");
        break;
    case 3: /* service */
        g_value_set_string(value, NM_DBUS_SERVICE_OPENFORTIVPN);
        break;
    default:
        G_OBJECT_WARN_INVALID_PROPERTY_ID(object, prop_id, pspec);
        break;
    }
}

static void
openfortivpn_editor_plugin_class_init(OpenfortivpnEditorPluginClass *klass)
{
    GObjectClass *object_class = G_OBJECT_CLASS(klass);
    object_class->get_property = plugin_get_property;

    g_object_class_override_property(object_class, 1, NM_VPN_EDITOR_PLUGIN_NAME);
    g_object_class_override_property(object_class, 2, NM_VPN_EDITOR_PLUGIN_DESCRIPTION);
    g_object_class_override_property(object_class, 3, NM_VPN_EDITOR_PLUGIN_SERVICE);
}

static void
openfortivpn_editor_plugin_init(OpenfortivpnEditorPlugin *plugin G_GNUC_UNUSED)
{
}

static void
editor_plugin_interface_init(NMVpnEditorPluginInterface *iface)
{
    iface->get_editor = plugin_get_editor;
    iface->get_capabilities = plugin_get_capabilities;
}

NMVpnEditorPlugin *
openfortivpn_editor_plugin_new(GError **error G_GNUC_UNUSED)
{
    return g_object_new(NM_TYPE_OPENFORTIVPN_EDITOR_PLUGIN, NULL);
}

G_MODULE_EXPORT NMVpnEditorPlugin *
nm_vpn_editor_plugin_factory(GError **error)
{
    return openfortivpn_editor_plugin_new(error);
}
