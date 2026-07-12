#!/usr/bin/env python3
"""Deterministic MVP pipeline for semantic architectural CAD and SketchUp drafts."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import zipfile
from pathlib import Path
from typing import Any, Iterable
from xml.etree import ElementTree


SKILL_DIR = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = SKILL_DIR / "assets" / "templates"
DEFAULT_LAYER_MAP = TEMPLATE_DIR / "layer_map.json"
DEFAULT_MATERIAL_MAP = TEMPLATE_DIR / "material_map.json"


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def safe_name(value: Any) -> str:
    text = re.sub(r"[^A-Za-z0-9]+", "-", str(value or "UNNAMED").upper()).strip("-")
    return text or "UNNAMED"


def polygon_area(points: list[list[float]]) -> float:
    return abs(
        sum(
            points[i][0] * points[(i + 1) % len(points)][1]
            - points[(i + 1) % len(points)][0] * points[i][1]
            for i in range(len(points))
        )
    ) / 2.0


def signed_area(points: list[list[float]]) -> float:
    return sum(
        points[i][0] * points[(i + 1) % len(points)][1]
        - points[(i + 1) % len(points)][0] * points[i][1]
        for i in range(len(points))
    ) / 2.0


def distance(a: list[float], b: list[float]) -> float:
    return math.hypot(b[0] - a[0], b[1] - a[1])


def cross(a: list[float], b: list[float], c: list[float]) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def point_on_segment(p: list[float], a: list[float], b: list[float], eps: float = 1e-7) -> bool:
    return abs(cross(a, b, p)) <= eps and min(a[0], b[0]) - eps <= p[0] <= max(a[0], b[0]) + eps and min(a[1], b[1]) - eps <= p[1] <= max(a[1], b[1]) + eps


def segments_intersect(a: list[float], b: list[float], c: list[float], d: list[float]) -> bool:
    c1, c2, c3, c4 = cross(a, b, c), cross(a, b, d), cross(c, d, a), cross(c, d, b)
    if ((c1 > 0 > c2) or (c2 > 0 > c1)) and ((c3 > 0 > c4) or (c4 > 0 > c3)):
        return True
    return any((point_on_segment(p, x, y) for p, x, y in ((c, a, b), (d, a, b), (a, c, d), (b, c, d))))


def polygon_self_intersects(points: list[list[float]]) -> bool:
    n = len(points)
    for i in range(n):
        a, b = points[i], points[(i + 1) % n]
        for j in range(i + 1, n):
            if j in (i, (i + 1) % n) or (j + 1) % n in (i, (i + 1) % n):
                continue
            c, d = points[j], points[(j + 1) % n]
            if segments_intersect(a, b, c, d):
                return True
    return False


def point_in_polygon(point: list[float], polygon: list[list[float]]) -> bool:
    inside = False
    j = len(polygon) - 1
    for i in range(len(polygon)):
        a, b = polygon[i], polygon[j]
        if point_on_segment(point, a, b):
            return True
        if (a[1] > point[1]) != (b[1] > point[1]):
            x_hit = (b[0] - a[0]) * (point[1] - a[1]) / (b[1] - a[1]) + a[0]
            if point[0] < x_hit:
                inside = not inside
        j = i
    return inside


def point_segment_distance(point: list[float], a: list[float], b: list[float]) -> float:
    dx, dy = b[0] - a[0], b[1] - a[1]
    denom = dx * dx + dy * dy
    if denom == 0:
        return distance(point, a)
    t = max(0.0, min(1.0, ((point[0] - a[0]) * dx + (point[1] - a[1]) * dy) / denom))
    return distance(point, [a[0] + t * dx, a[1] + t * dy])


def polygon_min_boundary_distance(points: list[list[float]], boundary: list[list[float]]) -> float:
    return min(
        point_segment_distance(p, boundary[i], boundary[(i + 1) % len(boundary)])
        for p in points
        for i in range(len(boundary))
    )


def valid_polygon(value: Any) -> bool:
    return isinstance(value, list) and len(value) >= 3 and all(
        isinstance(p, list) and len(p) == 2 and all(isinstance(v, (int, float)) for v in p)
        for p in value
    )


def add_issue(issues: list[dict[str, str]], level: str, code: str, message: str, path: str) -> None:
    issues.append({"level": level, "code": code, "message": message, "path": path})


def check_polygon(value: Any, path: str, issues: list[dict[str, str]]) -> list[list[float]] | None:
    if not valid_polygon(value):
        add_issue(issues, "ERROR", "INVALID_POLYGON", "Polygon needs at least three numeric [x,y] points.", path)
        return None
    points = [[float(p[0]), float(p[1])] for p in value]
    if polygon_area(points) <= 1e-6:
        add_issue(issues, "ERROR", "ZERO_AREA_POLYGON", "Polygon area must be positive.", path)
    if polygon_self_intersects(points):
        add_issue(issues, "ERROR", "SELF_INTERSECTION", "Polygon self-intersects.", path)
    if points[0] == points[-1]:
        add_issue(issues, "WARNING", "REPEATED_CLOSING_POINT", "Omit the repeated closing point; generators close polygons.", path)
    return points


def calculate_metrics(model: dict[str, Any]) -> dict[str, Any]:
    site_boundary = model.get("site", {}).get("boundary", [])
    site_area_mm2 = polygon_area(site_boundary) if valid_polygon(site_boundary) else 0.0
    storey_areas: dict[str, float] = {}
    for storey in model.get("storeys", []):
        area = sum(polygon_area(space.get("polygon", [])) for space in storey.get("spaces", []) if valid_polygon(space.get("polygon")))
        storey_areas[str(storey.get("id", "?"))] = area / 1_000_000.0
    ordered = sorted(model.get("storeys", []), key=lambda s: float(s.get("z_mm", 0)))
    lowest_slabs = ordered[0].get("slabs", []) if ordered else []
    footprint_mm2 = max((polygon_area(s.get("polygon", [])) for s in lowest_slabs if valid_polygon(s.get("polygon"))), default=0.0)
    total_floor_area_m2 = sum(storey_areas.values())
    site_area_m2 = site_area_mm2 / 1_000_000.0
    modeled_height_mm = max((float(s.get("z_mm", 0)) + float(s.get("height_mm", 0)) for s in ordered), default=0.0)
    return {
        "site_area_m2": round(site_area_m2, 3),
        "footprint_area_m2": round(footprint_mm2 / 1_000_000.0, 3),
        "floor_area_by_storey_m2": {k: round(v, 3) for k, v in storey_areas.items()},
        "gross_floor_area_m2": round(total_floor_area_m2, 3),
        "building_coverage_percent": round((footprint_mm2 / site_area_mm2 * 100.0), 3) if site_area_mm2 else None,
        "floor_area_ratio_percent": round((total_floor_area_m2 / site_area_m2 * 100.0), 3) if site_area_m2 else None,
        "modeled_height_mm": round(modeled_height_mm, 3),
        "area_basis": model.get("project", {}).get("area_basis", "sum_of_space_polygons"),
    }


def constraint_check(name: str, actual: float | None, limit: Any, units: str, sources_verified: bool) -> dict[str, Any]:
    if limit is None:
        return {"name": name, "status": "NOT_PROVIDED", "actual": actual, "limit": None, "units": units}
    numeric_limit = float(limit)
    if actual is None:
        status = "ERROR"
    elif actual > numeric_limit + 1e-7:
        status = "FAIL"
    else:
        status = "PASS" if sources_verified else "UNVERIFIED"
    return {"name": name, "status": status, "actual": actual, "limit": numeric_limit, "units": units}


def validate_model(model: dict[str, Any]) -> dict[str, Any]:
    issues: list[dict[str, str]] = []
    if model.get("schema_version") != "1.0":
        add_issue(issues, "ERROR", "SCHEMA_VERSION", "schema_version must be '1.0'.", "schema_version")
    if model.get("units") != "mm":
        add_issue(issues, "ERROR", "UNITS", "Geometry units must be mm.", "units")

    project = model.get("project")
    if not isinstance(project, dict):
        add_issue(issues, "ERROR", "PROJECT_REQUIRED", "project object is required.", "project")
        project = {}
    for field in ("id", "title", "mode", "use"):
        if not project.get(field):
            add_issue(issues, "ERROR", "PROJECT_FIELD", f"project.{field} is required.", f"project.{field}")
    if project.get("mode") not in ("concept", "preliminary", "construction_assistance"):
        add_issue(issues, "ERROR", "PROJECT_MODE", "Unsupported project mode.", "project.mode")
    for field in ("jurisdiction", "address_or_parcel"):
        if not project.get(field):
            add_issue(issues, "WARNING", "PROJECT_EVIDENCE_MISSING", f"project.{field} is missing.", f"project.{field}")

    site = model.get("site")
    if not isinstance(site, dict):
        add_issue(issues, "ERROR", "SITE_REQUIRED", "site object is required.", "site")
        site = {}
    boundary = check_polygon(site.get("boundary"), "site.boundary", issues)
    for field in ("source_file", "source_revision", "coordinate_system"):
        if not site.get(field):
            add_issue(issues, "WARNING", "SITE_EVIDENCE_MISSING", f"site.{field} is missing.", f"site.{field}")

    storeys = model.get("storeys")
    if not isinstance(storeys, list) or not storeys:
        add_issue(issues, "ERROR", "STOREYS_REQUIRED", "At least one storey is required.", "storeys")
        storeys = []

    seen_ids: dict[str, str] = {}
    storey_z: list[tuple[float, float, str]] = []
    for si, storey in enumerate(storeys):
        spath = f"storeys[{si}]"
        if not isinstance(storey, dict):
            add_issue(issues, "ERROR", "INVALID_STOREY", "Storey must be an object.", spath)
            continue
        for field in ("id", "name"):
            if not storey.get(field):
                add_issue(issues, "ERROR", "STOREY_FIELD", f"{field} is required.", f"{spath}.{field}")
        try:
            z = float(storey.get("z_mm"))
            height = float(storey.get("height_mm"))
            if height <= 0:
                raise ValueError
            storey_z.append((z, z + height, str(storey.get("id", si))))
        except (TypeError, ValueError):
            add_issue(issues, "ERROR", "STOREY_DIMENSIONS", "z_mm must be numeric and height_mm positive.", spath)

        components: list[tuple[str, dict[str, Any], str]] = []
        for collection in ("spaces", "slabs", "walls", "openings", "columns", "beams"):
            items = storey.get(collection, [])
            if not isinstance(items, list):
                add_issue(issues, "ERROR", "COMPONENT_ARRAY", f"{collection} must be an array.", f"{spath}.{collection}")
                continue
            for index, item in enumerate(items):
                ipath = f"{spath}.{collection}[{index}]"
                if not isinstance(item, dict):
                    add_issue(issues, "ERROR", "COMPONENT_OBJECT", "Component must be an object.", ipath)
                    continue
                component_id = str(item.get("id", ""))
                if not component_id:
                    add_issue(issues, "ERROR", "ID_REQUIRED", "Stable component id is required.", f"{ipath}.id")
                elif component_id in seen_ids:
                    add_issue(issues, "ERROR", "DUPLICATE_ID", f"Duplicate id; first used at {seen_ids[component_id]}.", f"{ipath}.id")
                else:
                    seen_ids[component_id] = ipath
                components.append((collection, item, ipath))

        wall_index = {str(w.get("id")): w for w in storey.get("walls", []) if isinstance(w, dict)}
        for collection, item, ipath in components:
            if collection in ("spaces", "slabs"):
                poly = check_polygon(item.get("polygon"), f"{ipath}.polygon", issues)
                if poly and boundary:
                    outside = [p for p in poly if not point_in_polygon(p, boundary)]
                    if outside:
                        add_issue(issues, "ERROR", "OUTSIDE_SITE", f"{len(outside)} polygon vertices are outside the site boundary.", f"{ipath}.polygon")
                if collection == "slabs" and float(item.get("thickness_mm", 0) or 0) <= 0:
                    add_issue(issues, "ERROR", "SLAB_THICKNESS", "Slab thickness must be positive.", f"{ipath}.thickness_mm")
            elif collection == "walls":
                axis = item.get("axis")
                if not isinstance(axis, list) or len(axis) != 2 or not all(isinstance(p, list) and len(p) == 2 for p in axis):
                    add_issue(issues, "ERROR", "WALL_AXIS", "MVP wall axis must have exactly two [x,y] points.", f"{ipath}.axis")
                elif distance(axis[0], axis[1]) <= 1e-6:
                    add_issue(issues, "ERROR", "ZERO_LENGTH_WALL", "Wall axis must have positive length.", f"{ipath}.axis")
                for field in ("thickness_mm", "height_mm"):
                    if float(item.get(field, 0) or 0) <= 0:
                        add_issue(issues, "ERROR", "WALL_DIMENSION", f"{field} must be positive.", f"{ipath}.{field}")
            elif collection == "openings":
                host = wall_index.get(str(item.get("host_wall_id")))
                if not host:
                    add_issue(issues, "ERROR", "OPENING_HOST", "Opening host wall does not exist on this storey.", f"{ipath}.host_wall_id")
                    continue
                wall_length = distance(host["axis"][0], host["axis"][1])
                offset = float(item.get("offset_mm", -1) or 0)
                width = float(item.get("width_mm", 0) or 0)
                sill = float(item.get("sill_mm", -1) or 0)
                opening_height = float(item.get("height_mm", 0) or 0)
                wall_height = float(host.get("height_mm", 0) or 0)
                if offset < 0 or width <= 0 or offset + width > wall_length + 1e-6:
                    add_issue(issues, "ERROR", "OPENING_HORIZONTAL_FIT", "Opening must fit within host wall length.", ipath)
                if sill < 0 or opening_height <= 0 or sill + opening_height > wall_height + 1e-6:
                    add_issue(issues, "ERROR", "OPENING_VERTICAL_FIT", "Opening must fit within host wall height.", ipath)
            elif collection == "columns":
                if not (isinstance(item.get("center"), list) and len(item["center"]) == 2):
                    add_issue(issues, "ERROR", "COLUMN_CENTER", "Column center must be [x,y].", f"{ipath}.center")
                for field in ("width_mm", "depth_mm", "height_mm"):
                    if float(item.get(field, 0) or 0) <= 0:
                        add_issue(issues, "ERROR", "COLUMN_DIMENSION", f"{field} must be positive.", f"{ipath}.{field}")
            elif collection == "beams":
                axis = item.get("axis")
                if not isinstance(axis, list) or len(axis) != 2 or distance(axis[0], axis[1]) <= 1e-6:
                    add_issue(issues, "ERROR", "BEAM_AXIS", "Beam needs a positive two-point axis.", f"{ipath}.axis")
                for field in ("width_mm", "depth_mm"):
                    if float(item.get(field, 0) or 0) <= 0:
                        add_issue(issues, "ERROR", "BEAM_DIMENSION", f"{field} must be positive.", f"{ipath}.{field}")

    for current, following in zip(sorted(storey_z), sorted(storey_z)[1:]):
        if following[0] < current[1] - 1e-6:
            add_issue(issues, "WARNING", "STOREY_VERTICAL_OVERLAP", f"{current[2]} overlaps vertically with {following[2]}.", "storeys")

    legal = model.get("legal_constraints", {}) if isinstance(model.get("legal_constraints", {}), dict) else {}
    sources = legal.get("sources", []) if isinstance(legal.get("sources", []), list) else []
    source_ids = {str(s.get("id")) for s in sources if isinstance(s, dict) and s.get("id")}
    claimed_ids = {str(x) for x in legal.get("constraint_source_ids", [])}
    sources_verified = bool(claimed_ids) and claimed_ids.issubset(source_ids)
    if any(legal.get(key) is not None for key in ("building_coverage_max_percent", "floor_area_ratio_max_percent", "max_height_mm", "uniform_setback_mm")) and not sources_verified:
        add_issue(issues, "WARNING", "LEGAL_SOURCE_UNVERIFIED", "Numeric legal constraints lack complete source IDs; results are screening-only.", "legal_constraints")
    for index, source in enumerate(sources):
        missing = [field for field in ("id", "authority", "title", "version", "locator", "url_or_file") if not source.get(field)]
        if missing:
            add_issue(issues, "WARNING", "LEGAL_SOURCE_INCOMPLETE", f"Source is missing: {', '.join(missing)}.", f"legal_constraints.sources[{index}]")

    metrics = calculate_metrics(model)
    checks = [
        constraint_check("building_coverage", metrics["building_coverage_percent"], legal.get("building_coverage_max_percent"), "percent", sources_verified),
        constraint_check("floor_area_ratio", metrics["floor_area_ratio_percent"], legal.get("floor_area_ratio_max_percent"), "percent", sources_verified),
        constraint_check("modeled_height", metrics["modeled_height_mm"], legal.get("max_height_mm"), "mm", sources_verified),
    ]

    setback = legal.get("uniform_setback_mm")
    if setback is None:
        checks.append({"name": "uniform_setback", "status": "NOT_PROVIDED", "actual": None, "limit": None, "units": "mm"})
    elif boundary:
        slab_polys = [slab.get("polygon") for s in storeys for slab in s.get("slabs", []) if valid_polygon(slab.get("polygon"))]
        actual = min((polygon_min_boundary_distance(poly, boundary) for poly in slab_polys), default=None)
        checks.append({
            "name": "uniform_setback",
            "status": ("FAIL" if actual is not None and actual + 1e-7 < float(setback) else ("PASS" if sources_verified else "UNVERIFIED")),
            "actual": round(actual, 3) if actual is not None else None,
            "limit": float(setback),
            "units": "mm",
        })

    unresolved = model.get("unresolved", []) if isinstance(model.get("unresolved", []), list) else []
    assumptions = model.get("assumptions", []) if isinstance(model.get("assumptions", []), list) else []
    return {
        "status": "ERROR" if any(i["level"] == "ERROR" for i in issues) else ("WARNING" if issues or any(c["status"] in ("FAIL", "UNVERIFIED") for c in checks) else "PASS"),
        "legal_disclaimer": "Geometric screening only; not a legal opinion, permit approval, structural check, or final construction document.",
        "metrics": metrics,
        "checks": checks,
        "issues": issues,
        "assumptions": assumptions,
        "unresolved": unresolved,
        "required_professional_reviews": ["architecture/planning", "structure", "fire/life safety", "accessibility", "MEP coordination", "survey/geotechnical"],
    }


def review_markdown(model: dict[str, Any], report: dict[str, Any]) -> str:
    project = model.get("project", {})
    lines = [
        f"# Review report — {project.get('title', 'Untitled project')}",
        "",
        f"**Pipeline status:** {report['status']}",
        "",
        "> Geometric screening and drafting assistance only. This is not a legal opinion, permit approval, structural calculation, or final construction document.",
        "",
        "## Metrics",
        "",
    ]
    for key, value in report["metrics"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Constraint checks", ""])
    for check in report["checks"]:
        lines.append(f"- **{check['status']}** {check['name']}: actual {check.get('actual')} {check.get('units', '')}; limit {check.get('limit')}")
    lines.extend(["", "## Validation issues", ""])
    if report["issues"]:
        for item in report["issues"]:
            lines.append(f"- **{item['level']} {item['code']}** `{item['path']}` — {item['message']}")
    else:
        lines.append("- No schema or geometry issues detected by the MVP validator.")
    lines.extend(["", "## Assumptions", ""])
    lines.extend([f"- {x}" for x in report.get("assumptions", [])] or ["- None recorded."])
    lines.extend(["", "## Unresolved inputs", ""])
    lines.extend([f"- {x}" for x in report.get("unresolved", [])] or ["- None recorded."])
    lines.extend(["", "## Mandatory human reviews", ""])
    lines.extend(f"- {x}" for x in report["required_professional_reviews"])
    lines.extend(["", "Generated artifacts must remain labeled concept, preliminary, or construction-drawing assistance until approved by the responsible professionals.", ""])
    return "\n".join(lines)


def run_validation(model_path: Path, output_dir: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    model = read_json(model_path)
    report = validate_model(model)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "metrics.json", report["metrics"])
    write_json(output_dir / "validation_report.json", report)
    (output_dir / "review_report.md").write_text(review_markdown(model, report), encoding="utf-8")
    return model, report


def yaml_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(str(value), ensure_ascii=False)


def yaml_lines(value: Any, indent: int = 0) -> list[str]:
    pad = " " * indent
    if isinstance(value, dict):
        out: list[str] = []
        for key, item in value.items():
            if isinstance(item, (dict, list)) and item:
                out.append(f"{pad}{key}:")
                out.extend(yaml_lines(item, indent + 2))
            elif isinstance(item, (dict, list)):
                out.append(f"{pad}{key}: {'{}' if isinstance(item, dict) else '[]'}")
            else:
                out.append(f"{pad}{key}: {yaml_scalar(item)}")
        return out
    if isinstance(value, list):
        out = []
        for item in value:
            if isinstance(item, dict):
                if not item:
                    out.append(f"{pad}- {{}}")
                else:
                    first, *rest = item.items()
                    key, val = first
                    if isinstance(val, (dict, list)):
                        out.append(f"{pad}- {key}:")
                        out.extend(yaml_lines(val, indent + 4))
                    else:
                        out.append(f"{pad}- {key}: {yaml_scalar(val)}")
                    for rkey, rval in rest:
                        if isinstance(rval, (dict, list)):
                            out.append(f"{pad}  {rkey}:")
                            out.extend(yaml_lines(rval, indent + 4))
                        else:
                            out.append(f"{pad}  {rkey}: {yaml_scalar(rval)}")
            else:
                out.append(f"{pad}- {yaml_scalar(item)}")
        return out
    return [f"{pad}{yaml_scalar(value)}"]


def extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in (".txt", ".md", ".yaml", ".yml"):
        return path.read_text(encoding="utf-8-sig")
    if suffix == ".json":
        return json.dumps(read_json(path), ensure_ascii=False)
    if suffix == ".docx":
        with zipfile.ZipFile(path) as archive:
            xml = archive.read("word/document.xml")
        root = ElementTree.fromstring(xml)
        return "\n".join(node.text or "" for node in root.iter() if node.tag.endswith("}t"))
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader  # type: ignore
        except ImportError as exc:
            raise RuntimeError("PDF extraction requires pypdf. Install it or provide TXT/DOCX.") from exc
        return "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)
    raise ValueError(f"Unsupported requirements file: {path.suffix}")


def first_number(text: str, patterns: Iterable[str]) -> float | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return float(match.group(1))
    return None


def parse_requirements(path: Path) -> dict[str, Any]:
    text = extract_text(path)
    floors = first_number(text, (r"(?:floors?|storeys?)\s*[:：]?\s*(\d+)", r"(\d+)\s*层"))
    site_area = first_number(text, (r"(?:site|plot)\s*area\s*[:：]?\s*([\d.]+)", r"(?:敷地|用地|基地)面积\s*[:：]?\s*([\d.]+)"))
    target_area = first_number(text, (r"target\s*floor\s*area\s*[:：]?\s*([\d.]+)", r"(?:目标|计划)?(?:建筑|延床|总建筑)面积\s*[:：]?\s*([\d.]+)"))
    bcr = first_number(text, (r"(?:building\s*coverage|BCR)\s*[:：]?\s*([\d.]+)", r"建[蔽ぺ]率\s*[:：]?\s*([\d.]+)"))
    far = first_number(text, (r"(?:floor\s*area\s*ratio|FAR)\s*[:：]?\s*([\d.]+)", r"容积率\s*[:：]?\s*([\d.]+)"))
    height_m = first_number(text, (r"max(?:imum)?\s*height\s*[:：]?\s*([\d.]+)\s*m", r"(?:最高|最大)?高度\s*[:：]?\s*([\d.]+)\s*m"))
    road_width_m = first_number(text, (r"road\s*width\s*[:：]?\s*([\d.]+)\s*m", r"道路幅(?:员|員)?\s*[:：]?\s*([\d.]+)\s*m"))
    bedrooms = first_number(text, (r"(\d+)\s*bedrooms?", r"(?:卧室|寝室)\s*[:：]?\s*(\d+)"))
    parking = first_number(text, (r"(\d+)\s*parking", r"停车(?:位|台数)?\s*[:：]?\s*(\d+)"))
    structure = None
    for token, normalized in (("RC", "rc"), ("reinforced concrete", "rc"), ("木造", "wood"), ("wood", "wood"), ("steel", "steel"), ("钢结构", "steel")):
        if token.lower() in text.lower():
            structure = normalized
            break
    use = "detached_house" if any(token in text.lower() for token in ("住宅", "house", "residential")) else None
    data = {
        "project": {
            "source_file": str(path.resolve()),
            "mode": "preliminary",
            "use": use,
            "structure_intent": structure,
            "floors": int(floors) if floors is not None else None,
            "site_area_m2_text_claim": site_area,
            "target_floor_area_m2": target_area,
        },
        "design_constraints": {"bedrooms": int(bedrooms) if bedrooms is not None else None, "parking_spaces": int(parking) if parking is not None else None},
        "legal_constraints": {
            "building_coverage_max_percent": bcr,
            "floor_area_ratio_max_percent": far,
            "max_height_mm": height_m * 1000 if height_m is not None else None,
            "road_width_mm": road_width_m * 1000 if road_width_m is not None else None,
            "sources": [],
            "constraint_source_ids": [],
        },
        "extraction": {
            "status": "UNVERIFIED_HEURISTIC",
            "instruction": "Review every value against the source and add exact legal source locators before use.",
        },
    }
    return data


def dxf_pair(code: int, value: Any) -> str:
    return f"{code}\n{value}\n"


def dxf_polyline(layer: str, points: list[list[float]], closed: bool = True) -> str:
    out = dxf_pair(0, "LWPOLYLINE") + dxf_pair(100, "AcDbEntity") + dxf_pair(8, layer) + dxf_pair(100, "AcDbPolyline")
    out += dxf_pair(90, len(points)) + dxf_pair(70, 1 if closed else 0)
    for x, y in points:
        out += dxf_pair(10, f"{x:.6f}") + dxf_pair(20, f"{y:.6f}")
    return out


def dxf_text(layer: str, point: list[float], height: float, text: str) -> str:
    clean = "".join(char if 32 <= ord(char) < 127 else f"\\U+{ord(char):04X}" for char in str(text).replace("\n", " "))
    return dxf_pair(0, "TEXT") + dxf_pair(100, "AcDbEntity") + dxf_pair(8, layer) + dxf_pair(100, "AcDbText") + dxf_pair(10, point[0]) + dxf_pair(20, point[1]) + dxf_pair(40, height) + dxf_pair(1, clean)


def axis_rectangle(axis: list[list[float]], width: float) -> list[list[float]]:
    a, b = axis
    length = distance(a, b)
    nx, ny = -(b[1] - a[1]) / length * width / 2.0, (b[0] - a[0]) / length * width / 2.0
    return [[a[0] + nx, a[1] + ny], [b[0] + nx, b[1] + ny], [b[0] - nx, b[1] - ny], [a[0] - nx, a[1] - ny]]


def rect_at(center: list[float], width: float, depth: float) -> list[list[float]]:
    x, y = center
    return [[x - width / 2, y - depth / 2], [x + width / 2, y - depth / 2], [x + width / 2, y + depth / 2], [x - width / 2, y + depth / 2]]


def centroid(points: list[list[float]]) -> list[float]:
    return [sum(p[0] for p in points) / len(points), sum(p[1] for p in points) / len(points)]


def inset_rectangle(points: list[list[float]], inset: float) -> list[list[float]] | None:
    xs, ys = sorted({float(p[0]) for p in points}), sorted({float(p[1]) for p in points})
    if len(points) == 4 and len(xs) == 2 and len(ys) == 2 and xs[1] - xs[0] > 2 * inset and ys[1] - ys[0] > 2 * inset:
        return [[xs[0] + inset, ys[0] + inset], [xs[1] - inset, ys[0] + inset], [xs[1] - inset, ys[1] - inset], [xs[0] + inset, ys[1] - inset]]
    return None


def generate_dxf(model: dict[str, Any], output: Path, layer_map: dict[str, Any]) -> None:
    entities: list[str] = []
    layers: dict[str, int] = {}

    def add(layer: str, entity: str, aci: int) -> None:
        layers[layer] = aci
        entities.append(entity)

    site = model.get("site", {})
    boundary = site.get("boundary", [])
    if valid_polygon(boundary):
        lm = layer_map["site_boundary"]
        add(lm["pattern"], dxf_polyline(lm["pattern"], boundary), lm["aci"])
        setback = model.get("legal_constraints", {}).get("uniform_setback_mm")
        inset = inset_rectangle(boundary, float(setback)) if setback is not None else None
        if inset:
            lm = layer_map["legal_setback"]
            add(lm["pattern"], dxf_polyline(lm["pattern"], inset), lm["aci"])
    for road in site.get("roads", []):
        if isinstance(road.get("edge"), list) and len(road["edge"]) >= 2:
            lm = layer_map["site_road"]
            add(lm["pattern"], dxf_polyline(lm["pattern"], road["edge"], False), lm["aci"])

    for storey in model.get("storeys", []):
        sid = safe_name(storey.get("id"))
        for slab in storey.get("slabs", []):
            lm = layer_map["slab"]
            layer = lm["pattern"].format(storey=sid)
            add(layer, dxf_polyline(layer, slab["polygon"]), lm["aci"])
        for space in storey.get("spaces", []):
            lm = layer_map["zone"]
            layer = lm["pattern"].format(storey=sid, usage=safe_name(space.get("usage")))
            add(layer, dxf_polyline(layer, space["polygon"]), lm["aci"])
            anno = layer_map["annotation"]
            anno_layer = anno["pattern"].format(storey=sid)
            label = f"{space.get('name', space.get('id'))} {polygon_area(space['polygon']) / 1_000_000:.2f}m2"
            add(anno_layer, dxf_text(anno_layer, centroid(space["polygon"]), 250, label), anno["aci"])
        wall_by_id = {w["id"]: w for w in storey.get("walls", [])}
        for wall in storey.get("walls", []):
            key = "external_wall" if wall.get("type") == "external" else "internal_wall"
            lm = layer_map[key]
            layer = lm["pattern"].format(storey=sid)
            add(layer, dxf_polyline(layer, axis_rectangle(wall["axis"], float(wall["thickness_mm"]))), lm["aci"])
        for opening in storey.get("openings", []):
            wall = wall_by_id.get(opening.get("host_wall_id"))
            if not wall:
                continue
            a, b = wall["axis"]
            length = distance(a, b)
            ux, uy = (b[0] - a[0]) / length, (b[1] - a[1]) / length
            start = [a[0] + ux * float(opening["offset_mm"]), a[1] + uy * float(opening["offset_mm"])]
            end = [start[0] + ux * float(opening["width_mm"]), start[1] + uy * float(opening["width_mm"])]
            lm = layer_map[opening["type"]]
            layer = lm["pattern"].format(storey=sid)
            add(layer, dxf_polyline(layer, axis_rectangle([start, end], float(wall["thickness_mm"]) * 1.2)), lm["aci"])
        for column in storey.get("columns", []):
            lm = layer_map["column"]
            layer = lm["pattern"].format(storey=sid)
            add(layer, dxf_polyline(layer, rect_at(column["center"], float(column["width_mm"]), float(column["depth_mm"]))), lm["aci"])
        for beam in storey.get("beams", []):
            lm = layer_map["beam"]
            layer = lm["pattern"].format(storey=sid)
            add(layer, dxf_polyline(layer, axis_rectangle(beam["axis"], float(beam["width_mm"]))), lm["aci"])

    header = dxf_pair(0, "SECTION") + dxf_pair(2, "HEADER") + dxf_pair(9, "$ACADVER") + dxf_pair(1, "AC1015") + dxf_pair(9, "$INSUNITS") + dxf_pair(70, 4) + dxf_pair(0, "ENDSEC")
    tables = dxf_pair(0, "SECTION") + dxf_pair(2, "TABLES") + dxf_pair(0, "TABLE") + dxf_pair(2, "LAYER") + dxf_pair(70, len(layers))
    for layer, aci in sorted(layers.items()):
        tables += dxf_pair(0, "LAYER") + dxf_pair(100, "AcDbSymbolTableRecord") + dxf_pair(100, "AcDbLayerTableRecord") + dxf_pair(2, layer) + dxf_pair(70, 0) + dxf_pair(62, aci) + dxf_pair(6, "CONTINUOUS")
    tables += dxf_pair(0, "ENDTAB") + dxf_pair(0, "ENDSEC")
    body = dxf_pair(0, "SECTION") + dxf_pair(2, "ENTITIES") + "".join(entities) + dxf_pair(0, "ENDSEC") + dxf_pair(0, "EOF")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(header + tables + body, encoding="ascii", errors="replace")


RUBY_TEMPLATE = r'''# Generated by ArchFlow Studio. Review before running.
require 'json'
require 'fileutils'

MODEL_DATA = JSON.parse(<<~'MODELJSON')
__MODEL_JSON__
MODELJSON
MATERIAL_DATA = JSON.parse(<<~'MATERIALJSON')
__MATERIAL_JSON__
MATERIALJSON

def mm(value)
  value.to_f / 25.4
end

def material_for(model, key, explicit_hex = nil)
  name = "MAT-#{key.to_s.upcase}"
  material = model.materials[name] || model.materials.add(name)
  spec = MATERIAL_DATA[key.to_s] || MATERIAL_DATA['default']
  hex = explicit_hex || spec['hex']
  material.color = Sketchup::Color.new(hex[1,2].to_i(16), hex[3,2].to_i(16), hex[5,2].to_i(16))
  material.alpha = key.to_s == 'glass' ? 0.45 : 1.0
  material
end

def tag_for(model, name)
  model.layers[name] || model.layers.add(name)
end

def add_prism(parent, name, polygon, z_mm, height_mm, material, tag)
  group = parent.add_group
  group.name = name
  group.layer = tag
  points = polygon.map { |p| Geom::Point3d.new(mm(p[0]), mm(p[1]), mm(z_mm)) }
  face = group.entities.add_face(points)
  raise "Cannot create face for #{name}" unless face
  face.reverse! if face.normal.z < 0
  face.material = material
  face.back_material = material
  face.pushpull(mm(height_mm))
  group
end

def axis_geometry(axis, width_mm, x0_mm, x1_mm)
  a, b = axis
  length = Math.hypot(b[0] - a[0], b[1] - a[1])
  ux = (b[0] - a[0]) / length
  uy = (b[1] - a[1]) / length
  nx = -uy * width_mm / 2.0
  ny = ux * width_mm / 2.0
  p0 = [a[0] + ux * x0_mm, a[1] + uy * x0_mm]
  p1 = [a[0] + ux * x1_mm, a[1] + uy * x1_mm]
  [[p0[0] + nx, p0[1] + ny], [p1[0] + nx, p1[1] + ny], [p1[0] - nx, p1[1] - ny], [p0[0] - nx, p0[1] - ny]]
end

def add_axis_prism(parent, name, axis, width_mm, z_mm, height_mm, material, tag, x0_mm = 0.0, x1_mm = nil)
  length = Math.hypot(axis[1][0] - axis[0][0], axis[1][1] - axis[0][1])
  add_prism(parent, name, axis_geometry(axis, width_mm, x0_mm, x1_mm || length), z_mm, height_mm, material, tag)
end

def add_wall(parent, model, storey, wall, openings)
  sid = storey['id'].to_s.upcase
  tag = tag_for(model, "A-WALL-#{wall['type'].to_s.upcase}-#{sid}")
  material = material_for(model, wall['material'])
  length = Math.hypot(wall['axis'][1][0] - wall['axis'][0][0], wall['axis'][1][1] - wall['axis'][0][1])
  xs = [0.0, length]
  zs = [0.0, wall['height_mm'].to_f]
  openings.each do |opening|
    xs.concat([opening['offset_mm'].to_f, opening['offset_mm'].to_f + opening['width_mm'].to_f])
    zs.concat([opening['sill_mm'].to_f, opening['sill_mm'].to_f + opening['height_mm'].to_f])
  end
  xs = xs.uniq.sort
  zs = zs.uniq.sort
  wall_group = parent.add_group
  wall_group.name = wall['id']
  wall_group.layer = tag
  xs.each_cons(2) do |x0, x1|
    zs.each_cons(2) do |z0, z1|
      xc = (x0 + x1) / 2.0
      zc = (z0 + z1) / 2.0
      blocked = openings.any? do |opening|
        xc > opening['offset_mm'].to_f && xc < opening['offset_mm'].to_f + opening['width_mm'].to_f &&
          zc > opening['sill_mm'].to_f && zc < opening['sill_mm'].to_f + opening['height_mm'].to_f
      end
      next if blocked || x1 <= x0 || z1 <= z0
      add_axis_prism(wall_group.entities, "#{wall['id']}-X#{x0.round}-Z#{z0.round}", wall['axis'], wall['thickness_mm'].to_f,
                     storey['z_mm'].to_f + wall.fetch('base_offset_mm', 0).to_f + z0,
                     z1 - z0, material, tag, x0, x1)
    end
  end
  wall_group
end

def add_opening_panel(parent, model, storey, wall, opening)
  axis = wall['axis']
  length = Math.hypot(axis[1][0] - axis[0][0], axis[1][1] - axis[0][1])
  ux = (axis[1][0] - axis[0][0]) / length
  uy = (axis[1][1] - axis[0][1]) / length
  x0 = opening['offset_mm'].to_f
  x1 = x0 + opening['width_mm'].to_f
  p0 = [axis[0][0] + ux * x0, axis[0][1] + uy * x0]
  p1 = [axis[0][0] + ux * x1, axis[0][1] + uy * x1]
  z0 = storey['z_mm'].to_f + wall.fetch('base_offset_mm', 0).to_f + opening['sill_mm'].to_f
  z1 = z0 + opening['height_mm'].to_f
  group = parent.add_group
  group.name = opening['id']
  group.layer = tag_for(model, "A-OPEN-#{opening['type'].to_s.upcase}-#{storey['id'].to_s.upcase}")
  points = [Geom::Point3d.new(mm(p0[0]), mm(p0[1]), mm(z0)), Geom::Point3d.new(mm(p1[0]), mm(p1[1]), mm(z0)),
            Geom::Point3d.new(mm(p1[0]), mm(p1[1]), mm(z1)), Geom::Point3d.new(mm(p0[0]), mm(p0[1]), mm(z1))]
  face = group.entities.add_face(points)
  if face
    mat = material_for(model, opening.fetch('material', opening['type'] == 'window' ? 'glass' : 'wood'))
    face.material = mat
    face.back_material = mat
  end
  group
end

def create_scene(model, name, eye, target, up, perspective)
  model.active_view.camera = Sketchup::Camera.new(eye, target, up, perspective)
  model.active_view.zoom_extents
  page = model.pages.to_a.find { |candidate| candidate.name == name } || model.pages.add(name)
  page.update(PAGE_USE_CAMERA)
  page
end

def create_and_export_scenes(model, output_dir)
  bounds = model.bounds
  center = bounds.center
  span = [bounds.width, bounds.height, bounds.depth, 1000.mm].max * 2.5
  scenes = {
    'Front' => [Geom::Point3d.new(center.x, center.y - span, center.z), center, Z_AXIS, false],
    'Right' => [Geom::Point3d.new(center.x + span, center.y, center.z), center, Z_AXIS, false],
    'Top' => [Geom::Point3d.new(center.x, center.y, center.z + span), center, Y_AXIS, false],
    'Axon' => [Geom::Point3d.new(center.x + span, center.y - span, center.z + span), center, Z_AXIS, true]
  }
  FileUtils.mkdir_p(output_dir)
  scenes.each do |name, values|
    page = create_scene(model, name, *values)
    model.pages.selected_page = page
    model.active_view.zoom_extents
    model.active_view.write_image(filename: File.join(output_dir, "#{name.downcase}.png"), width: 2000, height: 1600, antialias: true, transparent: false)
  end
end

model = Sketchup.active_model
model.start_operation('Codex semantic building model', true)
begin
  root = model.entities.add_group
  root.name = "CODEX-#{MODEL_DATA.dig('project', 'id')}"
  MODEL_DATA['storeys'].each do |storey|
    storey_group = root.entities.add_group
    storey_group.name = "STOREY-#{storey['id']}"
    storey_group.layer = tag_for(model, "STOREY-#{storey['id'].to_s.upcase}")

    storey.fetch('slabs', []).each do |slab|
      tag = tag_for(model, "A-SLAB-#{storey['id'].to_s.upcase}")
      add_prism(storey_group.entities, slab['id'], slab['polygon'], storey['z_mm'].to_f + slab.fetch('base_offset_mm', 0).to_f,
                slab['thickness_mm'].to_f, material_for(model, slab['material']), tag)
    end
    storey.fetch('spaces', []).each do |space|
      tag = tag_for(model, "A-ZONE-#{space['usage'].to_s.upcase}-#{storey['id'].to_s.upcase}")
      add_prism(storey_group.entities, space['id'], space['polygon'], storey['z_mm'].to_f + 5.0, 5.0,
                material_for(model, space.fetch('material', space['usage']), space['color']), tag)
    end
    walls = storey.fetch('walls', [])
    wall_index = walls.map { |wall| [wall['id'], wall] }.to_h
    walls.each do |wall|
      openings = storey.fetch('openings', []).select { |opening| opening['host_wall_id'] == wall['id'] }
      add_wall(storey_group.entities, model, storey, wall, openings)
    end
    storey.fetch('openings', []).each do |opening|
      wall = wall_index[opening['host_wall_id']]
      add_opening_panel(storey_group.entities, model, storey, wall, opening) if wall
    end
    storey.fetch('columns', []).each do |column|
      x, y = column['center']
      polygon = [[x - column['width_mm']/2.0, y - column['depth_mm']/2.0], [x + column['width_mm']/2.0, y - column['depth_mm']/2.0],
                 [x + column['width_mm']/2.0, y + column['depth_mm']/2.0], [x - column['width_mm']/2.0, y + column['depth_mm']/2.0]]
      tag = tag_for(model, "S-COLUMN-#{storey['id'].to_s.upcase}")
      add_prism(storey_group.entities, column['id'], polygon, storey['z_mm'].to_f + column.fetch('base_offset_mm', 0).to_f,
                column['height_mm'].to_f, material_for(model, column['material']), tag)
    end
    storey.fetch('beams', []).each do |beam|
      tag = tag_for(model, "S-BEAM-#{storey['id'].to_s.upcase}")
      add_axis_prism(storey_group.entities, beam['id'], beam['axis'], beam['width_mm'].to_f,
                     storey['z_mm'].to_f + beam['base_offset_mm'].to_f, beam['depth_mm'].to_f,
                     material_for(model, beam['material']), tag)
    end
  end
  output_dir = File.join(File.dirname(__FILE__), 'sketchup_views')
  create_and_export_scenes(model, output_dir)
  model.commit_operation
  UI.messagebox("Semantic model created. Review groups, tags, openings, scenes, and exported images.\n#{output_dir}")
rescue => error
  model.abort_operation
  UI.messagebox("Generation failed: #{error.message}\n#{error.backtrace.first(5).join("\n")}")
  raise
end
'''


def generate_sketchup(model: dict[str, Any], output: Path, material_map: dict[str, Any]) -> None:
    content = RUBY_TEMPLATE.replace("__MODEL_JSON__", json.dumps(model, ensure_ascii=False, indent=2)).replace("__MATERIAL_JSON__", json.dumps(material_map, ensure_ascii=False, indent=2))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")


def generate_prompts(model: dict[str, Any], output_dir: Path, material_map: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    used = sorted({str(item.get("material")) for storey in model.get("storeys", []) for collection in ("spaces", "slabs", "walls", "openings", "columns", "beams") for item in storey.get(collection, []) if item.get("material")})
    palette = [f"{key}: {material_map.get(key, material_map['default']).get('render')} ({material_map.get(key, material_map['default']).get('hex')})" for key in used]
    project = model.get("project", {})
    views = {
        "front": "orthographic front elevation looking toward positive Y",
        "right": "orthographic right elevation looking toward negative X",
        "top": "orthographic top/plan view",
        "axon": "bird-eye axonometric perspective showing front and right sides",
    }
    manifest = {"project_id": project.get("id"), "creative_assumptions": ["lighting, weather, landscaping, and context are unspecified unless supplied separately"], "views": []}
    negative = "Do not change the camera, site boundary, footprint, floor count, roof silhouette, wall positions, openings, structural grid, or adjacent-site geometry. Do not invent unsupported construction details."
    for key, camera in views.items():
        prompt = (
            f"Architectural visualization based strictly on the supplied line image: {camera}. "
            f"Project: {project.get('title')}, use {project.get('use')}, {len(model.get('storeys', []))} modeled storeys, mode {project.get('mode')}. "
            f"Preserve geometry exactly. Material intent: {'; '.join(palette) if palette else 'neutral architectural materials'}. "
            "Use restrained natural daylight and a clear professional architectural presentation; lighting and landscape are creative assumptions. "
            + negative
        )
        (output_dir / f"{key}.txt").write_text(prompt + "\n", encoding="utf-8")
        manifest["views"].append({"id": key, "camera": camera, "line_image": f"../sketchup_views/{key}.png", "prompt_file": f"{key}.txt", "prompt": prompt})
    write_json(output_dir / "manifest.json", manifest)


def command_parse(args: argparse.Namespace) -> int:
    data = parse_requirements(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(yaml_lines(data)) + "\n", encoding="utf-8")
    print(f"Wrote heuristic, unverified extraction: {args.output}")
    return 0


def command_validate(args: argparse.Namespace) -> int:
    _, report = run_validation(args.model, args.output_dir)
    print(f"Validation status: {report['status']}")
    print(f"Reports: {args.output_dir}")
    return 2 if report["status"] == "ERROR" else 0


def command_dxf(args: argparse.Namespace) -> int:
    model = read_json(args.model)
    report = validate_model(model)
    if report["status"] == "ERROR":
        print("Refusing DXF generation because validation has errors.", file=sys.stderr)
        return 2
    generate_dxf(model, args.output, read_json(args.layer_map))
    print(f"Wrote DXF: {args.output}")
    return 0


def command_sketchup(args: argparse.Namespace) -> int:
    model = read_json(args.model)
    report = validate_model(model)
    if report["status"] == "ERROR":
        print("Refusing SketchUp generation because validation has errors.", file=sys.stderr)
        return 2
    generate_sketchup(model, args.output, read_json(args.material_map))
    print(f"Wrote inspectable SketchUp Ruby script: {args.output}")
    return 0


def command_prompts(args: argparse.Namespace) -> int:
    model = read_json(args.model)
    report = validate_model(model)
    if report["status"] == "ERROR":
        print("Refusing prompt generation because validation has errors.", file=sys.stderr)
        return 2
    generate_prompts(model, args.output_dir, read_json(args.material_map))
    print(f"Wrote render prompt manifest: {args.output_dir}")
    return 0


def command_all(args: argparse.Namespace) -> int:
    model, report = run_validation(args.model, args.output_dir)
    if report["status"] == "ERROR":
        print("Validation failed; reports were written but downstream generation was stopped.", file=sys.stderr)
        return 2
    generate_dxf(model, args.output_dir / "semantic_plans.dxf", read_json(args.layer_map))
    generate_sketchup(model, args.output_dir / "build_model.rb", read_json(args.material_map))
    generate_prompts(model, args.output_dir / "render_prompts", read_json(args.material_map))
    print(f"Pipeline complete with status {report['status']}: {args.output_dir}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate a semantic building model and generate reviewable CAD/SketchUp drafts.")
    sub = parser.add_subparsers(dest="command", required=True)

    parse = sub.add_parser("parse-requirements", help="Heuristically extract requirements to reviewable YAML.")
    parse.add_argument("input", type=Path)
    parse.add_argument("--output", type=Path, required=True)
    parse.set_defaults(func=command_parse)

    validate = sub.add_parser("validate", help="Validate schema, geometry, and screening constraints.")
    validate.add_argument("model", type=Path)
    validate.add_argument("--output-dir", type=Path, required=True)
    validate.set_defaults(func=command_validate)

    dxf = sub.add_parser("generate-dxf", help="Generate a new semantic-layer ASCII DXF.")
    dxf.add_argument("model", type=Path)
    dxf.add_argument("--output", type=Path, required=True)
    dxf.add_argument("--layer-map", type=Path, default=DEFAULT_LAYER_MAP)
    dxf.set_defaults(func=command_dxf)

    sketchup = sub.add_parser("generate-sketchup", help="Generate an inspectable SketchUp Ruby modeling script.")
    sketchup.add_argument("model", type=Path)
    sketchup.add_argument("--output", type=Path, required=True)
    sketchup.add_argument("--material-map", type=Path, default=DEFAULT_MATERIAL_MAP)
    sketchup.set_defaults(func=command_sketchup)

    prompts = sub.add_parser("generate-prompts", help="Generate view-specific rendering prompts.")
    prompts.add_argument("model", type=Path)
    prompts.add_argument("--output-dir", type=Path, required=True)
    prompts.add_argument("--material-map", type=Path, default=DEFAULT_MATERIAL_MAP)
    prompts.set_defaults(func=command_prompts)

    all_cmd = sub.add_parser("all", help="Validate then generate reports, DXF, SketchUp Ruby, and prompts.")
    all_cmd.add_argument("model", type=Path)
    all_cmd.add_argument("--output-dir", type=Path, required=True)
    all_cmd.add_argument("--layer-map", type=Path, default=DEFAULT_LAYER_MAP)
    all_cmd.add_argument("--material-map", type=Path, default=DEFAULT_MATERIAL_MAP)
    all_cmd.set_defaults(func=command_all)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return int(args.func(args))
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
