# CAD and SketchUp integration

## CAD inspection

For an active AutoCAD-compatible drawing, use the bundled CAD bridge:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\cad-cli.ps1 diagnose
powershell -ExecutionPolicy Bypass -File scripts\cad-cli.ps1 export -OutputPath .\cad-context.json
```

Use read-only export first. Resolve units and select the authoritative site-boundary entities before authoring the semantic model. The MVP generator writes a new ASCII DXF and never edits the source.

## Semantic layers

Use uppercase ASCII names for broad CAD compatibility:

- `SITE-BOUNDARY`, `SITE-ROAD`, `LEGAL-SETBACK`
- `A-WALL-EXT-{STOREY}`, `A-WALL-INT-{STOREY}`
- `A-SLAB-{STOREY}`, `A-OPEN-DOOR-{STOREY}`, `A-OPEN-WINDOW-{STOREY}`
- `A-ZONE-{USAGE}-{STOREY}`
- `S-COLUMN-{STOREY}`, `S-BEAM-{STOREY}`

Normalize spaces and punctuation to hyphens. Store custom office mappings in a project copy of `layer_map.json`.

## SketchUp execution

The generated Ruby script:

- converts millimetres to SketchUp inches;
- creates named groups for storeys and components;
- assigns tags and materials;
- subdivides straight walls around rectangular hosted openings;
- creates front, right, top, and axon scenes;
- exports PNG images beside the Ruby file.

Run the script from SketchUp's Ruby console with:

```ruby
load 'C:/absolute/path/to/build_model.rb'
```

Use forward slashes in the Ruby path. Execute in a blank or copied model. Inspect the Ruby file before running it.

For MCP-based execution, use the bundled ArchFlow bridge: keep the authenticated connection on `127.0.0.1:9877`, validate with `sketchup_bridge_status` or a read-only scene query first, and mutate geometry only after an explicit user request.

## Known MVP limits

- Walls must have straight two-point axes.
- Openings are rectangular and orthogonal to their host wall.
- Roof, stair, terrain, curved wall, and detailed connection generation are not included.
- Image export depends on SketchUp permissions and active graphics context; verify every output file.
