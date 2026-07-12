#!/usr/bin/env python3
"""Build the ArchFlow SketchUp RBZ reproducibly from owned source files.

SPDX-FileCopyrightText: 2026 OHDESIGN
SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path


FILES = ("archflow_bridge.rb", "archflow_bridge/main.rb")
ZIP_TIME = (2026, 1, 1, 0, 0, 0)


def build(source: Path, output: Path) -> str:
    missing = [name for name in FILES if not (source / name).is_file()]
    if missing:
        raise FileNotFoundError(f"Missing SketchUp bridge source: {', '.join(missing)}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in FILES:
            info = zipfile.ZipInfo(name, ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, (source / name).read_bytes())
    return hashlib.sha256(output.read_bytes()).hexdigest().upper()


def update_lock(lock_path: Path, relative_file: str, digest: str) -> None:
    lock = {
        "schema_version": "0.2",
        "sketchup_bridge": {
            "implementation": "ArchFlow-owned",
            "protocol": "archflow-sketchup/1",
            "license": "Apache-2.0",
            "source": "assets/sketchup-extension"
        },
        "bundled_plugins": [{"file": relative_file, "sha256": digest}],
    }
    lock_path.write_text(json.dumps(lock, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    skill = Path(__file__).resolve().parents[1]
    parser.add_argument("--source", type=Path, default=skill / "assets" / "sketchup-extension")
    parser.add_argument("--output", type=Path, default=skill / "assets" / "plugins" / "archflow_bridge.rbz")
    parser.add_argument("--lock", type=Path, default=skill / "assets" / "integration-lock.json")
    args = parser.parse_args()
    digest = build(args.source.resolve(), args.output.resolve())
    relative = args.output.resolve().relative_to((skill / "assets").resolve()).as_posix()
    update_lock(args.lock.resolve(), relative, digest)
    print(f"Built {args.output} SHA256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
