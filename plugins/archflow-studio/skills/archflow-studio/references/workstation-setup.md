# Workstation setup

## Goal

Configure the local chain without touching project drawings or model geometry:

```text
Codex -> ArchFlow Studio -> CAD COM bridge
                     \-> bundled MCP server -> local TCP 127.0.0.1:9877 -> ArchFlow::Bridge
```

## Procedure

1. Run `scripts/setup_workstation.ps1` without `-Apply`.
2. Review detected CAD applications, SketchUp versions/plugin directories, Python, destination paths, RBZ hash, and port status.
3. Treat missing software, ambiguous multiple SketchUp plugin directories, a public/non-local port, or an unknown plugin hash as blockers.
4. When the user has asked to configure the machine and the plan is correct, run with `-Apply`.
5. Restart SketchUp and Codex. Open a blank SketchUp model.
6. Validate TCP and call a read-only selection/scene query. Do not use arbitrary Ruby evaluation as a health check.
7. Record versions, selected plugin directory, RBZ hash, backup paths, and validation result. Never record the pairing token.

The apply path deploys the reproducibly built ArchFlow RBZ with backups and creates a local pairing token. It does not clone a repository, install Python packages, edit Codex configuration, or delete unrelated plugins.

CAD COM access requires no permanent AutoCAD installation changes. Load `assets/codex_cad_bridge.lsp` into an active drawing only when the user wants the in-CAD helper commands.
