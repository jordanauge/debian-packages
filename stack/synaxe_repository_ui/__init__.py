"""Shared, self-contained Synaxe repository presentation."""

import html
import json
import re
from pathlib import Path


def homebrew_install(scope: str) -> str:
    instructions = (
        "<h2>Install with Homebrew</h2>"
        "<p>Native Synaxe applications and selected third-party packages, "
        "not a mirror of Homebrew core.</p>"
        f'<pre id="bootstrap">brew tap synaxe/{scope} https://homebrew.at.synaxe.org/{scope}/tap.git</pre>'
        '<button data-copy="bootstrap">Copy tap command</button>'
    )
    if scope == "private":
        return instructions + (
            "<p>Private Git access and artifact downloads need separately configured "
            "credentials. Use your Git credential helper and a protected netrc/curl "
            "configuration. Never put passwords in URLs or Brewfiles.</p>"
            '<p><a href="/public/">Public repository</a></p>'
        )
    return instructions + (
        "<pre>brew install synaxe/public/synaxe-homebrew-client</pre>"
        '<p><a href="/private/">Private packages (authentication required)</a></p>'
        "<p>Dependencies may still be downloaded from normal Homebrew channels.</p>"
    )


def fdroid_install() -> str:
    return (
        "<h2>Add the F-Droid repository</h2>"
        "<p>Scan the QR code on your Android device, or copy the repository URL.</p>"
        '<img class="qr" src="/qr.svg" width="224" height="224" alt="F-Droid repository QR code">'
        '<pre id="bootstrap">https://fdroid.at.synaxe.org/repo</pre>'
        '<button data-copy="bootstrap">Copy repository URL</button>'
        '<ol><li>Install <a href="https://f-droid.org">F-Droid</a> on your phone.</li>'
        "<li>Open Settings &rarr; Repositories &rarr; Add.</li>"
        "<li>Scan the code or paste the URL, then confirm the repository.</li></ol>"
        "<p>Use the F-Droid client for repository verification and updates. "
        "APK links in the catalogue are also available for manual downloads.</p>"
    )


def render(platform: str, scope: str, install: str, rows: list[dict] | None) -> str:
    assets = Path(__file__).parent
    title = f"Synaxe {platform} packages"
    values = {
        "TITLE": html.escape(title),
        "PLATFORM": html.escape(platform, quote=True),
        "SCOPE": html.escape(scope, quote=True),
        "INSTALL": install,
        "DATA": json.dumps(rows).replace("<", "\\u003c"),
        "STYLE": (assets / "theme.css").read_text(),
        "SCRIPT": (assets / "catalogue.js").read_text(),
        "LOGO": "<svg" + (assets / "logo.svg").read_text().split("<svg", 1)[1],
    }
    page = (assets / "page.html").read_text()
    # Replace once, so package metadata cannot be interpreted as template markers.
    return re.sub(r"@@([A-Z]+)@@", lambda match: values[match[1]], page)
