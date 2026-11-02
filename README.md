# Synaxe Debian packages

The archive is served by the **debian** Dockge stack on maccha at
<https://debian.at.synaxe.org/>. The landing page provides the public bootstrap
package and a copy-paste installation command. Private packages require the
private bootstrap and a per-host credential. The public page's short command
downloads `/install.sh` to `synaxe-install.sh`, then runs it only after curl
succeeds. Inspect the script before execution if desired. It downloads the
bootstrap package, verifies its generated SHA-256 checksum, and uses root or
sudo for installation and `apt update`. It does not pipe a live download into
a shell; first-install trust still rests on HTTPS and the independently
verifiable signing fingerprint.

## Sources and builds

- `bootstrap/`: public key/source bootstrap and optional private authentication
  package. The committed key is public; the signing secret stays on maccha.
- `recipes/dahua-rpc-api/debian/`: packaging overlay for upstream v0.1.5.
- `recipes/freebox-cli/debian/`: overlay for KevinGallaccio/freebox-cli v0.8.1
  (commit `89d1aed`), providing `fbx`, not a separately developed Freebox client.
- Our own tools keep `debian/` in their own repositories; Stern stays private.
- `../packages`: shared base metapackage generated from `packages/base`.
- Old versioned package directories are historical and are not built.

Build a source tree containing `debian/`:

```sh
sh build.sh bootstrap dist
sh build.sh ../stern-mirror dist
sh build.sh ../packages dist
```

The build image declares its dependencies in the Dockerfile. Builds run in
disposable containers, run package tests and Lintian, and retain `.deb`,
`.changes` and `.buildinfo` in the ignored `dist/` directory. No installation
or service activation happens on the build host.

For Dahua, check out upstream v0.1.5, overlay `recipes/dahua-rpc-api/debian/`
as `debian/`, then build that tree. Its build version is set explicitly to
avoid guessing a different version from shallow Git history.

For Freebox, check out upstream v0.8.1 and overlay
`recipes/freebox-cli/debian/` as `debian/`. The package includes the core CLI
and TUI. Optional MCP support is excluded because its dependency is not
available in Debian forky; only its optional test module is excluded from
the upstream test run. Credentials use upstream's XDG configuration
directory and mode-0600 storage. Installing or testing command help does
not pair with or modify a router.

## Dockge deployment

Deploy `stack/` as `/opt/stacks/debian`. Persistent state is under
`/home/gromit/debian-repository`, on maccha's large data filesystem rather
than its small root partition. The Compose UID/GID defaults match maccha.

```sh
cd /opt/stacks/debian
docker compose build reprepro
docker compose run --rm reprepro init
docker compose up -d nginx
```

`init` generates a signing key only when none exists; preserve the `gnupg/`
directory. A new key requires rebuilding the bootstrap package, not merely
restarting the stack. NPM forwards the HTTPS hostname to `172.17.0.1:8591`.
Private access control is enforced by this stack, not by NPM's global ACL.

Place package files in `incoming/`, then publish:

```sh
docker compose run --rm reprepro publish public main /repository/incoming/PACKAGE.deb
docker compose run --rm reprepro publish public thirdparty /repository/incoming/PACKAGE.deb
docker compose run --rm reprepro publish private private /repository/incoming/PACKAGE.deb
docker compose run --rm reprepro list public
docker compose run --rm reprepro issue home
```

`issue` creates a random per-host password, stores a root-style APT credential
file in `credentials/home.conf` with mode 0600, and adds its bcrypt hash to the
server. It does not display the password. Transfer the credential securely to
the client's `/etc/apt/auth.conf.d/synaxe.conf` (root:root, 0600), or enter it
through debconf on private-bootstrap installation. `user USER` rotates a
server password supplied on stdin; update the client's credential too.

## Tests and operational boundaries

`tests/lifecycle.sh` runs inside a disposable build container with built
packages mounted at `/packages`. It checks missing-credential rejection,
provisioning, upgrades, rotation, password clearing, remove/purge, Stern's
conffile preservation and systemd units. `tests/live-bootstrap.py` runs the
landing page's exact bootstrap command inside a disposable container.

The backup solution owns backup/restore. Packages and this stack expose
stable paths; they do not create backup jobs or implement a restore engine.
The running hand-installed Stern mirror is not automatically migrated:
its `/etc/systemd/system` units override packaged vendor units until an
administrator performs the documented migration.

Automatic CI upload, watchers and full host profiles
are separate follow-up work; this repository must not imply they are live
until configured and tested.

The reusable GitHub workflow builds and uploads Actions artifacts and
creates a failure issue for our own agents. It does not publish to the
live APT archive or assign a Copilot agent.
