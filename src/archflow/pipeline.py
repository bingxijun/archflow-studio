from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .project import (
    ProjectError,
    fingerprint,
    input_inventory,
    project_root,
    read_json,
    resolve_portable_path,
    validate_manifest,
    write_json,
)


CORE_SKILL = "archflow-studio"
LEGACY_CORE_SKILL = "architectural-cad-to-sketchup"


def discover_core_skill(explicit: str | None = None) -> Path:
    candidates = []
    if explicit:
        candidates.append(Path(explicit))
    if os.environ.get("ARCHFLOW_CORE_SKILL"):
        candidates.append(Path(os.environ["ARCHFLOW_CORE_SKILL"]))
    candidates.extend(
        [
            Path(__file__).resolve().parents[2],
            Path.cwd() / "plugins" / "archflow-studio" / "skills" / "archflow-studio",
            Path.cwd() / "skills" / LEGACY_CORE_SKILL,
            Path.home() / ".codex" / "skills" / CORE_SKILL,
            Path.home() / ".codex" / "skills" / LEGACY_CORE_SKILL,
        ]
    )
    for candidate in candidates:
        if (candidate / "scripts" / "architectural_pipeline.py").is_file():
            return candidate.resolve()
    searched = ", ".join(str(path) for path in candidates)
    raise ProjectError(f"Could not find {CORE_SKILL}. Searched: {searched}")


def doctor(core_skill: str | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "python": {"status": "ready", "executable": sys.executable, "version": sys.version.split()[0]},
        "capabilities": {},
    }
    try:
        root = discover_core_skill(core_skill)
        result["capabilities"][CORE_SKILL] = {"status": "ready", "path": str(root)}
    except ProjectError as exc:
        result["capabilities"][CORE_SKILL] = {"status": "missing", "message": str(exc)}
    unified = None
    try:
        unified = discover_core_skill(core_skill)
    except ProjectError:
        pass
    bundled = {
        "archflow-cad-bridge": unified / "scripts" / "cad-cli.ps1" if unified else None,
        "archflow-sketchup-bridge": unified / "scripts" / "preflight_check.ps1" if unified else None,
    }
    for name in ("archflow-cad-bridge", "archflow-sketchup-bridge"):
        bundled_path = bundled[name]
        if bundled_path and bundled_path.is_file():
            result["capabilities"][name] = {"status": "ready", "path": str(bundled_path), "source": "bundled"}
        else:
            result["capabilities"][name] = {
                "status": "missing",
                "path": str(bundled_path) if bundled_path else None,
                "source": "bundled",
            }
    result["status"] = "ready" if all(item["status"] == "ready" for item in result["capabilities"].values()) else "degraded"
    return result


def build_plan(manifest_path: Path, stage: str, core_skill: Path, output_dir: Path) -> list[list[str]]:
    manifest = read_json(manifest_path)
    root = project_root(manifest_path)
    script = core_skill / "scripts" / "architectural_pipeline.py"
    model = resolve_portable_path(root, manifest["model"]["building_model"], "model.building_model")
    commands: list[list[str]] = []
    requirements = manifest["inputs"].get("requirements")
    if stage in {"parse", "build"} and requirements:
        source = resolve_portable_path(root, requirements, "inputs.requirements")
        commands.append([sys.executable, str(script), "parse-requirements", str(source), "--output", str(output_dir / "parsed_requirements.yaml")])
    if stage == "parse" and not requirements:
        raise ProjectError("The parse stage requires inputs.requirements")
    if stage == "validate":
        commands.append([sys.executable, str(script), "validate", str(model), "--output-dir", str(output_dir)])
    if stage == "build":
        commands.append([sys.executable, str(script), "all", str(model), "--output-dir", str(output_dir)])
    return commands


def run_project(manifest_path: Path, stage: str, core_skill_arg: str | None = None, plan_only: bool = False) -> dict[str, Any]:
    manifest_path = manifest_path.resolve()
    manifest = read_json(manifest_path)
    root = project_root(manifest_path)
    issues = validate_manifest(manifest, root, check_files=True)
    if issues:
        raise ProjectError("Project manifest is invalid:\n- " + "\n- ".join(issues))
    core_skill = discover_core_skill(core_skill_arg)
    inventory = input_inventory(manifest, root)
    digest = fingerprint(inventory)
    run_time = datetime.now(timezone.utc)
    timestamp = run_time.strftime("%Y%m%dT%H%M%S") + f"{run_time.microsecond // 1000:03d}Z"
    run_id = f"{timestamp}-{digest[:8]}"
    output_root = resolve_portable_path(root, manifest["pipeline"]["output_root"], "pipeline.output_root")
    output_dir = output_root / run_id
    commands = build_plan(manifest_path, stage, core_skill, output_dir)
    plan = {
        "stage": stage,
        "run_id": run_id,
        "output_dir": str(output_dir),
        "input_fingerprint": digest,
        "inputs": inventory,
        "commands": commands,
        "mutates_source_cad": False,
        "executes_sketchup": False,
    }
    if plan_only:
        return plan

    output_dir.mkdir(parents=True, exist_ok=False)
    started = run_time.isoformat()
    stdout_parts: list[str] = []
    stderr_parts: list[str] = []
    exit_code = 0
    try:
        for command in commands:
            completed = subprocess.run(command, cwd=root, text=True, encoding="utf-8", errors="replace", capture_output=True, check=False)
            stdout_parts.append(completed.stdout)
            stderr_parts.append(completed.stderr)
            if completed.returncode:
                exit_code = completed.returncode
                break
    except OSError as exc:
        exit_code = 127
        stderr_parts.append(str(exc))

    (output_dir / "stdout.log").write_text("".join(stdout_parts), encoding="utf-8")
    (output_dir / "stderr.log").write_text("".join(stderr_parts), encoding="utf-8")
    record = {
        **plan,
        "started_at": started,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "exit_code": exit_code,
        "status": "succeeded" if exit_code == 0 else "failed",
        "core_skill": str(core_skill),
    }
    write_json(output_dir / "run.json", record)
    write_json(root / ".archflow" / "last-run.json", record)
    if exit_code:
        raise ProjectError(f"Pipeline failed with exit code {exit_code}. See {output_dir / 'stderr.log'}")
    return record


def last_status(manifest_path: Path) -> dict[str, Any]:
    path = project_root(manifest_path) / ".archflow" / "last-run.json"
    return read_json(path)


def pretty_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)
