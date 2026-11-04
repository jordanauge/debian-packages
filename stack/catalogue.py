#!/usr/bin/env python3
"""Generate separate public/private package catalogues from reprepro indexes."""
import gzip
import hashlib
import html
import shutil
import subprocess
import sys
from pathlib import Path

from synaxe_repository_ui import render

def packages(root):
    rows = {}
    for index in sorted((root / "dists").glob("*/**/Packages.gz")):
        suite = index.relative_to(root / "dists").parts[0]
        component = index.relative_to(root / "dists").parts[1]
        for paragraph in gzip.decompress(index.read_bytes()).decode().strip().split("\n\n"):
            fields = {}
            key = None
            for line in paragraph.splitlines():
                if line.startswith(" ") and key:
                    fields[key] += "\n" + line[1:]
                elif ": " in line:
                    key, value = line.split(": ", 1)
                    fields[key] = value
            if not fields:
                continue
            fields["Suite"], fields["Component"] = suite, component
            identity = (fields["Package"], fields["Version"], fields["Architecture"], suite, component)
            rows[identity] = fields
    return list(rows.values())


def generate(base):
    for tree in ("public", "private"):
        root = base / tree
        rows = packages(root)
        bootstrap = ""
        if tree == "public":
            candidates = [p for p in rows if p["Package"] == "synaxe-archive-keyring"]
            if candidates:
                package = candidates[0]
                source = root / package["Filename"]
                name = source.name
                shutil.copyfile(source, root / name)
                checksum = hashlib.sha256(source.read_bytes()).hexdigest()
                script = (
                    "#!/bin/sh\nset -eu\n"
                    "d=$(mktemp -d)\n"
                    "trap 'rm -f \"$d/" + name + "\"; rmdir \"$d\"' EXIT\n"
                    'cd "$d"\n'
                    'curl --fail --show-error --location --proto "=https" --proto-redir "=https" '
                    "--output " + name + " https://debian.at.synaxe.org/" + name + "\n"
                    "printf '%s  %s\\n' " + checksum + " " + name + " | sha256sum --check -\n"
                    'if [ "$(id -u)" -eq 0 ]; then\n'
                    "    apt install --yes ./" + name + "\n    apt update\n"
                    "else\n    sudo apt install --yes ./" + name + "\n    sudo apt update\nfi\n"
                )
                installer = root / ".install.sh.new"
                installer.write_text(script)
                installer.replace(root / "install.sh")
                command = (
                    'curl -fSL --proto "=https" --proto-redir "=https" '
                    "-o synaxe-install.sh https://debian.at.synaxe.org/install.sh"
                    " && sh synaxe-install.sh"
                )
                key_info = subprocess.run(
                    ["gpg", "--batch", "--with-colons", "--show-keys", str(root / "synaxe-archive-keyring.asc")],
                    check=True, capture_output=True, text=True,
                )
                fingerprint = next(line.split(":")[9] for line in key_info.stdout.splitlines() if line.startswith("fpr:"))
                bootstrap = (
                    f'<h2>Enable the public repository</h2><p><a href="/{html.escape(name)}">'
                    f'Download {html.escape(name)}</a></p><p>SHA-256: <code>{checksum}</code></p>'
                    f'<p>Signing key fingerprint: <code>{html.escape(fingerprint)}</code></p>'
                    '<p>Copy and paste (requires curl). Trust the HTTPS site for this first install; '
                    'verify the signing fingerprint independently for stronger bootstrap trust.</p>'
                    f'<pre id="bootstrap">{html.escape(command)}</pre>'
                    '<button onclick="copyText(document.querySelector(\'#bootstrap\').textContent)">Copy install command</button>'
                    '<p><a href="/install.sh">Inspect install.sh</a> before running it. '
                    'The command downloads the complete script before execution; it does not pipe into a shell. '
                    'The script verifies the package checksum and requests sudo only for installation.</p>'
                    '<p><a href="/synaxe-archive-keyring.asc">Public signing key</a> | '
                    '<a href="/private/">Private packages and host profiles</a></p>'
                    '<p>Enable private access: <code>sudo apt install synaxe-archive-keyring-private</code>, '
                    'enter credentials, then <code>sudo apt update</code>.</p>'
                )
        if tree == "private":
            bootstrap = (
                "<h2>Private Debian packages</h2>"
                "<p>This catalogue is authenticated. Enable the public archive first, "
                "then provision your per-device credentials.</p>"
                "<pre>sudo apt install synaxe-archive-keyring-private\nsudo apt update</pre>"
                '<p><a href="/">Public repository setup</a></p>'
            )
        for package in rows:
            package["DownloadLabel"] = "Download .deb"
        page = render("Debian", tree, bootstrap, rows)
        destination = root / "index.html"
        staged = root / ".index.html.new"
        staged.write_text(page)
        staged.replace(destination)


if __name__ == "__main__":
    generate(Path(sys.argv[1]))
