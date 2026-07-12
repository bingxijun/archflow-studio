---
name: archflow-studio
description: Configure a user's local Windows CAD and SketchUp workflow, inspect DWG/DXF context, research current official planning and building regulations with traceable evidence, convert requirements and verified constraints into a 3D-aware semantic building model, validate geometry and screening metrics, generate semantic DXF and SketchUp Ruby models, export standard views and rendering prompts, and maintain immutable review records. Use when Codex needs to set up or repair the complete CAD-to-SketchUp toolchain, automate architectural concept/preliminary/construction-assistance work, or improve a design from sourced legal and site information; never claim permit, legal, structural, or final construction validity.
---

# ArchFlow Studio

Official website: https://archflow.best

Use this folder as the single self-contained workflow package. Use only its bundled ArchFlow CAD, design-core, MCP, and SketchUp bridge resources; do not require separately installed adapter Skills.

## Non-negotiable rules

- Label outputs `concept`, `preliminary`, or `construction_assistance`.
- Never call an output permit-ready, legally compliant, structurally approved, or a final construction document.
- Keep source CAD read-only. Write generated files to a project output directory.
- Treat loading CAD commands and executing SketchUp Ruby as mutations. Show the exact plan first and execute only when the user asked to configure or modify the application.
- Accept a legal rule only with jurisdiction, issuing authority, title, version/effective date, URL or supplied file, exact article/page/locator, retrieval time, and content hash. Mark incomplete rules `UNVERIFIED`.
- Do not invent structure, fire resistance, egress, accessibility, soil, foundation, or MEP requirements.
- Stop downstream generation on schema or geometry errors. Warnings may continue only when written to the review report.

## Route the request

1. **First-time setup or repair**: read [workstation-setup.md](references/workstation-setup.md). Run `scripts/setup_workstation.ps1` without `-Apply`; if the user asked to configure the machine and the plan is safe, run it again with `-Apply`.
2. **CAD inspection**: read [cad-com.md](references/cad-com.md) and [cad-sketchup.md](references/cad-sketchup.md). Run `scripts/cad-cli.ps1 diagnose`, then export the active drawing context read-only.
3. **Regulation or planning research**: read [legal-research.md](references/legal-research.md). Determine the project address, jurisdiction, and design date before searching official sources. Archive every relied-on source with `scripts/legal_evidence.py`.
4. **Semantic design and generation**: read [input-and-safety.md](references/input-and-safety.md) and [semantic-model.md](references/semantic-model.md). Build `building_model.json`, validate, then generate artifacts.
5. **SketchUp execution**: read [deployment.md](references/deployment.md) and [modeling.md](references/modeling.md). Use the bundled ArchFlow-owned MCP server and `ArchFlow::Bridge`; validate read-only, inspect and hash generated Ruby, then execute only in a blank or copied model after explicit approval.
6. **Views and rendering**: read [render-views.md](references/render-views.md). Preserve camera, openings, storeys, massing, setbacks, and source-view hashes.

## End-to-end workflow

1. Run the workstation doctor and produce a setup plan.
2. Inventory site CAD, requirements, legal files, jurisdiction, revisions, units, origin, datum, and north.
3. Research national, prefectural, municipal, district-plan, fire-zone, accessibility, energy, landscape, and agreement sources that apply to the project.
4. Create a legal evidence bundle and separate verified constraints from unresolved interpretations.
5. Export CAD context read-only and let the user identify authoritative site/road entities when ambiguous.
6. Create `archflow.project.json`, `requirements.yaml`, and one `building_model.json` as the semantic source of truth.
7. Validate IDs, polygons, hosted openings, storey volumes, areas, BCR/FAR/height/setbacks, provenance, and human review gates.
8. Generate a new semantic DXF, inspectable SketchUp Ruby, metrics, reports, view prompts, hashes, and logs in an immutable run directory.
9. If explicitly requested, apply CAD/SketchUp changes in reversible batches and verify by reading back entity counts, tags, groups, scenes, and exported image files.
10. Compare warnings and design objectives, revise the semantic model, and create a new run rather than overwriting prior evidence.

For iterative optimization, copy `assets/templates/optimization_objectives.json`, set explicit metrics/targets/weights, generate a candidate as a new run, then compare it with `scripts/design_optimizer.py`. Reject candidates that fail configured hard gates. Treat the quantitative winner as a recommendation pending the listed human reviews.

## Commands

Workstation plan and approved setup:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup_workstation.ps1
powershell -ExecutionPolicy Bypass -File scripts/setup_workstation.ps1 -Apply
```

Unified project CLI:

```powershell
python scripts/archflow_cli.py doctor --json
python scripts/archflow_cli.py init C:\projects\my-house --title "My House" --mode preliminary --core-skill .
python scripts/archflow_cli.py run C:\projects\my-house\archflow.project.json --stage build --core-skill .
```

CAD read-only diagnostics and export:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/cad-cli.ps1 diagnose
powershell -ExecutionPolicy Bypass -File scripts/cad-cli.ps1 export -OutputPath .\cad-context.json
```

Archive and verify official legal evidence:

```powershell
python scripts/legal_evidence.py init --jurisdiction "Japan/Tokyo/Example City" --effective-date 2026-07-11 --output-dir legal
python scripts/legal_evidence.py fetch --bundle legal --id JP-BSL --authority "Digital Agency" --title "Building Standards Act" --effective-date 2026-07-11 --locator "articles to be reviewed" --url "https://laws.e-gov.go.jp/law/325AC0000000201"
python scripts/legal_evidence.py verify --bundle legal
```

Compare two immutable design runs:

```powershell
python scripts/design_optimizer.py --baseline-run outputs\runs\BASE --candidate-run outputs\runs\CANDIDATE --objectives optimization_objectives.json --output optimization_report.json
```

## Output contract

A complete run contains `parsed_requirements.yaml`, `building_model.json` or its input hash, `metrics.json`, `validation_report.json`, `review_report.md`, `semantic_plans.dxf`, `build_model.rb`, `render_prompts/`, `run.json`, and stdout/stderr logs. Legal research additionally contains `legal_evidence.json` and archived source files.

Before redistributing the package, read [third-party-notices.md](references/third-party-notices.md) and run `python scripts/validate_skill_package.py`.
