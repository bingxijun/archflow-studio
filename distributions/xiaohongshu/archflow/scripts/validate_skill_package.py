#!/usr/bin/env python3
"""Validate the standalone Xiaohongshu ArchFlow Skill package."""

from __future__ import annotations

import hashlib
import io
import json
import re
import sys
import zipfile
from pathlib import Path


SKILL_NAME = "archflow"
MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_PACKAGE_BYTES = 30 * 1024 * 1024
REQUIRED_FILES = [
    "SKILL.md",
    "references/permissions-and-security.md",
    "references/workstation-setup.md",
    "references/legal-research.md",
    "references/deployment.md",
    "references/troubleshooting.md",
    "references/modeling.md",
    "scripts/archflow_mcp_server.py",
    "scripts/preflight_check.ps1",
    "scripts/deploy_sketchup_mcp.ps1",
    "scripts/build_sketchup_rbz.py",
    "scripts/setup_workstation.ps1",
    "scripts/architectural_pipeline.py",
    "scripts/archflow_cli.py",
    "scripts/legal_evidence.py",
    "scripts/design_optimizer.py",
    "scripts/render_workflow.py",
    "scripts/cad-cli.ps1",
    "scripts/CadBridge.ps1",
    "assets/mcp/archflow-sketchup.json",
    "assets/codex_cad_bridge.lsp.txt",
    "assets/integration-lock.json",
    "assets/sketchup-extension/archflow_bridge.rb.txt",
    "assets/sketchup-extension/archflow_bridge/main.rb.txt",
    "assets/templates/building_model_schema.json",
    "assets/templates/optimization_objectives.json",
    "assets/templates/render_style_catalog.json",
    "assets/templates/read_only_test_prompt.txt",
    "assets/templates/white_model_test_prompt.txt",
]
ALLOWED_EXTENSIONS = {
    ".md", ".txt", ".html", ".htm", ".css", ".js", ".py", ".java",
    ".cpp", ".c", ".h", ".php", ".sh", ".bat", ".ps1", ".json",
    ".xml", ".sql", ".ini", ".cfg", ".log", ".db", ".sqlite",
    ".sqlite3", ".mdb", ".accdb", ".sys",
}
FORBIDDEN_SOURCE_MARKERS = (
    "Invoke-Expression",
    "-EncodedCommand",
    "eval" + "(",
    "exec" + "(",
    "base64." + "b64decode",
    "DownloadString" + "(",
)


def fail(message: str) -> None:
    print(f"[FAIL] {message}")
    raise SystemExit(1)


def ok(message: str) -> None:
    print(f"[OK] {message}")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def package_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            fail(f"Symbolic links are not allowed: {path.relative_to(root).as_posix()}")
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if "__pycache__" in relative.parts or path.suffix.lower() == ".pyc":
            fail(f"Generated Python cache must not be published: {relative.as_posix()}")
        files.append(path)
    return files


def validate_frontmatter(skill_md: Path) -> None:
    text = skill_md.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not match:
        fail("SKILL.md is missing YAML frontmatter")
    frontmatter = match.group(1)
    if f"name: {SKILL_NAME}" not in frontmatter:
        fail(f"SKILL.md frontmatter name is not {SKILL_NAME}")
    if set(re.findall(r"^([a-z_]+):", frontmatter, re.MULTILINE)) != {"name", "description"}:
        fail("SKILL.md frontmatter may contain only name and description")
    description = re.search(r"^description:\s*(.+)$", frontmatter, re.MULTILINE)
    if not description or len(description.group(1).strip()) < 80:
        fail("SKILL.md description is missing or too short")
    ok("SKILL.md frontmatter looks valid")


def validate_size(files: list[Path], root: Path) -> None:
    total = 0
    for path in files:
        size = path.stat().st_size
        if size > MAX_FILE_BYTES:
            fail(f"File exceeds 10 MiB: {path.relative_to(root).as_posix()}")
        total += size
    if total > MAX_PACKAGE_BYTES:
        fail(f"Package exceeds 30 MiB: {total} bytes")
    ok(f"Upload limits satisfied: {len(files)} files, {total} bytes")


def validate_source_transparency(files: list[Path], root: Path) -> None:
    source_suffixes = {".py", ".ps1"}
    excluded = {"scripts/validate_skill_package.py"}
    for path in files:
        relative = path.relative_to(root).as_posix()
        transparent_text_source = relative.endswith((".rb.txt", ".lsp.txt"))
        if relative in excluded or (path.suffix.lower() not in source_suffixes and not transparent_text_source):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for marker in FORBIDDEN_SOURCE_MARKERS:
            if marker.lower() in text.lower():
                fail(f"Opaque or arbitrary execution marker {marker!r} found in {relative}")
    ok("Source transparency scan passed")


def validate_allowed_extensions(files: list[Path], root: Path) -> None:
    for path in files:
        if path.suffix.lower() not in ALLOWED_EXTENSIONS:
            fail(f"SkillHub does not allow this file type: {path.relative_to(root).as_posix()}")
    ok("Every file extension is accepted by the SkillHub CLI")


def validate_generated_rbz(root: Path) -> None:
    sources = (
        ("assets/sketchup-extension/archflow_bridge.rb.txt", "archflow_bridge.rb"),
        ("assets/sketchup-extension/archflow_bridge/main.rb.txt", "archflow_bridge/main.rb"),
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for source_name, archive_name in sources:
            info = zipfile.ZipInfo(archive_name, (2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, (root / source_name).read_bytes())
    lock = json.loads((root / "assets" / "integration-lock.json").read_text(encoding="utf-8"))
    bridge = lock.get("sketchup_bridge", {})
    if bridge.get("implementation") != "ArchFlow-owned" or bridge.get("license") != "Apache-2.0":
        fail("Integration lock does not identify the ArchFlow-owned bridge")
    expected = str(lock.get("generated_plugin", {}).get("sha256", "")).upper()
    actual = hashlib.sha256(buffer.getvalue()).hexdigest().upper()
    if actual != expected:
        fail(f"Generated RBZ hash does not match integration lock: {actual}")
    ok("Transparent Ruby sources reproduce the locked RBZ hash")


def validate_render_catalog(root: Path) -> None:
    catalog = json.loads((root / "assets" / "templates" / "render_style_catalog.json").read_text(encoding="utf-8"))
    styles = catalog.get("styles", [])
    identifiers = [item.get("id") for item in styles]
    if len(styles) < 10 or any(not item for item in identifiers) or len(identifiers) != len(set(identifiers)):
        fail("Render style catalog must contain at least 10 unique styles")
    if not catalog.get("geometry_lock") or not catalog.get("base_negative_prompt"):
        fail("Render style catalog is missing geometry safeguards")
    ok(f"Render style catalog valid: {len(styles)} styles")


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
    root = root.resolve()
    if not root.exists():
        fail(f"Skill path does not exist: {root}")
    for relative in REQUIRED_FILES:
        if not (root / relative).is_file():
            fail(f"Missing required file: {relative}")
    ok("Required standalone file set is present")
    files = package_files(root)
    validate_frontmatter(root / "SKILL.md")
    validate_size(files, root)
    validate_allowed_extensions(files, root)
    validate_source_transparency(files, root)
    validate_render_catalog(root)
    validate_generated_rbz(root)
    permissions = (root / "references" / "permissions-and-security.md").read_text(encoding="utf-8")
    for required in ("127.0.0.1:9877", "不发送遥测", "用户明确要求", "MCP"):
        if required not in permissions:
            fail(f"Permission disclosure is missing: {required}")
    ok("Permission disclosures are present")
    print("Xiaohongshu Skill package validation complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
