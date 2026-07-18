from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .pipeline import discover_core_skill, doctor, last_status, pretty_json, run_project
from .project import ProjectError, create_project, project_root, read_json, validate_manifest


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="archflow", description="Traceable CAD-to-SketchUp workflow orchestration.")
    commands = root.add_subparsers(dest="command", required=True)

    doctor_cmd = commands.add_parser("doctor", help="Check local workflow capabilities without changing CAD or SketchUp.")
    doctor_cmd.add_argument("--core-skill")
    doctor_cmd.add_argument("--json", action="store_true")

    init_cmd = commands.add_parser("init", help="Create a portable ArchFlow project package.")
    init_cmd.add_argument("path", type=Path)
    init_cmd.add_argument("--title", required=True)
    init_cmd.add_argument("--mode", choices=["concept", "preliminary", "construction_assistance"], default="preliminary")
    init_cmd.add_argument("--core-skill")

    check_cmd = commands.add_parser("check", help="Validate a project manifest and referenced files.")
    check_cmd.add_argument("manifest", type=Path)

    run_cmd = commands.add_parser("run", help="Run an immutable parse, validation, or build job.")
    run_cmd.add_argument("manifest", type=Path)
    run_cmd.add_argument("--stage", choices=["parse", "validate", "build"], default="build")
    run_cmd.add_argument("--plan", action="store_true")
    run_cmd.add_argument("--core-skill")

    status_cmd = commands.add_parser("status", help="Show the most recent run record.")
    status_cmd.add_argument("manifest", type=Path)
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "doctor":
            result = doctor(args.core_skill)
            if args.json:
                print(pretty_json(result))
            else:
                print(f"ArchFlow doctor: {result['status']}")
                for name, item in result["capabilities"].items():
                    print(f"- {name}: {item['status']} ({item.get('path', item.get('message', ''))})")
            return 0 if result["status"] == "ready" else 1
        if args.command == "init":
            skill = discover_core_skill(args.core_skill)
            path = create_project(args.path, args.title, args.mode, skill)
            print(path)
            return 0
        if args.command == "check":
            manifest = read_json(args.manifest.resolve())
            issues = validate_manifest(manifest, project_root(args.manifest), check_files=True)
            if issues:
                print("INVALID")
                for issue in issues:
                    print(f"- {issue}")
                return 1
            print("VALID")
            return 0
        if args.command == "run":
            result = run_project(args.manifest, args.stage, args.core_skill, args.plan)
            print(pretty_json(result))
            return 0
        if args.command == "status":
            print(pretty_json(last_status(args.manifest)))
            return 0
    except ProjectError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 2
