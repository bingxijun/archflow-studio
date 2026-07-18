#!/usr/bin/env python3
"""Prepare traceable image-edit jobs for ArchFlow architectural rendering."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SKILL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = SKILL_ROOT / "assets" / "templates" / "render_style_catalog.json"
SUPPORTED_VIEWS = {"current", "front", "right", "top", "axon"}


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalized(value: str) -> str:
    return re.sub(r"[\s_-]+", " ", value.strip().lower())


def load_catalog(path: Path = DEFAULT_CATALOG) -> dict[str, Any]:
    catalog = read_json(path.resolve())
    styles = catalog.get("styles")
    if not isinstance(styles, list) or not styles:
        raise ValueError("Render style catalog contains no styles")
    identifiers = [style.get("id") for style in styles]
    if any(not isinstance(item, str) or not item for item in identifiers) or len(identifiers) != len(set(identifiers)):
        raise ValueError("Render style IDs must be unique non-empty strings")
    return catalog


def resolve_style(catalog: dict[str, Any], requested: str, custom_style: str | None = None) -> dict[str, Any]:
    if normalized(requested) == "custom":
        if not custom_style or not custom_style.strip():
            raise ValueError("--custom-style is required when --style custom")
        description = custom_style.strip()
        return {
            "id": "custom",
            "label_zh": "自定义风格",
            "label_en": "Custom style",
            "summary_zh": description,
            "prompt": description,
            "provider_hint": "custom",
        }
    wanted = normalized(requested)
    for style in catalog["styles"]:
        candidates = [style["id"], style.get("label_zh", ""), style.get("label_en", ""), *style.get("aliases", [])]
        if wanted in {normalized(str(item)) for item in candidates if item}:
            return style
    choices = ", ".join(style["id"] for style in catalog["styles"])
    raise ValueError(f"Unknown render style {requested!r}. Available: {choices}, custom")


def base_prompt_from_manifest(path: Path | None, view: str) -> tuple[str, dict[str, Any] | None]:
    if not path:
        return "Architectural visualization based strictly on the supplied SketchUp view.", None
    manifest = read_json(path.resolve())
    if view != "current":
        for item in manifest.get("views", []):
            if item.get("id") == view:
                return str(item.get("prompt") or "Architectural visualization based strictly on the supplied view."), manifest
    return "Architectural visualization based strictly on the supplied current SketchUp view.", manifest


def prepare_job(
    *,
    source_image: Path,
    view: str,
    style_name: str,
    output: Path,
    catalog_path: Path = DEFAULT_CATALOG,
    model_path: Path | None = None,
    render_manifest_path: Path | None = None,
    custom_style: str | None = None,
    provider: str = "auto",
) -> dict[str, Any]:
    source_image = source_image.resolve()
    if view not in SUPPORTED_VIEWS:
        raise ValueError(f"Unsupported view: {view}")
    if not source_image.is_file():
        raise FileNotFoundError(f"Source image not found: {source_image}")
    if source_image.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
        raise ValueError("Source image must be PNG, JPG, JPEG, or WebP")

    catalog = load_catalog(catalog_path)
    style = resolve_style(catalog, style_name, custom_style)
    base_prompt, render_manifest = base_prompt_from_manifest(render_manifest_path, view)
    locks = list(catalog.get("geometry_lock", []))
    lock_text = ", ".join(locks)
    prompt = (
        f"{base_prompt.rstrip()} "
        "Use the source image as a strict geometry, camera, crop, and composition reference. "
        f"Selected visual direction: {style['prompt'].rstrip()}. "
        f"Preserve exactly: {lock_text}. "
        "Treat lighting, weather, people, planting, loose furniture, and background atmosphere as creative layers only. "
        "This is a concept visualization, not evidence of code compliance, structural adequacy, or constructability."
    )

    model_info = None
    if model_path:
        model_path = model_path.resolve()
        if not model_path.is_file():
            raise FileNotFoundError(f"Building model not found: {model_path}")
        model_info = {"path": str(model_path), "sha256": sha256(model_path)}

    job = {
        "schema_version": "0.1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "ready",
        "action": "image_edit",
        "provider": provider,
        "input_fidelity": "high",
        "view": view,
        "source_image": {"path": str(source_image), "sha256": sha256(source_image)},
        "building_model": model_info,
        "render_manifest": {
            "path": str(render_manifest_path.resolve()),
            "project_id": render_manifest.get("project_id") if render_manifest else None,
        } if render_manifest_path else None,
        "style": {
            "id": style["id"],
            "label_zh": style.get("label_zh"),
            "label_en": style.get("label_en"),
            "summary_zh": style.get("summary_zh"),
            "provider_hint": style.get("provider_hint"),
        },
        "geometry_lock": locks,
        "prompt": prompt,
        "negative_prompt": catalog.get("base_negative_prompt", ""),
        "human_review": [
            "Compare camera, crop, footprint, floor count, roof silhouette, and openings with the source image.",
            "Treat the result as concept visualization only.",
        ],
    }
    write_json(output.resolve(), job)
    return job


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare ArchFlow image-edit jobs from SketchUp view exports.")
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    sub = parser.add_subparsers(dest="command", required=True)

    list_cmd = sub.add_parser("list-styles", help="List built-in architectural render styles.")
    list_cmd.add_argument("--json", action="store_true")

    brief = sub.add_parser("brief", help="Resolve one style and print its short user-facing description.")
    brief.add_argument("--style", required=True)
    brief.add_argument("--custom-style")

    prepare = sub.add_parser("prepare", help="Write a traceable render job manifest for an exported view image.")
    prepare.add_argument("--source-image", type=Path, required=True)
    prepare.add_argument("--view", choices=sorted(SUPPORTED_VIEWS), required=True)
    prepare.add_argument("--style", required=True)
    prepare.add_argument("--custom-style")
    prepare.add_argument("--model", type=Path)
    prepare.add_argument("--render-manifest", type=Path)
    prepare.add_argument("--provider", default="auto")
    prepare.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        catalog = load_catalog(args.catalog)
        if args.command == "list-styles":
            rows = [
                {"id": style["id"], "label_zh": style.get("label_zh"), "summary_zh": style.get("summary_zh")}
                for style in catalog["styles"]
            ]
            if args.json:
                print(json.dumps(rows, ensure_ascii=False, indent=2))
            else:
                for row in rows:
                    print(f"{row['id']}\t{row['label_zh']}\t{row['summary_zh']}")
            return 0
        if args.command == "brief":
            style = resolve_style(catalog, args.style, args.custom_style)
            print(json.dumps({
                "id": style["id"],
                "label_zh": style.get("label_zh"),
                "summary_zh": style.get("summary_zh"),
            }, ensure_ascii=False, indent=2))
            return 0
        job = prepare_job(
            source_image=args.source_image,
            view=args.view,
            style_name=args.style,
            custom_style=args.custom_style,
            output=args.output,
            catalog_path=args.catalog,
            model_path=args.model,
            render_manifest_path=args.render_manifest,
            provider=args.provider,
        )
        print(json.dumps(job, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
