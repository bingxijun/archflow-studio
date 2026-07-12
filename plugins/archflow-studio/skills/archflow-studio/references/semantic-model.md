# Semantic building model

Use `assets/templates/building_model_schema.json` as the field contract and `building_model_template.json` as a working example.

## Coordinate rules

- Geometry values are millimetres in one project coordinate system.
- Each storey has an absolute `z_mm` and clear/model height `height_mm`.
- Polygons omit the repeated closing vertex; generators close them.
- Keep the source CAD origin. Do not arrange storeys side-by-side in model coordinates.
- Storey-specific CAD separation belongs in layer names, not coordinate offsets.

## Component rules

- `spaces`: named usage polygons for area schedules, zoning color, and finish intent. Do not treat them as structure.
- `slabs`: load-bearing or architectural slab volumes with thickness and material.
- `walls`: centerline axis, thickness, base offset, height, type, and material. The MVP supports a straight two-point axis per wall.
- `openings`: host-wall ID, along-wall offset, width, sill, and height. Offsets start at the wall axis first point.
- `columns`: center, width, depth, base offset, height, and material.
- `beams`: straight axis, width, depth, base offset, and material.

Keep construction assemblies as intent fields or review items until a qualified designer supplies verified layer build-ups. A material label such as `rc` is not a structural design calculation.

## Area policy

The pipeline calculates:

- Footprint: largest slab polygon area on the lowest storey.
- Gross floor area: sum of all `spaces` polygons unless `project.area_basis` says otherwise.
- BCR: calculated footprint / site polygon area.
- FAR: calculated gross floor area / site polygon area.
- Height: highest storey `z_mm + height_mm` minus project datum 0.

These are geometric screening metrics. Replace the area basis where the governing jurisdiction includes or excludes specific elements.

## Modeling limitations

- Curved walls, sloped slabs, roofs, stairs, railings, terrain, boolean wall penetrations beyond rectangular hosted openings, and detailed junctions require a later schema version or manual modeling.
- Space overlap and code-specific area exemptions are not automatically resolved.
- Structural member dimensions are modeled values, not proof of adequacy.
