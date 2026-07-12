#!/usr/bin/env python3
"""Create, archive, and verify official-source legal evidence bundles."""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


INDEX_NAME = "legal_evidence.json"
OFFICIAL_HOSTS = {"laws.e-gov.go.jp", "www.mlit.go.jp", "mlit.go.jp", "www.reinfolib.mlit.go.jp"}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def safe_id(value: str) -> str:
    result = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-")
    if not result:
        raise ValueError("Evidence id must contain a letter or number")
    return result


def official_url(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    host = (parsed.hostname or "").lower()
    return parsed.scheme == "https" and (host in OFFICIAL_HOSTS or host.endswith(".go.jp") or host.endswith(".lg.jp"))


def load_bundle(root: Path) -> dict[str, Any]:
    path = root / INDEX_NAME
    if not path.is_file():
        raise ValueError(f"Evidence bundle not initialized: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Evidence index must be a JSON object")
    return value


def command_init(args: argparse.Namespace) -> int:
    root = args.output_dir.resolve()
    path = root / INDEX_NAME
    if path.exists():
        raise ValueError(f"Evidence bundle already exists: {path}")
    bundle = {
        "schema_version": "0.1",
        "jurisdiction": args.jurisdiction,
        "design_effective_date": args.effective_date,
        "created_at": now(),
        "status": "UNVERIFIED",
        "sources": [],
        "unresolved": [
            "Confirm the authority having jurisdiction and local ordinances.",
            "Confirm every applied rule with an exact article, page, map legend, or clause.",
        ],
    }
    write_json(path, bundle)
    print(path)
    return 0


def extension(content_type: str, url: str) -> str:
    guessed = mimetypes.guess_extension(content_type.split(";", 1)[0].strip())
    if guessed:
        return guessed
    suffix = Path(urllib.parse.urlparse(url).path).suffix
    return suffix if suffix and len(suffix) <= 8 else ".bin"


def command_fetch(args: argparse.Namespace) -> int:
    if not official_url(args.url):
        raise ValueError("Refusing non-official or non-HTTPS URL; use e-Gov, go.jp, or lg.jp sources")
    root = args.bundle.resolve()
    bundle = load_bundle(root)
    evidence_id = safe_id(args.id)
    request = urllib.request.Request(args.url, headers={"User-Agent": "ArchFlow-Studio/0.1 evidence-archiver"})
    with urllib.request.urlopen(request, timeout=args.timeout) as response:
        content = response.read(args.max_bytes + 1)
        if len(content) > args.max_bytes:
            raise ValueError(f"Source exceeds --max-bytes ({args.max_bytes})")
        content_type = response.headers.get("Content-Type", "application/octet-stream")
        final_url = response.geturl()
    if not official_url(final_url):
        raise ValueError(f"Official URL redirected to a non-official host: {final_url}")

    source_dir = root / "sources"
    source_dir.mkdir(parents=True, exist_ok=True)
    output = source_dir / f"{evidence_id}{extension(content_type, final_url)}"
    output.write_bytes(content)
    record = {
        "id": evidence_id,
        "authority": args.authority,
        "title": args.title,
        "jurisdiction": bundle["jurisdiction"],
        "version": args.version,
        "effective_date": args.effective_date,
        "locator": args.locator,
        "url": final_url,
        "retrieved_at": now(),
        "content_type": content_type,
        "file": output.relative_to(root).as_posix(),
        "sha256": sha256(output),
        "verification": "PENDING_HUMAN_REVIEW",
    }
    sources = [item for item in bundle.get("sources", []) if item.get("id") != evidence_id]
    sources.append(record)
    bundle["sources"] = sources
    bundle["updated_at"] = now()
    write_json(root / INDEX_NAME, bundle)
    print(json.dumps(record, ensure_ascii=False, indent=2))
    return 0


def command_verify(args: argparse.Namespace) -> int:
    root = args.bundle.resolve()
    bundle = load_bundle(root)
    issues = []
    required = ("id", "authority", "title", "effective_date", "locator", "url", "file", "sha256")
    seen = set()
    for index, source in enumerate(bundle.get("sources", [])):
        for field in required:
            if not source.get(field):
                issues.append(f"sources[{index}].{field} is missing")
        if source.get("id") in seen:
            issues.append(f"duplicate source id: {source.get('id')}")
        seen.add(source.get("id"))
        path = (root / source.get("file", "")).resolve()
        try:
            path.relative_to(root)
        except ValueError:
            issues.append(f"source path escapes bundle: {source.get('file')}")
            continue
        if not path.is_file():
            issues.append(f"source file missing: {source.get('file')}")
        elif sha256(path) != source.get("sha256"):
            issues.append(f"source hash mismatch: {source.get('file')}")
        if source.get("url") and not official_url(source["url"]):
            issues.append(f"source URL is not recognized as official: {source.get('url')}")
    source_count = len(bundle.get("sources", []))
    status = "INVALID" if issues else ("VALID" if source_count else "UNVERIFIED")
    report = {"status": status, "source_count": source_count, "issues": issues}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not issues else 2


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Archive official legal sources with reproducible evidence metadata.")
    commands = root.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init")
    init.add_argument("--jurisdiction", required=True)
    init.add_argument("--effective-date", required=True)
    init.add_argument("--output-dir", type=Path, required=True)
    init.set_defaults(func=command_init)
    fetch = commands.add_parser("fetch")
    fetch.add_argument("--bundle", type=Path, required=True)
    fetch.add_argument("--id", required=True)
    fetch.add_argument("--authority", required=True)
    fetch.add_argument("--title", required=True)
    fetch.add_argument("--version", default="current at retrieval")
    fetch.add_argument("--effective-date", required=True)
    fetch.add_argument("--locator", required=True)
    fetch.add_argument("--url", required=True)
    fetch.add_argument("--timeout", type=int, default=30)
    fetch.add_argument("--max-bytes", type=int, default=50_000_000)
    fetch.set_defaults(func=command_fetch)
    verify = commands.add_parser("verify")
    verify.add_argument("--bundle", type=Path, required=True)
    verify.set_defaults(func=command_verify)
    return root


def main() -> int:
    try:
        args = parser().parse_args()
        return int(args.func(args))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
