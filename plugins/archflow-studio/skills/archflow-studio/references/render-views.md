# View and rendering rules

## Standard views

- `front`: orthographic view looking toward positive Y.
- `right`: orthographic view looking toward negative X.
- `top`: orthographic plan from above.
- `axon`: perspective bird-eye view showing front and right sides.

Use SketchUp parallel projection for front, right, and top. Keep visible edges and profiles on, textures off for line exports. Verify orientation against project north and the desired principal facade; rename scenes if the site coordinate system differs.

## Prompt construction

Build prompts from evidence in the model:

1. View/camera and massing preservation instruction.
2. Building use, storeys, and architectural intent.
3. Explicit material map and color zoning.
4. Site, season, time, weather, and lighting only when supplied; otherwise mark them as creative assumptions.
5. Negative constraints: do not change openings, floor count, silhouette, camera, setbacks, or adjacent-site geometry.

Rendering is a design visualization, not evidence that a detail is buildable or compliant. Keep line exports and the exact prompt manifest with each rendered image for traceability.
