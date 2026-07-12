# Input evidence and safety gates

## Required project evidence

Record these fields before design generation:

- Source CAD path, revision/date, author if known, drawing unit, origin, north, and coordinate system.
- Site boundary and road boundary provenance; distinguish surveyed lines from diagrammatic lines.
- Project jurisdiction and address/parcel identifier.
- Use, structure intent, storey count, target areas, height, rooms, parking, accessibility, cost, and delivery mode.
- Legal sources with issuing authority, title, version/effective date, URL or supplied file, and exact page/clause.

If the site boundary, unit, origin, or jurisdiction is unknown, do not generate a compliance result. A concept mass may still be produced with an explicit assumption register.

## Legal constraint record

Use this shape inside `building_model.json`:

```json
{
  "sources": [
    {
      "id": "SRC-001",
      "authority": "Issuing authority",
      "title": "Document title",
      "version": "Effective date or revision",
      "locator": "page 12, clause 3.2",
      "url_or_file": "supplied/path/or/url"
    }
  ],
  "building_coverage_max_percent": 60,
  "floor_area_ratio_max_percent": 200,
  "max_height_mm": 10000,
  "uniform_setback_mm": 500,
  "constraint_source_ids": ["SRC-001"]
}
```

Missing `constraint_source_ids` makes numeric checks `UNVERIFIED`, even when the arithmetic passes.

## Human approval gates

Always put these gates in the review report when applicable:

- Licensed architect/designer: site interpretation, planning/code path, spatial design, permit and construction issue.
- Structural engineer: system, member sizing, lateral design, foundations, connections, and calculations.
- Fire/life-safety specialist or authority: occupancy, fire zones, egress, compartmentation, fire resistance, and firefighting access.
- Accessibility reviewer: routes, gradients, clearances, sanitary provisions, and local exceptions.
- MEP engineers: plant, shafts, routing, penetrations, loads, and coordination.
- Surveyor/geotechnical specialist: boundary, levels, datum, soil, groundwater, and retaining conditions.

## Mutation safety

- Never modify the original DWG/DXF. Export context or write a new DXF in a project output directory.
- Treat SketchUp execution as a model mutation. Generate the Ruby file first; run only with explicit user intent and preferably in a blank or copied model.
- Do not use arbitrary Ruby evaluation when a generated, inspectable script is sufficient.
