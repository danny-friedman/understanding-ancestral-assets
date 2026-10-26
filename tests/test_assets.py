import contextlib
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import assets


class AssetTests(unittest.TestCase):
    def fixture(self, root):
        for path in assets.inventory():
            target = root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(assets.ROOT / path, target)

    def test_corrupted_font_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.fixture(root)
            (root / "assets/v1/mtg.woff2").write_bytes(b"broken")
            with self.assertRaisesRegex(ValueError, "manifest mismatch"):
                assets.inventory(root)

    def test_unlisted_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.fixture(root)
            (root / "assets/v1/unapproved.txt").write_text("not an approved asset")
            with self.assertRaisesRegex(ValueError, "unlisted"):
                assets.inventory(root)

    def test_path_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.fixture(root)
            path = root / "assets/v1/manifest.json"
            manifest = json.loads(path.read_text())
            manifest["../escape.woff"] = manifest.pop("mtg.woff")
            path.write_text(json.dumps(manifest))
            with self.assertRaises(ValueError):
                assets.inventory(root)

    def test_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.fixture(root)
            path = root / "assets/v1/mtg.woff"
            path.unlink()
            path.symlink_to(root / "assets/v1/mtg.woff2")
            with self.assertRaisesRegex(ValueError, "unsafe"):
                assets.inventory(root)

    def test_publish_bundle_excludes_code_and_metadata(self):
        with tempfile.TemporaryDirectory() as temp:
            stage = Path(temp) / "site"
            with patch.object(sys, "argv", ["assets.py", "--stage", str(stage)]), contextlib.redirect_stdout(io.StringIO()):
                assets.main()
            actual = {p.relative_to(stage) for p in stage.rglob("*") if p.is_file()}
            self.assertEqual(actual, set(assets.inventory()))
            self.assertFalse((stage / ".git").exists())
            self.assertFalse((stage / "scripts").exists())


if __name__ == "__main__":
    unittest.main()
