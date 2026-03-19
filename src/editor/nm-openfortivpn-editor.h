/* SPDX-License-Identifier: GPL-2.0-only
 *
 * nm-openfortivpn-editor.h — NM VPN Editor Plugin for openfortivpn
 */

#ifndef NM_OPENFORTIVPN_EDITOR_H
#define NM_OPENFORTIVPN_EDITOR_H

#include <glib.h>
#include <NetworkManager.h>

#define NM_TYPE_OPENFORTIVPN_EDITOR_PLUGIN (openfortivpn_editor_plugin_get_type())

G_DECLARE_FINAL_TYPE(OpenfortivpnEditorPlugin, openfortivpn_editor_plugin,
                     NM, OPENFORTIVPN_EDITOR_PLUGIN, GObject)

NMVpnEditorPlugin *openfortivpn_editor_plugin_new(GError **error);

/* Factory function called by libnm */
G_MODULE_EXPORT NMVpnEditorPlugin *nm_vpn_editor_plugin_factory(GError **error);

#endif /* NM_OPENFORTIVPN_EDITOR_H */
