#!/bin/sh
# Run in a disposable container; /provision/auth.conf is read-only.
set -eu
export DEBIAN_FRONTEND=noninteractive
if ! command -v curl >/dev/null; then
    apt-get update -qq
    apt-get install -y --no-install-recommends curl
fi
python3 /tests/live-bootstrap.py
install -m 600 /provision/auth.conf /etc/apt/auth.conf.d/synaxe.conf
apt-get install -y synaxe-archive-keyring-private
apt-get update
apt-get install -y --no-install-recommends stern-mirror synaxe-base python3-dahua-rpc-api freebox-cli git-safe
stern-mirror --version
fbx --help >/dev/null
fbx dhcp --help >/dev/null
test ! -e /root/.config/fbx/credentials.json
python3 -c 'from dahua.client import DahuaRpc; client = DahuaRpc("127.0.0.1"); assert client.base_url == "http://127.0.0.1:80"; print("Dahua RPC client imports and constructs without contacting a device.")'
test -s /etc/stern-mirror/stern-mirror.conf
test ! -e /etc/systemd/system/timers.target.wants/stern-mirror.timer
git-safe --version | grep -qx 1.1.0
test ! -e /etc/systemd/system/timers.target.wants/git-safe.timer
test -s /usr/lib/systemd/system/git-safe.service
test -s /usr/lib/systemd/system/git-safe.timer
python3 -c '
import json, runpy, tempfile
from pathlib import Path
sync = runpy.run_path("/usr/bin/git-safe", run_name="git_safe_smoke")["sync_release"]
item = {"api": "https://api.github.com/repos/RPCSX/rpcsx/releases/latest",
        "path": "binaries/rpcsx", "labels": ["emulator", "ps-4", "ps-5"]}
with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    first = sync(root, item)
    latest = root / item["path"] / "latest"
    manifest = json.loads((latest / "manifest.json").read_text())
    assert first["assets"] == len(manifest["files"]) > 0
    generation = latest.resolve()
    assert sync(root, item) == first
    assert latest.resolve() == generation
    print("Live RPCSX binary download, checksums and idempotent reuse passed.")
'
dpkg --print-architecture
echo "Live signed APT installation passed."
