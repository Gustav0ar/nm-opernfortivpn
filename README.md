# nm-openfortivpn

**NetworkManager VPN plugin for openfortivpn** — connect to Fortinet SSL VPN (FortiGate) via NetworkManager.

## Features

- **GUI & CLI management** — works with `nmcli`, `nmtui`, and `nm-connection-editor`
- **Cross-desktop** — editor plugin uses GTK3 and auth dialog uses GTK4
- **Secure credentials** — passwords stored via NM secret agent (GNOME Keyring / KWallet)
- **Certificate trust** — detects untrusted certs and offers to trust them via UI dialog
- **Full settings** — gateway, port, realm, DNS, routes, persistent mode, certificates, and more
- **Editor plugin** — native settings UI in nm-connection-editor with tabs for all options

## Building

### Dependencies

| Package | Arch | Debian/Ubuntu | Fedora |
|---|---|---|---|
| NetworkManager | `networkmanager` | `network-manager` | `NetworkManager` |
| libnm (dev) | `libnm` | `libnm-dev` | `pkgconfig(libnm)` |
| GTK3 (dev) | `gtk3` | `libgtk-3-dev` | `pkgconfig(gtk3)` |
| GTK4 (runtime, auth dialog) | `gtk4` | `gir1.2-gtk-4.0` | `gtk4` |
| pppd (dev) | `ppp` | `ppp-dev` | `ppp-devel` |
| Python 3 | `python` | `python3` | `python3` |
| PyGObject | `python-gobject` | `python3-gi` | `python3-gobject` |
| openfortivpn | `openfortivpn` | `openfortivpn` | `openfortivpn` |
| Meson | `meson` | `meson` | `meson` |

### Install dependencies

#### Arch

```bash
sudo pacman -S --needed networkmanager libnm gtk3 gtk4 ppp python python-gobject openfortivpn meson ninja
```

#### Debian / Ubuntu

```bash
sudo apt-get update
sudo apt-get install -y \
  build-essential meson ninja-build pkg-config \
  libnm-dev libgtk-3-dev libglib2.0-dev ppp-dev \
  python3 python3-gi gir1.2-gtk-4.0 \
  network-manager openfortivpn ppp
```

#### Fedora

```bash
sudo dnf install -y \
  meson ninja-build gcc make pkgconf-pkg-config \
  NetworkManager-libnm-devel gtk3-devel glib2-devel ppp-devel \
  python3 python3-gobject gtk4 \
  NetworkManager openfortivpn ppp
```

### Build from source

These steps are the same on any distro once dependencies are installed.

```bash
meson setup build
meson compile -C build
sudo meson install -C build
sudo systemctl restart NetworkManager
```

If you want a system-wide install under `/usr` (instead of Meson's default `/usr/local`):

```bash
meson setup build --prefix=/usr --libdir=lib --libexecdir=lib
meson compile -C build
sudo meson install -C build
sudo systemctl restart NetworkManager
```

### Uninstall & clean build

If you installed from source with Meson/Ninja, uninstall with:

```bash
sudo ninja -C build uninstall
sudo systemctl restart NetworkManager
```

To force a fully clean rebuild from source:

```bash
rm -rf build
meson setup build
meson compile -C build
sudo meson install -C build
sudo systemctl restart NetworkManager
```

### Build packages

Packaging targets and support policy:
- **Arch Linux**: latest rolling release
- **Debian**: latest stable + current LTS
- **Ubuntu**: latest interim + current LTS
- **Fedora**: latest release + previous supported release

The packaging files under `packaging/` were validated with real builds on these reference versions:
- Arch (`makepkg`)
- Debian 12 (`dpkg-buildpackage`)
- Ubuntu 24.04 LTS (`dpkg-buildpackage`)
- Fedora 44 (`rpmbuild`)

If package names differ slightly between distro versions, install equivalent dependencies and use the same commands below.

## CI/CD and release process

- CI runs on every Pull Request to `master` and on every push to `master` (including merged PRs).
- Release pipeline runs on tags matching `v*` (for example `v1.0.0`).
- Release pipeline runs tests first, then builds and publishes:
  - source archive (`.tar.gz`)
  - Debian package (`.deb`)
  - RPM package (`.rpm`)

### Recommended deployment flow (best practice)

1. Merge to `master` only after CI is green.
  - Enable branch protection on `master` and require the CI workflow checks before merge.
2. Create an annotated semantic version tag:

```bash
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0
```

3. GitHub Actions will build, test, and publish artifacts to the GitHub Release automatically.

This tag-driven flow is the standard industry approach because releases are immutable, auditable, and reproducible from a specific commit.

#### Arch Linux (`PKGBUILD`)

```bash
cd packaging
makepkg -si
```

#### Debian / Ubuntu (`debian/`)

From the project root:

```bash
cp -a packaging/debian debian
dpkg-buildpackage -us -uc -b
```

#### Fedora (`.spec`)

From the project root:

```bash
mkdir -p ~/rpmbuild/SOURCES ~/rpmbuild/SPECS
tar -czf ~/rpmbuild/SOURCES/nm-openfortivpn-1.0.0.tar.gz \
  --transform 's,^,nm-openfortivpn-1.0.0/,' .
cp packaging/nm-openfortivpn.spec ~/rpmbuild/SPECS/
rpmbuild -ba ~/rpmbuild/SPECS/nm-openfortivpn.spec
```

## Usage

### CLI (nmcli)

```bash
# Create a VPN connection
nmcli connection add type vpn vpn-type openfortivpn \
  con-name "My FortiVPN" \
  vpn.data "gateway=vpn.example.com, port=443, user=myuser, set-dns=1, pppd-use-peerdns=0"

# Set password (stored in keyring)
nmcli connection modify "My FortiVPN" vpn.secrets password=mypassword

# Connect
nmcli connection up "My FortiVPN"

# Disconnect
nmcli connection down "My FortiVPN"

# Show connection details
nmcli connection show "My FortiVPN"
```

### GUI

Open **nm-connection-editor** or **GNOME Settings → Network → VPN → +** and select "OpenFortiVPN".

After installation, if the plugin does not appear immediately:

```bash
sudo systemctl restart NetworkManager
```

### Available Settings

| Setting | nmcli data key | Description |
|---|---|---|
| Gateway | `gateway` | VPN server hostname or IP |
| Port | `port` | VPN server port (default: 443) |
| Username | `user` | VPN account username |
| Realm | `realm` | Authentication realm |
| Trusted Cert | `trusted-cert` | SHA256 hash of trusted gateway cert |
| CA File | `ca-file` | Path to CA certificate bundle |
| User Cert | `user-cert` | Path to user certificate |
| User Key | `user-key` | Path to user private key |
| Set DNS | `set-dns` | Use VPN DNS servers (0/1) |
| PPPd Peer DNS | `pppd-use-peerdns` | Let pppd set DNS (0/1) |
| Set Routes | `set-routes` | Configure VPN routes (0/1) |
| Half Routes | `half-internet-routes` | Use /1 routes instead of default (0/1) |
| Persistent | `persistent` | Reconnect interval in seconds (0=off) |
| PPPd Log | `pppd-log` | Path for pppd debug log |

## Certificate Trust

When connecting to a server with an untrusted certificate, the plugin will:

1. Detect the certificate validation failure
2. Parse the SHA256 fingerprint from openfortivpn output
3. Show a GTK3 dialog with the fingerprint for user verification
4. If accepted, save the hash as `trusted-cert` in the connection

## Testing

```bash
# Run unit tests
python3 -m pytest tests/ -v

# Run tests via meson
meson test -C build

# Build with AddressSanitizer (C components)
meson setup build-asan -Db_sanitize=address,undefined
meson test -C build-asan
```

## License

GPL-2.0-only
