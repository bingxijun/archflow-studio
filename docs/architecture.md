# Architecture

## Product boundary

ArchFlow is an orchestrator and audit layer. It does not replace CAD, SketchUp, a licensed designer, a structural engineer, or an authority having jurisdiction.

```text
requirements + site CAD + sourced constraints
                    |
                    v
          archflow.project.json
                    |
                    v
          building_model.json
             /      |       \
            v       v        v
     semantic DXF  Ruby   review/metrics
                       \
                        v
                 verified line views
                        |
                        v
          captured standard/current view
                        |
                        v
              traceable render job
                        |
                        v
          available Codex image-edit tool
```

## Components

- `archflow`: project packaging, dependency discovery, immutable run directories, input fingerprints, subprocess isolation, logs, and status.
- `architectural-cad-to-sketchup`: semantic schema, deterministic validators and generators.
- ArchFlow CAD bridge: read-only CAD context acquisition and explicitly authorized CAD mutation through installed COM APIs.
- ArchFlow SketchUp bridge: bundled MCP stdio server, authenticated local TCP adapter, read-only health checks, and explicitly authorized model mutation.
- ArchFlow render handoff: standard/current SketchUp view capture, source/model hashes, an original architectural style catalog, geometry locks, and provider-neutral image-edit job manifests.

## Project package

```text
project/
  archflow.project.json
  inputs/
    requirements.*
    site.dwg|site.dxf
    legal/
  model/
    building_model.json
  outputs/
      runs/<timestamp>-<fingerprint>/
        render_inputs/
        render_jobs/
  .archflow/
    last-run.json
```

All manifest paths are relative to the project root. Paths may not escape the root. A run ID combines UTC time and the first eight characters of an input SHA-256 fingerprint. Each run stores `run.json`, `stdout.log`, and `stderr.log` beside generated artifacts.

The machine-readable manifest contract is [schemas/archflow-project.schema.json](../schemas/archflow-project.schema.json).

## Execution gates

Application mutation and paid/external provider execution use separate gates:

- CAD write gate: user selects target copy and confirms the exact mutation plan.
- SketchUp execution gate: user selects a blank/copied model and confirms loading the generated Ruby.
- Render gate: selecting view and style authorizes capture and an available built-in Codex image-edit tool; an external or paid provider still requires its cost/privacy authorization.
- Release gate: responsible professionals approve discipline-specific outputs.

## Versioning

Version these contracts independently:

- ArchFlow project manifest: `0.x` until the package layout stabilizes.
- Semantic building model: currently `1.0` in the architectural skill.
- Generator outputs: record generator path and input fingerprint in each run.

Do not silently migrate geometry. A migration must write a new model and a migration report.
