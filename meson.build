# SPDX-License-Identifier: GPL-2.0-only
project('nm-openfortivpn', 'c',
  version: '1.0.0',
  license: 'GPL-2.0-only',
  meson_version: '>= 0.56',
  default_options: [
    'c_std=c11',
    'warning_level=2',
  ],
)

# Dependencies
libnm_dep = dependency('libnm', version: '>= 1.2.0')
gio_dep = dependency('gio-2.0')
gtk3_dep = dependency('gtk+-3.0', version: '>= 3.0')
glib_dep = dependency('glib-2.0')

# pppd
pppd_dep = dependency('pppd', required: false)
if not pppd_dep.found()
  # Fallback: manual pppd detection
  cc = meson.get_compiler('c')
  pppd_dep = declare_dependency(
    include_directories: include_directories('/usr/include'),
  )
endif

# Install directories
prefix = get_option('prefix')
libdir = get_option('libdir')
libexecdir = join_paths(prefix, get_option('libexecdir'))
datadir = join_paths(prefix, get_option('datadir'))
sysconfdir = get_option('sysconfdir')

nm_vpndir = join_paths(prefix, libdir, 'NetworkManager', 'VPN')
nm_plugindir = join_paths(prefix, libdir, 'NetworkManager')
pppd_plugindir_opt = get_option('pppd_plugin_dir')
if pppd_plugindir_opt != ''
  pppd_plugindir = pppd_plugindir_opt
else
  fs = import('fs')
  pppd_version = '2.5.2'
  pppd_version_detected = false
  pppd_prog = find_program('pppd', required: false)
  if pppd_prog.found()
    pppd_version_cmd = run_command(pppd_prog, '--version', check: false)
    if pppd_version_cmd.returncode() == 0
      pppd_version_line = pppd_version_cmd.stdout().strip()
      if pppd_version_line != ''
        pppd_version_parts = pppd_version_line.split()
        if pppd_version_parts.length() > 0
          pppd_version = pppd_version_parts[-1]
          pppd_version_detected = true
        endif
      endif
    endif
  endif

  if not pppd_version_detected
    pppdconf_header = '/usr/include/pppd/pppdconf.h'
    patchlevel_header = '/usr/include/pppd/patchlevel.h'
    if fs.exists(pppdconf_header)
      pppd_version_cmd = run_command('sh', '-c', 'awk -F\" "/^#define PPPD_VERSION/{print \$2}" ' + pppdconf_header, check: false)
      if pppd_version_cmd.returncode() == 0 and pppd_version_cmd.stdout().strip() != ''
        pppd_version = pppd_version_cmd.stdout().strip()
        pppd_version_detected = true
      endif
    endif

    if not pppd_version_detected and fs.exists(patchlevel_header)
      pppd_version_cmd = run_command('sh', '-c', 'awk -F\" "/^#define VERSION/{print \$2}" ' + patchlevel_header, check: false)
      if pppd_version_cmd.returncode() == 0 and pppd_version_cmd.stdout().strip() != ''
        pppd_version = pppd_version_cmd.stdout().strip()
      endif
    endif
  endif

  pppd_plugindir = join_paths(prefix, libdir, 'pppd', pppd_version)
  if libdir.contains('/')
    pppd_plugindir = join_paths(prefix, 'lib', 'pppd', pppd_version)
  endif

  pppd_plugindir_candidates = [
    pppd_plugindir,
    join_paths(prefix, 'lib', 'pppd', pppd_version),
    join_paths(prefix, 'lib64', 'pppd', pppd_version),
  ]

  foreach candidate : pppd_plugindir_candidates
    if fs.exists(candidate)
      pppd_plugindir = candidate
      break
    endif
  endforeach
endif
dbus_confdir = join_paths(datadir, 'dbus-1', 'system.d')
dbus_svcdir = join_paths(datadir, 'dbus-1', 'system-services')

conf_data = configuration_data()
conf_data.set('LIBEXECDIR', libexecdir)
conf_data.set('PLUGINDIR', nm_plugindir)
conf_data.set('VERSION', meson.project_version())

# Shared include path
shared_inc = include_directories('shared')

# ---- PPP Plugin (C shared library) ----
pppd_plugin = shared_library('nm-openfortivpn-pppd-plugin',
  'src/pppd-plugin/nm-openfortivpn-pppd-plugin.c',
  include_directories: shared_inc,
  dependencies: [gio_dep, pppd_dep],
  install: true,
  install_dir: pppd_plugindir,
  name_prefix: '',  # no 'lib' prefix
  override_options: ['b_lundef=false'],
)

# ---- Editor Plugin (C shared library for nm-connection-editor) ----
editor_plugin = shared_library('nm-vpn-plugin-openfortivpn-editor',
  'src/editor/nm-openfortivpn-editor.c',
  include_directories: shared_inc,
  dependencies: [libnm_dep, gtk3_dep, glib_dep],
  install: true,
  install_dir: nm_plugindir,
)

# ---- Install Python service daemon ----
install_data(
  'src/service/nm-openfortivpn-service',
  install_dir: libexecdir,
  install_mode: 'rwxr-xr-x',
)
install_data(
  'src/service/nm_openfortivpn_service.py',
  install_dir: libexecdir,
)

# ---- Install Python auth dialog ----
install_data(
  'src/auth-dialog/nm-openfortivpn-auth-dialog',
  install_dir: libexecdir,
  install_mode: 'rwxr-xr-x',
)

# ---- Install shared Python module ----
install_data(
  'shared/nm_openfortivpn_keys.py',
  install_dir: join_paths(libexecdir, 'shared'),
)

# ---- Install NM VPN plugin descriptor ----
configure_file(
  input: 'data/nm-openfortivpn.name.in',
  output: 'nm-openfortivpn.name',
  configuration: conf_data,
  install: true,
  install_dir: nm_vpndir,
)

# ---- Install D-Bus config ----
install_data(
  'data/nm-openfortivpn.conf',
  install_dir: dbus_confdir,
)

# ---- Install D-Bus activation service ----
configure_file(
  input: 'data/org.freedesktop.NetworkManager.openfortivpn.service.in',
  output: 'org.freedesktop.NetworkManager.openfortivpn.service',
  configuration: conf_data,
  install: true,
  install_dir: dbus_svcdir,
)

# ---- Tests ----
if get_option('tests')
  subdir('tests')
endif

# Summary
summary({
  'prefix': prefix,
  'libexecdir': libexecdir,
  'NM VPN dir': nm_vpndir,
  'NM plugin dir': nm_plugindir,
  'pppd plugin dir': pppd_plugindir,
}, section: 'Directories')
