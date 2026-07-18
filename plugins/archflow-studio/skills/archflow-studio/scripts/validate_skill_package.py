#!/usr/bin/env python3
"""Validate the shareable ArchFlow Studio skill package."""

from __future__ import annotations

import re
import json
import hashlib
import sys
import zipfile
from pathlib import Path


REQUIRED_FILES = [
    "SKILL.md",
    "agents/openai.yaml",
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
    "scripts/CadBridge.psm1",
    "assets/codex_cad_bridge.lsp",
    "assets/integration-lock.json",
    "assets/sketchup-extension/archflow_bridge.rb",
    "assets/sketchup-extension/archflow_bridge/main.rb",
    "assets/templates/building_model_schema.json",
    "assets/templates/optimization_objectives.json",
    "assets/templates/render_style_catalog.json",
    "references/workstation-setup.md",
    "references/legal-research.md",
    "references/deployment.md",
    "references/troubleshooting.md",
    "references/modeling.md",
    "assets/templates/read_only_test_prompt.txt",
    "assets/templates/white_model_test_prompt.txt",
]


def fail(message: str) -> None:
    print(f"[FAIL] {message}")
    raise SystemExit(1)


def ok(message: str) -> None:
    print(f"[OK] {message}")


def warn(message: str) -> None:
    print(f"[WARN] {message}")


def validate_frontmatter(skill_md: Path) -> None:
    text = skill_md.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not match:
        fail("SKILL.md is missing YAML frontmatter")

    frontmatter = match.group(1)
    if "name: archflow-studio" not in frontmatter:
        fail("SKILL.md frontmatter name is not archflow-studio")
    desc_match = re.search(r"^description:\s*(.+)$", frontmatter, re.MULTILINE)
    if not desc_match or len(desc_match.group(1).strip()) < 80:
        fail("SKILL.md description is missing or too short")
    ok("SKILL.md frontmatter looks valid")


def validate_rbz(path: Path) -> None:
    with zipfile.ZipFile(path) as zf:
        entries = {name.replace("/", "\\") for name in zf.namelist()}
    expected = {"archflow_bridge.rb", "archflow_bridge\\main.rb"}
    if entries != expected:
        fail(f"{path.name} must contain only archflow_bridge.rb and archflow_bridge/main.rb")
    ok(f"RBZ layout valid: {path.name}")


def validate_render_catalog(path: Path) -> None:
    catalog = json.loads(path.read_text(encoding="utf-8"))
    styles = catalog.get("styles", [])
    if len(styles) < 10:
        fail("Render style catalog must contain at least 10 architectural styles")
    identifiers = [item.get("id") for item in styles]
    if any(not item for item in identifiers) or len(identifiers) != len(set(identifiers)):
        fail("Render style IDs must be unique and non-empty")
    for item in styles:
        if not item.get("label_zh") or not item.get("summary_zh") or not item.get("prompt"):
            fail(f"Render style is incomplete: {item.get('id')}")
    if not catalog.get("geometry_lock") or not catalog.get("base_negative_prompt"):
        fail("Render style catalog is missing geometry safeguards")
    ok(f"Render style catalog valid: {len(styles)} styles")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
    root = root.resolve()
    if not root.exists():
        fail(f"Skill path does not exist: {root}")

    for rel in REQUIRED_FILES:
        path = root / rel
        if not path.exists():
            fail(f"Missing required file: {rel}")
    ok("Required file set is present")

    validate_frontmatter(root / "SKILL.md")
    validate_render_catalog(root / "assets" / "templates" / "render_style_catalog.json")

    rbz_dir = root / "assets" / "plugins"
    rbz_files = sorted(rbz_dir.glob("*.rbz"))
    if not rbz_files:
        fail("No RBZ files found under assets/plugins")
    for rbz in rbz_files:
        validate_rbz(rbz)

    if [path.name for path in rbz_files] != ["archflow_bridge.rbz"]:
        fail("Only the ArchFlow-owned archflow_bridge.rbz may be bundled")

    lock = json.loads((root / "assets" / "integration-lock.json").read_text(encoding="utf-8"))
    bridge = lock.get("sketchup_bridge", {})
    if bridge.get("implementation") != "ArchFlow-owned" or bridge.get("license") != "Apache-2.0":
        fail("Integration lock does not identify the ArchFlow-owned bridge")
    locked = {item["file"]: item["sha256"].upper() for item in lock.get("bundled_plugins", [])}
    for rbz in rbz_files:
        relative = rbz.relative_to(root / "assets").as_posix()
        if relative not in locked:
            fail(f"RBZ is missing from integration lock: {relative}")
        if sha256(rbz) != locked[relative]:
            fail(f"RBZ hash does not match integration lock: {relative}")
        ok(f"RBZ hash locked: {relative}")

    openai_yaml = (root / "agents" / "openai.yaml").read_text(encoding="utf-8")
    if "$archflow-studio" not in openai_yaml:
        warn("agents/openai.yaml default_prompt does not mention $archflow-studio")
    else:
        ok("agents/openai.yaml default prompt references the skill")

    print("Skill package validation complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
