---
name: archflow-studio
description: Configure a user's local Windows CAD and SketchUp workflow, inspect DWG/DXF context, research current official planning and building regulations with traceable evidence, convert verified requirements into a 3D-aware semantic model, generate and execute reviewable CAD/SketchUp artifacts, capture standard or current SketchUp views, and automatically prepare and run geometry-preserving architectural concept renders in a user-selected style. Use for setup or repair, CAD-to-SketchUp automation, architectural concept/preliminary/construction-assistance work, design optimization, or any request mentioning render, rendering, visualization, concept image, effect image, 效果图, 概念图, 渲染, 出图, or turning the current model/view into an image; never claim permit, legal, structural, or final construction validity.
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
6. **Views and rendering**: read [render-views.md](references/render-views.md). Automatically enter this route after successful SketchUp generation and whenever the user requests a render, visualization, concept image, or effect image. Capture a selected standard scene or the user's current camera through `sketchup_capture_view`; do not ask the user to take or upload a screenshot when the bridge is available.

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
11. After a successful SketchUp build, offer render-view choices, collect only a missing style preference, capture the selected view, prepare a traceable render job, and immediately use an available image-editing tool after the user's selection.

For iterative optimization, copy `assets/templates/optimization_objectives.json`, set explicit metrics/targets/weights, generate a candidate as a new run, then compare it with `scripts/design_optimizer.py`. Reject candidates that fail configured hard gates. Treat the quantitative winner as a recommendation pending the listed human reviews.

## Automatic render handoff

1. Trigger this handoff after model generation or on any rendering intent. Do not require a separate screenshot.
2. If the user has not selected a view, use a structured choice UI when available; otherwise show one compact numbered choice: `Current SketchUp view`, `Front`, `Right`, `Top`, `Axon`, or `All standard views`. Tell the user to position the camera before choosing `Current`.
3. If the user has already specified a view, do not ask again. Capture it with `sketchup_capture_view` into the current immutable run's `render_inputs/` directory.
4. If style is missing, ask exactly one style question. Read [render-views.md](references/render-views.md), run `python scripts/render_workflow.py list-styles`, and show concise labels and one-line descriptions. Accept a built-in alias or a free-form custom style.
5. Treat the user's view/style selection as the instruction to generate. Do not request another confirmation. Run `render_workflow.py prepare` and write `render_jobs/<view>.json`.
6. If an image generation/editing tool is exposed, use it immediately in edit/reference-image mode with the captured PNG and the prepared prompt. Prefer high input fidelity. Do not use text-to-image when a captured view exists.
7. If no image tool is exposed, finish the render job manifest and prompt without pretending an image was generated. State the missing provider in one sentence.
8. Compare the result with the source image for camera, crop, footprint, floor count, roof silhouette, openings, setbacks, and adjacent geometry. Label the result `concept visualization`.

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

List styles and prepare a render job after capturing a SketchUp view:

```powershell
python scripts/render_workflow.py list-styles
python scripts/render_workflow.py prepare --source-image outputs\runs\RUN\render_inputs\current.png --view current --style golden-hour --model model\building_model.json --render-manifest outputs\runs\RUN\render_prompts\manifest.json --output outputs\runs\RUN\render_jobs\current.json
```

## Output contract

A complete run contains `parsed_requirements.yaml`, `building_model.json` or its input hash, `metrics.json`, `validation_report.json`, `review_report.md`, `semantic_plans.dxf`, `build_model.rb`, `render_prompts/`, `run.json`, and stdout/stderr logs. A requested render additionally contains a source PNG under `render_inputs/`, a traceable job under `render_jobs/`, and the generated concept image or an explicit provider-unavailable record. Legal research additionally contains `legal_evidence.json` and archived source files.

Before redistributing the package, read [third-party-notices.md](references/third-party-notices.md) and run `python scripts/validate_skill_package.py`.
