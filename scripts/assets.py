#!/usr/bin/env python3
"""Validate approved assets offline; optionally stage or verify the Pages site."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://danny-friedman.github.io/understanding-ancestral-assets/"
BLOG = "https://www.understandingancestral.com"
TYPES = {".gif": {"image/gif"}, ".png": {"image/png"}, ".ico": {"image/x-icon", "image/vnd.microsoft.icon"},
         ".woff": {"font/woff", "application/font-woff"}, ".woff2": {"font/woff2"}}
SIGNATURES = {".gif": (b"GIF87a", b"GIF89a"), ".png": (b"\x89PNG\r\n\x1a\n",),
              ".ico": (b"\x00\x00\x01\x00",), ".woff": (b"wOFF",), ".woff2": (b"wOF2",)}


def inventory(root=ROOT):
    approved = [Path("index.html"), Path("robots.txt"), Path(".nojekyll"),
                Path("upkeep/index.html"), Path("upkeep/privacy.html"), Path("upkeep/terms.html")]
    for item in approved:
        if not (root / item).is_file() or (root / item).is_symlink() or any((root / parent).is_symlink() for parent in item.parents):
            raise ValueError(f"missing/unsafe site file: {item}")
    versions = sorted((root / "assets").iterdir())
    if not versions:
        raise ValueError("no asset versions")
    for folder in versions:
        if folder.is_symlink() or not folder.is_dir() or not re.fullmatch(r"v[1-9][0-9]*", folder.name):
            raise ValueError(f"unexpected asset directory: {folder.name}")
        manifest = json.loads((folder / "manifest.json").read_text())
        if not isinstance(manifest, dict) or not manifest:
            raise ValueError("empty/invalid manifest")
        if {p.name for p in folder.iterdir()} != set(manifest) | {"manifest.json"}:
            raise ValueError(f"unlisted or missing files in {folder.name}")
        approved.append((folder / "manifest.json").relative_to(root))
        for name, expected in manifest.items():
            suffix = Path(name).suffix
            path = folder / name
            if Path(name).name != name or suffix not in TYPES or path.is_symlink():
                raise ValueError("unsafe asset name/type")
            payload = path.read_bytes()
            if len(payload) != expected["bytes"] or hashlib.sha256(payload).hexdigest() != expected["sha256"]:
                raise ValueError(f"manifest mismatch: {name}")
            if not payload.startswith(SIGNATURES[suffix]):
                raise ValueError(f"invalid file signature: {name}")
            approved.append(path.relative_to(root))
    return approved


def verify_public(paths, root=ROOT):
    for path in paths:
        if path.name == ".nojekyll":
            continue
        request = Request(BASE + path.as_posix(), headers={"Origin": BLOG, "User-Agent": "UnderstandingAncestralAssetCheck/1.0"})
        expected = (root / path).read_bytes()
        with urlopen(request, timeout=20) as response:
            if response.status != 200 or response.read(len(expected) + 1) != expected:
                raise ValueError(f"published bytes differ: {path}")
            if path.suffix in TYPES and response.headers.get_content_type() not in TYPES[path.suffix]:
                raise ValueError(f"unexpected MIME type: {path}")
            if path.suffix in (".woff", ".woff2") and response.headers.get("Access-Control-Allow-Origin") not in ("*", BLOG):
                raise ValueError(f"font CORS missing: {path}")
        print(f"PASS published bytes, MIME and applicable CORS: {path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", type=Path)
    parser.add_argument("--verify-public", action="store_true")
    args = parser.parse_args()
    paths = inventory()
    print(f"PASS {len(paths)} approved files; all asset sizes, signatures and SHA-256 hashes")
    if args.stage:
        if args.stage.exists():
            raise ValueError("staging directory already exists; use a fresh directory")
        for path in paths:
            target = args.stage / path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / path, target)
        print("Staged only approved public files; code and repository metadata excluded.")
    if args.verify_public:
        verify_public(paths)


if __name__ == "__main__":
    sys.exit(main())
