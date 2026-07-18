# Roadmap

## M0 — reproducible orchestrator and distribution foundation (implemented)

- Portable project manifest and path containment.
- Dependency doctor for the three installed Skills.
- Plan, parse, validate, build, immutable run records, hashes, and logs.
- Example detached-house project and automated tests.
- Self-contained `archflow-studio` Skill with bundled CAD, SketchUp, semantic modeling, setup, and official-source evidence tools.
- Standard Codex Plugin manifest with the Skill under `plugins/archflow-studio`.
- Windows Developer Preview lifecycle installer with plan, install, repair, uninstall, backup, Plugin registration, SBOM, checksums, and gated release build.

## M0.5 — local MCP broker (next)

- Expose one stable `archflow` MCP server instead of asking Codex to invoke each adapter directly.
- Start with read-only tools: workstation doctor, CAD status/export, SketchUp connection status, project validation, build plan, and run history.
- Add explicit approval metadata and reversible mutation endpoints only after read-only tools pass integration tests.
- Declare the broker in the Plugin `.mcp.json` and install it into a managed local runtime.

Exit criterion: after installing the Plugin, Codex can discover the broker, call every read-only health tool, and produce a single evidence-backed system status without arbitrary shell or Ruby evaluation.

## M0.7 — automated concept render handoff (implemented)

- Automatically trigger the rendering route after SketchUp generation or any render/effect-image request.
- Offer standard scenes, all standard scenes, or the user's current SketchUp camera as the render source.
- Capture source PNGs through the authenticated ArchFlow Bridge instead of requiring manual screenshots.
- Provide 13 original architectural visualization styles derived from official platform prompting principles.
- Prepare hashed image-edit jobs with high input fidelity, strict geometry locks, negative prompts, and concept-only review labels.
- Immediately use an exposed Codex image generation/edit tool after the user selects view and style; record provider unavailability honestly when no tool exists.

Exit criterion: one view/style selection produces a captured source image and traceable render job without another confirmation or manual screenshot.

## M1 — real site ingestion

- Export active DWG context through `codex-cad` without changing the drawing.
- Let the user identify authoritative boundary, road, datum, north, and units.
- Convert selected closed polylines into a versioned site context JSON.
- Add DXF fixture tests from AutoCAD, BricsCAD, ZWCAD, and GstarCAD.

Exit criterion: the same survey fixture produces the same normalized site geometry and provenance on every supported CAD application.

## M2 — requirements and evidence

- Parse PDF/DOCX/TXT into evidence spans, not just values.
- Store every legal constraint with authority, title, version/effective date, file/URL, page or clause, and hash.
- Add conflict detection, missing-input gates, and jurisdiction-specific rule packs maintained separately from the core.

Exit criterion: every machine check can be traced to an exact supplied source or is automatically marked `UNVERIFIED`.

## M3 — 3D-aware design authoring

- Add roofs, stairs, terrain, grids, levels, assemblies, shafts, and typed junctions to a new semantic schema version.
- Add room adjacency and circulation constraints.
- Separate architectural intent from structural calculation and verified member schedules.
- Add deterministic migration from model 1.0.

Exit criterion: plan, section, elevation, DXF, and SketchUp geometry are generated from the same component IDs with round-trip checks.

## M4 — controlled application execution

- Add a CAD adapter that always writes to a new drawing or named copy.
- Add a SketchUp adapter that validates the local bridge read-only, shows a mutation plan, then executes in reversible batches.
- Read back entity counts, tags, group names, scenes, and exported images.

Exit criterion: execution failures are detected and reported; no operation claims success from command submission alone.

## M5 — rendering and product UX

- Add direct provider adapters with consent, cost, seed/model, retry, output hash, and reproducibility metadata beyond the current Codex image-tool handoff.
- Local-first desktop UI for project intake, evidence review, model diff, approval gates, and run history.
- Plugin/adapter SDK, sample projects, CI matrix, signed releases, and contributor governance.

Exit criterion: a new contributor can add an adapter without modifying the semantic core, and a user can reproduce any published result from a project package.
