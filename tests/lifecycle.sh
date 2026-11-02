#!/bin/sh
# Run only inside a disposable synaxe-deb-builder container.
set -eu
export DEBIAN_FRONTEND=noninteractive
dpkg -i /packages/synaxe-archive-keyring_[0-9]*_all.deb
test -s /usr/share/keyrings/synaxe-archive-keyring.gpg
grep -q 'Components: main thirdparty' /etc/apt/sources.list.d/synaxe.sources
if dpkg -i /packages/synaxe-archive-keyring-private_*_all.deb; then
    echo "Missing private credentials were incorrectly accepted" >&2
    exit 1
fi
test ! -e /etc/apt/sources.list.d/synaxe-private.sources
install -d /etc/apt/auth.conf.d
printf 'machine https://debian.at.synaxe.org/private/\nlogin test-host\npassword test-only-password\n' \
    > /etc/apt/auth.conf.d/synaxe.conf
chmod 600 /etc/apt/auth.conf.d/synaxe.conf
dpkg --configure synaxe-archive-keyring-private
test "$(stat -c %a /etc/apt/auth.conf.d/synaxe.conf)" = 600
test "$(stat -c %U /etc/apt/auth.conf.d/synaxe.conf)" = root
grep -q 'Components: private' /etc/apt/sources.list.d/synaxe-private.sources
dpkg -i /packages/synaxe-archive-keyring-private_*_all.deb
grep -q test-only-password /etc/apt/auth.conf.d/synaxe.conf
printf 'synaxe-archive-keyring-private synaxe-archive-keyring-private/username string test-host\nsynaxe-archive-keyring-private synaxe-archive-keyring-private/password password rotated-test-password\n' \
    | debconf-set-selections
dpkg-reconfigure -f noninteractive synaxe-archive-keyring-private
grep -q rotated-test-password /etc/apt/auth.conf.d/synaxe.conf
printf 'GET synaxe-archive-keyring-private/password\n' | debconf-communicate \
    | grep -qx '0 '
dpkg -i /packages/stern-mirror_1.2.2_all.deb
stern-mirror --version | grep -q 1.2.2
pinmame-extract --help >/dev/null
test "$(stern-mirror --config /etc/stern-mirror/stern-mirror.conf --get TARGET_DIR)" = /srv/stern-mirror
systemd-analyze verify /usr/lib/systemd/system/stern-mirror.service /usr/lib/systemd/system/stern-mirror.timer
test ! -e /etc/systemd/system/timers.target.wants/stern-mirror.timer
printf '\n# administrator setting\n' >> /etc/stern-mirror/stern-mirror.conf
dpkg -i /packages/stern-mirror_1.2.2_all.deb
grep -q 'administrator setting' /etc/stern-mirror/stern-mirror.conf
dpkg --remove synaxe-archive-keyring-private
test ! -e /etc/apt/sources.list.d/synaxe-private.sources
test -e /etc/apt/auth.conf.d/synaxe.conf
dpkg --purge synaxe-archive-keyring-private
test ! -e /etc/apt/auth.conf.d/synaxe.conf
echo "Package lifecycle checks passed."
