%global nm_version 1:1.2.0

Name:           nm-openfortivpn
Version:        1.0.0
Release:        1%{?dist}
Summary:        NetworkManager VPN plugin for openfortivpn
License:        GPL-2.0-only
URL:            https://github.com/Gustav0ar/nm-opernfortivpn
Source0:        %{name}-%{version}.tar.gz

BuildRequires:  meson
BuildRequires:  ninja-build
BuildRequires:  gcc
BuildRequires:  pkgconfig(libnm) >= 1.2.0
BuildRequires:  pkgconfig(gtk+-3.0)
BuildRequires:  pkgconfig(glib-2.0)
BuildRequires:  ppp-devel
BuildRequires:  python3

Requires:       NetworkManager >= %{nm_version}
Requires:       openfortivpn
Requires:       ppp
Requires:       python3
Requires:       python3-gobject
Requires:       gtk3
Requires:       gtk4

Recommends:     nm-connection-editor
Recommends:     gnome-keyring

%description
Provides NetworkManager integration for openfortivpn, an open-source
client for Fortinet SSL VPN (FortiGate).

Features include GUI and CLI connection management, secure password
storage, untrusted certificate detection, and full settings editor.

%prep
%autosetup

%build
%meson \
    -Dtests=false
%meson_build

%install
%meson_install

%files
%license LICENSE
%doc README.md
%{_libdir}/NetworkManager/VPN/nm-openfortivpn.name
%{_libdir}/NetworkManager/libnm-vpn-plugin-openfortivpn-editor.so
%{_libdir}/pppd/*/nm-openfortivpn-pppd-plugin.so
%{_libexecdir}/nm-openfortivpn-service
%{_libexecdir}/nm_openfortivpn_service.py
%{_libexecdir}/nm-openfortivpn-auth-dialog
%{_libexecdir}/shared/nm_openfortivpn_keys.py
%{_datadir}/dbus-1/system.d/nm-openfortivpn.conf
%{_datadir}/dbus-1/system-services/org.freedesktop.NetworkManager.openfortivpn.service

%changelog
* Tue Mar 17 2026 Your Name <your@email.com> - 1.0.0-1
- Initial release
