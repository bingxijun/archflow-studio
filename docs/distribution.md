# Distribution model

Official website: https://archflow.best

ArchFlow uses one open-source repository with three deliverables:

- Codex Plugin: `plugins/archflow-studio`, containing the reusable Skill and local adapters.
- Windows companion installer: `installer/windows`, responsible for detection, backup, registration, repair, and uninstall.
- Xiaohongshu standalone Skill: `distributions/xiaohongshu/archflow`, containing the complete Skill resources, standalone MCP server source, explicit permission disclosure, upload validation, and a deterministic ZIP builder. It does not replace or modify the Codex Plugin deliverable.

Build the Xiaohongshu upload ZIP with `python distributions/xiaohongshu/archflow/scripts/build_xhs_package.py`. The generated archive keeps `SKILL.md` at the ZIP root and enforces the platform's 10 MiB per-file and 30 MiB total source limits.

Developer Preview packages are ZIP files produced by `installer/windows/build_release.ps1`. Each package includes the Plugin payload, setup script, Apache-2.0 license, third-party notices, SPDX SBOM, and SHA-256 file inventory.

Release readiness is machine-readable in `release/release-gates.json`. `scripts/release_check.py` allows Developer Preview builds while refusing a production channel whenever a required gate remains blocked.

Public production release gates:

1. Keep every bundled runtime or future third-party dependency mapped in the SPDX SBOM with its exact license and source.
2. Sign the reproducibly built ArchFlow RBZ through SketchUp Extension Warehouse and verify supported loading policies.
3. Maintain protocol and compatibility tests for the ArchFlow MCP broker declared through the Plugin `.mcp.json`.
4. Track native adapter installation so uninstall and rollback restore every changed file/configuration.
5. Build and Authenticode-sign an MSI/EXE wrapper and timestamp the signature.
6. Test clean install, upgrade, repair, rollback, and uninstall on the supported Windows/CAD/SketchUp matrix.
7. Publish privacy, security, support, and responsible-use policies.

Do not call a package an official production installer until every gate passes.
