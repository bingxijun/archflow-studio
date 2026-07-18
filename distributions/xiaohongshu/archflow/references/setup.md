# CAD setup compatibility note

The former standalone CAD setup has been merged into ArchFlow Studio. Use `references/workstation-setup.md` and run `scripts/setup_workstation.ps1` from the unified Skill folder.

CAD COM access itself does not require copying files into AutoCAD. The bundled `scripts/cad-cli.ps1` discovers compatible COM ProgIDs and materializes `assets/codex_cad_bridge.lsp.txt` as `%LOCALAPPDATA%\ArchFlow\generated\codex_cad_bridge.lsp` only when the user explicitly asks to load the in-CAD helper.
