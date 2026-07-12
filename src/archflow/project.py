from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any


MANIFEST_NAME = "archflow.project.json"
SUPPORTED_SCHEMA = "0.1"
SUPPORTED_MODES = {"concept", "preliminary", "construction_assistance"}


class ProjectError(ValueError):
    pass


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ProjectError(f"File not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ProjectError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ProjectError(f"Expected a JSON object: {path}")
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def project_root(manifest_path: Path) -> Path:
    return manifest_path.resolve().parent


def resolve_portable_path(root: Path, value: str, field: str) -> Path:
    candidate = Path(value)
    if candidate.is_absolute():
        raise ProjectError(f"{field} must be relative to the project root: {value}")
    resolved = (root / candidate).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise ProjectError(f"{field} escapes the project root: {value}") from exc
    return resolved


def _required_string(container: dict[str, Any], key: str, field: str, issues: list[str]) -> None:
    if not isinstance(container.get(key), str) or not container[key].strip():
        issues.append(f"{field}.{key} must be a non-empty string")


def validate_manifest(manifest: dict[str, Any], root: Path, check_files: bool = True) -> list[str]:
    issues: list[str] = []
    if manifest.get("schema_version") != SUPPORTED_SCHEMA:
        issues.append(f"schema_version must be {SUPPORTED_SCHEMA!r}")

    project = manifest.get("project")
    if not isinstance(project, dict):
        issues.append("project must be an object")
    else:
        _required_string(project, "id", "project", issues)
        _required_string(project, "title", "project", issues)
        if project.get("mode") not in SUPPORTED_MODES:
            issues.append(f"project.mode must be one of {sorted(SUPPORTED_MODES)}")

    inputs = manifest.get("inputs")
    if not isinstance(inputs, dict):
        issues.append("inputs must be an object")
        inputs = {}

    model = manifest.get("model")
    if not isinstance(model, dict):
        issues.append("model must be an object")
        model = {}

    pipeline = manifest.get("pipeline")
    if not isinstance(pipeline, dict):
        issues.append("pipeline must be an object")
        pipeline = {}

    path_fields = [
        ("inputs.site_cad", inputs.get("site_cad"), False),
        ("inputs.requirements", inputs.get("requirements"), False),
        ("model.building_model", model.get("building_model"), True),
        ("pipeline.output_root", pipeline.get("output_root"), True),
    ]
    for field, value, required in path_fields:
        if value is None and not required:
            continue
        if not isinstance(value, str) or not value.strip():
            issues.append(f"{field} must be a non-empty relative path" if required else f"{field} must be null or a relative path")
            continue
        try:
            resolved = resolve_portable_path(root, value, field)
        except ProjectError as exc:
            issues.append(str(exc))
            continue
        if check_files and field != "pipeline.output_root" and not resolved.is_file():
            issues.append(f"{field} does not exist: {value}")

    legal_sources = inputs.get("legal_sources", [])
    if not isinstance(legal_sources, list):
        issues.append("inputs.legal_sources must be an array")
    else:
        for index, item in enumerate(legal_sources):
            if not isinstance(item, str) or not item.strip():
                issues.append(f"inputs.legal_sources[{index}] must be a relative path")
                continue
            try:
                source = resolve_portable_path(root, item, f"inputs.legal_sources[{index}]")
                if check_files and not source.is_file():
                    issues.append(f"inputs.legal_sources[{index}] does not exist: {item}")
            except ProjectError as exc:
                issues.append(str(exc))

    if pipeline.get("execute_sketchup", False) is not False:
        issues.append("pipeline.execute_sketchup must remain false in manifest schema 0.1")
    return issues


def slug(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return normalized or "project"


def create_project(root: Path, title: str, mode: str, core_skill_root: Path) -> Path:
    root = root.resolve()
    if mode not in SUPPORTED_MODES:
        raise ProjectError(f"Unsupported mode: {mode}")
    root.mkdir(parents=True, exist_ok=True)
    manifest_path = root / MANIFEST_NAME
    if manifest_path.exists():
        raise ProjectError(f"Project already exists: {manifest_path}")

    template = core_skill_root / "assets" / "templates" / "building_model_template.json"
    if not template.is_file():
        raise ProjectError(f"Core building model template is missing: {template}")
    (root / "inputs" / "legal").mkdir(parents=True, exist_ok=True)
    (root / "model").mkdir(parents=True, exist_ok=True)
    shutil.copy2(template, root / "model" / "building_model.json")

    model = read_json(root / "model" / "building_model.json")
    model["project"]["id"] = slug(title).upper()
    model["project"]["title"] = title
    model["project"]["mode"] = mode
    write_json(root / "model" / "building_model.json", model)

    manifest = {
        "schema_version": SUPPORTED_SCHEMA,
        "project": {"id": slug(title), "title": title, "mode": mode},
        "inputs": {"site_cad": None, "requirements": None, "legal_sources": []},
        "model": {"building_model": "model/building_model.json"},
        "pipeline": {"output_root": "outputs/runs", "execute_sketchup": False, "render_provider": "none"},
    }
    write_json(manifest_path, manifest)
    return manifest_path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def input_inventory(manifest: dict[str, Any], root: Path) -> list[dict[str, str]]:
    values: list[tuple[str, Any]] = [
        ("building_model", manifest["model"]["building_model"]),
        ("site_cad", manifest["inputs"].get("site_cad")),
        ("requirements", manifest["inputs"].get("requirements")),
    ]
    values.extend((f"legal_source_{index}", value) for index, value in enumerate(manifest["inputs"].get("legal_sources", [])))
    inventory = []
    for role, value in values:
        if value:
            path = resolve_portable_path(root, value, role)
            inventory.append({"role": role, "path": value, "sha256": sha256_file(path)})
    return inventory


def fingerprint(inventory: list[dict[str, str]]) -> str:
    payload = json.dumps(inventory, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
