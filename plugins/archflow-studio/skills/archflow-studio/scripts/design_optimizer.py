#!/usr/bin/env python3
"""Compare immutable ArchFlow runs against explicit quantitative objectives."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def run_data(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    metrics = read_json(root / "metrics.json")
    validation = read_json(root / "validation_report.json")
    return metrics, validation


def gate_report(validation: dict[str, Any], objectives: dict[str, Any]) -> dict[str, Any]:
    reasons = []
    if objectives.get("require_no_validation_errors", True) and validation.get("status") == "ERROR":
        reasons.append("validation status is ERROR")
    checks = validation.get("checks", [])
    if objectives.get("require_no_failed_checks", True):
        failed = [check.get("name", "unknown") for check in checks if check.get("status") == "FAIL"]
        if failed:
            reasons.append("failed checks: " + ", ".join(failed))
    if objectives.get("require_verified_legal_checks", False):
        unverified = [check.get("name", "unknown") for check in checks if check.get("status") == "UNVERIFIED"]
        if unverified:
            reasons.append("unverified checks: " + ", ".join(unverified))
    return {"passed": not reasons, "reasons": reasons}


def objective_delta(objective: dict[str, Any], baseline: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    metric = objective.get("metric")
    before = baseline.get(metric)
    after = candidate.get(metric)
    if not isinstance(before, (int, float)) or not isinstance(after, (int, float)):
        return {"id": objective.get("id"), "metric": metric, "status": "UNAVAILABLE", "baseline": before, "candidate": after, "weighted_improvement": 0.0}
    direction = objective.get("direction")
    target = objective.get("target")
    if direction == "maximize":
        raw = after - before
        scale = max(abs(before), abs(after), 1.0)
    elif direction == "minimize":
        raw = before - after
        scale = max(abs(before), abs(after), 1.0)
    elif direction == "target" and isinstance(target, (int, float)):
        raw = abs(before - target) - abs(after - target)
        scale = max(abs(before), abs(after), abs(target), 1.0)
    else:
        raise ValueError(f"Invalid objective direction/target: {objective}")
    normalized = raw / scale
    weight = float(objective.get("weight", 1.0))
    return {
        "id": objective.get("id"),
        "metric": metric,
        "direction": direction,
        "target": target,
        "baseline": before,
        "candidate": after,
        "raw_improvement": round(raw, 6),
        "normalized_improvement": round(normalized, 6),
        "weight": weight,
        "weighted_improvement": round(normalized * weight, 6),
        "status": "IMPROVED" if raw > 0 else ("UNCHANGED" if raw == 0 else "WORSE"),
    }


def compare(baseline_root: Path, candidate_root: Path, objectives_path: Path) -> dict[str, Any]:
    objectives = read_json(objectives_path)
    baseline_metrics, baseline_validation = run_data(baseline_root)
    candidate_metrics, candidate_validation = run_data(candidate_root)
    baseline_gate = gate_report(baseline_validation, objectives)
    candidate_gate = gate_report(candidate_validation, objectives)
    deltas = [objective_delta(item, baseline_metrics, candidate_metrics) for item in objectives.get("objectives", [])]
    score = round(sum(item["weighted_improvement"] for item in deltas), 6)
    selected = "candidate" if candidate_gate["passed"] and (not baseline_gate["passed"] or score > 0) else "baseline"
    return {
        "status": "REVIEW_REQUIRED",
        "selected_quantitative_candidate": selected,
        "candidate_score": score,
        "baseline_gate": baseline_gate,
        "candidate_gate": candidate_gate,
        "objectives": deltas,
        "human_review_objectives": objectives.get("human_review_objectives", []),
        "disclaimer": "Quantitative comparison only; it is not a legal, architectural, structural, cost, or visual-quality approval.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare two ArchFlow run directories without changing either run.")
    parser.add_argument("--baseline-run", type=Path, required=True)
    parser.add_argument("--candidate-run", type=Path, required=True)
    parser.add_argument("--objectives", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        report = compare(args.baseline_run.resolve(), args.candidate_run.resolve(), args.objectives.resolve())
        text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(text, encoding="utf-8")
        print(text, end="")
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
