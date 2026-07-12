#!/usr/bin/env python3
"""Generate a deterministic SPDX 2.3 JSON file inventory for a release payload."""

from __future__ import annotations

import argparse
import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    files = []
    relationships = []
    for index, path in enumerate(sorted(item for item in root.rglob("*") if item.is_file()), start=1):
        spdx_id = f"SPDXRef-File-{index}"
        files.append(
            {
                "SPDXID": spdx_id,
                "fileName": "./" + path.relative_to(root).as_posix(),
                "checksums": [{"algorithm": "SHA256", "checksumValue": sha256(path)}],
                "licenseConcluded": "NOASSERTION",
                "copyrightText": "NOASSERTION",
            }
        )
        relationships.append({"spdxElementId": "SPDXRef-Package", "relationshipType": "CONTAINS", "relatedSpdxElement": spdx_id})
    namespace_seed = f"{args.name}:{args.version}:" + ":".join(item["checksums"][0]["checksumValue"] for item in files)
    document = {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": f"{args.name}-{args.version}",
        "documentNamespace": f"https://archflow.best/spdx/{uuid.uuid5(uuid.NAMESPACE_URL, namespace_seed)}",
        "creationInfo": {"created": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"), "creators": ["Tool: ArchFlow-SBOM-0.1"]},
        "packages": [
            {
                "name": args.name,
                "SPDXID": "SPDXRef-Package",
                "versionInfo": args.version,
                "downloadLocation": "NOASSERTION",
                "filesAnalyzed": True,
                "licenseConcluded": "Apache-2.0",
                "licenseDeclared": "Apache-2.0",
                "copyrightText": "Copyright OHDESIGN",
            }
        ],
        "files": files,
        "relationships": relationships,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
