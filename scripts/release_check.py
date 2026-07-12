#!/usr/bin/env python3
"""Enforce explicit release gates for Developer Preview and production channels."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gates", type=Path, required=True)
    parser.add_argument("--channel", choices=["developer-preview", "production"], required=True)
    args = parser.parse_args()
    data = json.loads(args.gates.read_text(encoding="utf-8"))
    blockers = []
    for gate in data.get("gates", []):
        required = args.channel in gate.get("required_for", [])
        status = gate.get("status")
        print(f"[{status}] {gate.get('id')}: {gate.get('evidence')}")
        if required and status != "PASS":
            blockers.append(gate.get("id"))
    if blockers:
        print(f"RELEASE BLOCKED for {args.channel}: {', '.join(blockers)}")
        return 2
    print(f"RELEASE READY for {args.channel}: {data.get('product_version')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
