# Modeling Reference

Use this only after the user explicitly asks to create, modify, or delete SketchUp geometry.

## Units

SketchUp Ruby API uses inches internally. Convert millimeters:

```ruby
mm = 1.0 / 25.4
width = 2000 * mm
```

## Safe Modeling Pattern

1. Summarize the intended modeling operation.
2. Use named groups or components for every created object.
3. Batch related Ruby operations into a SketchUp operation when possible.
4. Avoid destructive cleanup unless the user explicitly asked for it.
5. Read back object names or selection state after the operation.

## Smoke Test Shape

For an explicit modeling smoke test, create a simple one-story white massing model:

- `site_base`: 12000 mm x 9000 mm x 100 mm, light gray.
- `building_mass`: 7000 mm x 5000 mm x 3000 mm, white.
- `gable_roof`: dark gray gable roof, placeholder geometry is acceptable.
- `window_south_01`, `window_south_02`, `window_south_03`: blue translucent placeholder faces.
- `door_east_01`: dark placeholder face.
- `test_label`: 3D text reading `Codex SketchUp MCP Test`.

State clearly that placeholder faces are not true boolean openings.
