#!/usr/bin/env python3
"""Build a deterministic Xiaohongshu upload ZIP with SKILL.md at its root."""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
import zipfile
from pathlib import Path


ZIP_TIME = (2026, 1, 1, 0, 0, 0)


def main() -> int:
    parser = argparse.ArgumentParser()
    root = Path(__file__).resolve().parents[1]
    parser.add_argument("--output", type=Path, default=root.parent / "archflow-xiaohongshu.zip")
    args = parser.parse_args()
    output = args.output.resolve()
    if root in output.parents:
        raise SystemExit("Output ZIP must be outside the Skill directory")
    validator = root / "scripts" / "validate_skill_package.py"
    subprocess.run([sys.executable, str(validator), str(root)], check=True)
    files = [
        path for path in sorted(root.rglob("*"))
        if path.is_file() and "__pycache__" not in path.relative_to(root).parts and path.suffix.lower() != ".pyc"
    ]
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            relative = path.relative_to(root).as_posix()
            info = zipfile.ZipInfo(relative, ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes())
    digest = hashlib.sha256(output.read_bytes()).hexdigest().upper()
    print(f"Built {output}")
    print(f"Files={len(files)} Size={output.stat().st_size} SHA256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
