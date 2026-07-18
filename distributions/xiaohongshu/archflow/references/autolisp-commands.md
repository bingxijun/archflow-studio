# AutoLISP Plugin Commands

The published helper source is `assets/codex_cad_bridge.lsp.txt`. When the user explicitly runs `load-plugin`, ArchFlow copies it transparently to `%LOCALAPPDATA%\ArchFlow\generated\codex_cad_bridge.lsp` before loading it into CAD.

Load it through:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\cad-cli.ps1 load-plugin
```

Or manually in CAD:

```lisp
(load "C:/path/to/codex_cad_bridge.lsp")
```

## Commands

- `CODEXHELP`: Print available helper commands in the CAD command line.
- `CODEXEXPORT`: Prompt for a JSON path and export basic drawing context.

## Programmatic function

After loading the plugin:

```lisp
(codex-export "C:/temp/codex-cad-context.json")
```

The export includes drawing name, path, CAD version, layer names, and entity type counts from the current drawing database.
