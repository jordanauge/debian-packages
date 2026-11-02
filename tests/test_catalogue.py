import gzip
import hashlib
import html
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "stack"))
import catalogue


class CatalogueTests(unittest.TestCase):
    def test_separate_catalogues_and_bootstrap(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            for tree, name in (("public", "synaxe-archive-keyring"), ("private", "private-test-tool")):
                root = base / tree
                index = root / "dists/forky/main/binary-arm64/Packages.gz"
                index.parent.mkdir(parents=True)
                package = root / "pool/test_1_all.deb"
                package.parent.mkdir()
                package.write_bytes(b"test package")
                paragraph = (
                    f"Package: {name}\nVersion: 1\nArchitecture: all\n"
                    "Description: test <script>package</script>\n details\n"
                    "Filename: pool/test_1_all.deb\n\n"
                )
                index.write_bytes(gzip.compress(paragraph.encode()))
                shutil.copyfile(
                    Path(__file__).resolve().parents[1] / "bootstrap/keyrings/synaxe-archive-keyring.asc",
                    root / "synaxe-archive-keyring.asc",
                )
            catalogue.generate(base)
            public = (base / "public/index.html").read_text()
            private = (base / "private/index.html").read_text()
            self.assertNotIn("private-test-tool", public)
            self.assertNotIn("synaxe-host-home", public)
            self.assertIn("private-test-tool", private)
            self.assertNotIn("synaxe-host-home", private)
            self.assertIn('id="bootstrap"', public)
            self.assertNotIn('id="bootstrap"', private)
            self.assertIn("\\u003cscript>", public)
            self.assertTrue((base / "public/test_1_all.deb").is_file())
            script = base / "public/install.sh"
            self.assertIn(hashlib.sha256(b"test package").hexdigest(), script.read_text())
            self.assertIn("&& sh synaxe-install.sh", html.unescape(public))
            self.assertNotIn(" | sh", public)
            self.assertFalse((base / "private/install.sh").exists())
            subprocess.run(["sh", "-n", str(script)], check=True)
            self.assertEqual(len(catalogue.packages(base / "public")), 1)


if __name__ == "__main__":
    unittest.main()
