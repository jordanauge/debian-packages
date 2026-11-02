#!/usr/bin/env python3
"""Issue a per-host Basic-auth password without displaying it."""
import os
import re
import secrets
import subprocess
import sys
from pathlib import Path

username = sys.argv[1]
if not re.fullmatch(r"[A-Za-z0-9._@+-]+", username):
    raise SystemExit("Invalid username")
os.umask(0o077)
directory = Path("/repository/credentials")
directory.mkdir(mode=0o700, exist_ok=True)
destination = directory / (username + ".conf")
if destination.exists():
    raise SystemExit(f"Credentials already exist: {destination}; rotate explicitly instead")
password = secrets.token_urlsafe(32)
entry = (
    "machine https://debian.at.synaxe.org/private/\n"
    f"login {username}\npassword {password}\n"
)
with destination.open("x") as handle:
    handle.write(entry)
try:
    subprocess.run(
        ["htpasswd", "-iB", "/repository/auth/htpasswd", username],
        input=password + "\n", text=True, check=True,
    )
except (OSError, subprocess.CalledProcessError):
    destination.unlink()
    raise
print(f"Credentials stored in {destination} (mode 0600); transfer securely to that host's APT auth.conf.d.")
