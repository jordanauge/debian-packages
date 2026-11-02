"""Run the landing page's exact bootstrap command in a disposable container."""
import subprocess
import re
import urllib.request
from html.parser import HTMLParser


class CommandParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.active = False
        self.command = ""

    def handle_starttag(self, tag, attrs):
        if tag == "pre" and ("id", "bootstrap") in attrs:
            self.active = True

    def handle_endtag(self, tag):
        if tag == "pre":
            self.active = False

    def handle_data(self, data):
        if self.active:
            self.command += data


parser = CommandParser()
with urllib.request.urlopen("https://debian.at.synaxe.org/", timeout=30) as response:
    parser.feed(response.read().decode())
if not parser.command:
    raise SystemExit("Landing page has no bootstrap command")
with urllib.request.urlopen("https://debian.at.synaxe.org/install.sh", timeout=30) as response:
    script = response.read().decode()
checksum = re.search(r"\b[0-9a-f]{64}\b", script)
if checksum is None:
    raise SystemExit("Bootstrap script has no checksum")
invalid = script.replace(checksum.group(), "0" * 64)
rejected = subprocess.run(["sh", "-c", invalid], capture_output=True, text=True)
if rejected.returncode == 0 or "FAILED" not in rejected.stdout:
    raise SystemExit("Bootstrap command did not reject an invalid checksum as expected")
print("Incorrect bootstrap checksum rejected.", flush=True)
subprocess.run(["sh", "-c", parser.command], check=True)
