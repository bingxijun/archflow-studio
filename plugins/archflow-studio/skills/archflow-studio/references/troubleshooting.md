# SketchUp bridge troubleshooting

Use read-only checks before changing files.

## Extension does not load

Verify that the SketchUp Plugins directory contains:

```text
archflow_bridge.rb
archflow_bridge/main.rb
```

Run `scripts/preflight_check.ps1`. If SketchUp enforces signed-only loading, use a release signed through SketchUp Extension Warehouse; do not weaken the user's global loading policy.

## Port 9877 is closed

Run:

```powershell
Test-NetConnection 127.0.0.1 -Port 9877
netstat -ano | findstr 9877
```

Open SketchUp and a blank model. In SketchUp choose `Extensions > ArchFlow Bridge > Start Local Bridge`. Keep the listener on `127.0.0.1`; never expose it on a public interface.

## Authentication failed

Codex and SketchUp must run as the same Windows user and read `%LOCALAPPDATA%\ArchFlow\bridge-token`. Close both applications before repairing the token. Do not print the token in logs or support reports.

## Codex does not show tools

Confirm the installed Plugin contains `.mcp.json` and `mcp/archflow_mcp_server.py`, then restart Codex and open a new task. Do not add a duplicate `config.toml` MCP table.

## Validation accidentally requests modeling

For a connection test, call only `sketchup_bridge_status`, `sketchup_get_scene_info`, or `sketchup_get_selection`. If the user requests a modeling smoke test, create one small named box and report exactly what changed so SketchUp Undo can reverse it.
