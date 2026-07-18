# CAD COM Reference

The bridge tries these ProgIDs by default:

- `AutoCAD.Application.23.1` for AutoCAD 2020, including Simplified Chinese installs.
- `AutoCAD.Application`
- `AutoCAD.Application.23`
- `BricscadApp.AcadApplication`
- `ZWCAD.Application`
- `GstarCAD.Application`

After the preferred list, the bridge scans these registry roots for additional matching ProgIDs:

- `HKCU:\Software\Classes`
- `HKLM:\SOFTWARE\Classes`
- `HKLM:\SOFTWARE\WOW6432Node\Classes`

Use `cad-cli.ps1 progids` to show the final ordered list and discovered registrations.

COM access is local to Windows and depends on the CAD application registration. The same machine/user session must be able to create or retrieve the CAD automation object.

## Read-only operations

Preferred read operations:

- `Application.Name`
- `Application.Version`
- `Application.ActiveDocument`
- `Document.Name`
- `Document.FullName`
- `Document.Layers`
- `Document.Blocks`
- `Document.Layouts`
- `Document.ModelSpace`

## Mutating operations

Operations such as `Documents.Open`, `Document.SendCommand`, `Document.Save`, and plugin commands can change state. Use them only when the user asks, and verify afterward.

For Simplified Chinese AutoCAD, send locale-neutral global commands with `_` or `_.` prefixes, for example `_.ZOOM`, `_.LINE`, `_.REGEN`, and `_.APPLOAD`.

## Asynchronous commands

`SendCommand` usually returns before the CAD command finishes. For reliable workflows, run a follow-up `status` or `export` after the command completes.
