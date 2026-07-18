# View and rendering rules

## Automatic interaction

Enter this flow after a successful SketchUp model build and whenever the user asks for a render, effect image, concept image, visualization, 渲染, 效果图, 概念图, or 出图.

1. Do not ask the user to make a screenshot when ArchFlow Bridge is available.
2. If view is missing, present `Current`, `Front`, `Right`, `Top`, `Axon`, and `All standard views` as structured choices when the client supports them; otherwise use one numbered line.
3. `Current` means the camera currently visible in SketchUp. Tell the user to finish orbit/pan/zoom before selecting it.
4. If style is missing, ask one question only. Show concise style names and descriptions from `assets/templates/render_style_catalog.json` or `python scripts/render_workflow.py list-styles`.
5. Once the user chooses a view and style, capture and generate immediately. Do not ask for a second confirmation.

## Capture source views

- `current`: preserve the user's active SketchUp camera and crop.
- `front`: orthographic view looking toward positive Y.
- `right`: orthographic view looking toward negative X.
- `top`: orthographic plan from above.
- `axon`: bird-eye perspective showing front and right sides.

Use `sketchup_capture_view` with an explicit PNG output under the current run's `render_inputs/` directory. Use 2000×1600 unless the user requests another supported size. Record the returned camera values and source-image SHA-256 in the render job.

If the bridge is unavailable but an exported standard PNG exists under `sketchup_views/`, use that file. Ask for an uploaded screenshot only as the final fallback.

## Style choices

The built-in catalog contains:

- 写实自然日景 — neutral daylight and physically plausible materials.
- 金色黄昏 — warm low sun and long shadows.
- 蓝调暮色 — cool sky with warm interior lighting.
- 建筑夜景 — controlled facade, landscape, and interior lighting.
- 阴天极简 — diffuse light emphasizing massing and material.
- 日式自然极简 — warm timber, pale mineral surfaces, and quiet planting.
- 电影感建筑摄影 — editorial light and restrained filmic colour.
- 建筑水彩 — transparent washes with retained linework.
- 铅笔概念草图 — precise perspective lines and graphite hatching.
- 白模体块 — uniform matte clay material for massing review.
- 等距分析图 — limited colours and diagrammatic clarity.
- 材质研究 — physically plausible material texture and reflectance.
- 室内柔光 — soft window light and restrained interior styling.

Accept natural-language aliases. For an unlisted style, use `--style custom --custom-style "..."` and summarize it in one sentence before generation.

## Prompt assembly

Build the final prompt in this order:

1. Source image as strict geometry, camera, crop, and composition reference.
2. Building use, storeys, architectural intent, and verified material map.
3. Selected visual medium/style.
4. Environment, season, time, weather, people, and planting only when supplied; otherwise treat them as creative layers.
5. Lighting, colour, mood, and presentation quality.
6. Geometry lock and concept-only disclaimer.

Use `scripts/render_workflow.py prepare` to create the final prompt and negative prompt. Keep the phrasing concise; do not paste multiple competing style recipes.

## Image generation

- Prefer image edit/reference-image mode over text-to-image.
- Prefer high input fidelity when the provider supports it.
- Preserve the source aspect ratio when possible.
- Use the selected style for materials, atmosphere, lighting, and post-processing—not for geometry changes.
- For multiple views, generate one job and one output per view; never use one rendered view as the geometry reference for another.
- If a style reference image is supplied, treat it as style only and the SketchUp capture as composition/geometry.

## Geometry lock

Never change camera, crop, site boundary, adjacent geometry, footprint, floor count, finished-floor elevations, roof silhouette, walls, slabs, openings, columns, beams, or setbacks. Do not invent unsupported construction details. Compare every result with its source PNG and flag visible drift.

Rendering is a `concept visualization`, not evidence that a detail is buildable, structurally adequate, or legally compliant. Keep the source image, prepared prompt, negative prompt, model hash, camera data, provider, and output together.

## Research basis

The catalog uses original ArchFlow wording derived from current official platform guidance:

- OpenAI image models support image generation/editing and high-fidelity image inputs: https://developers.openai.com/api/docs/models/gpt-image-2
- Midjourney recommends concise prompts covering subject, medium, environment, lighting, colour, mood, and composition: https://docs.midjourney.com/docs/prompts
- Stability separates image-to-image strength, style presets, prompt, and negative prompt: https://platform.stability.ai/docs/api-reference
- Adobe recommends direct prompts with subject, descriptors, style, and lighting: https://helpx.adobe.com/firefly/web/work-with-images/generate-images/writing-effective-text-prompts.html
- D5 separates concept generation, atmosphere matching, enhancement, and style transfer: https://support.d5render.com/support/solutions/articles/72000649240-ai-features
