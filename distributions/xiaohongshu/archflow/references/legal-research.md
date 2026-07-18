# Official regulation research

## Evidence order

For a project in Japan, search and reconcile sources in this order:

1. e-Gov current/historical law text for national acts, cabinet orders, ministerial ordinances, and exact effective dates.
2. Ministry of Land, Infrastructure, Transport and Tourism pages, notices, technical guidance, and official planning datasets.
3. Prefecture and municipality official ordinance databases, planning maps, district plans, landscape plans, fire-zone maps, road classifications, building agreements, and authority guidance.
4. User-supplied official certificates, survey material, consultations, and authority correspondence.

Use secondary sources only to discover official material. Never use a blog, vendor summary, AI answer, or search snippet as the rule evidence.

## Required research inputs

- Address or parcel identifier.
- Country, prefecture, municipality, and authority having jurisdiction.
- Design/check date and intended submission date.
- Use, scale, structure intent, storeys, height, site/road facts, and proposed work type.
- Supplied planning certificates, maps, agreements, prior approvals, and consultation notes.

If these are incomplete, create a research plan and unresolved list; do not issue a compliance result.

## Evidence record

Archive relied-on official pages/files with `scripts/legal_evidence.py`. Each applied constraint must point to one or more evidence IDs and an exact article, page, map legend, or clause. Keep source text separate from the interpreted machine rule.

Record these statuses:

- `VERIFIED_SOURCE`: source identity, date, locator, and hash are complete; interpretation still needs professional review.
- `UNVERIFIED`: source or applicability is incomplete; exclude from compliance claims.
- `CONFLICT`: official sources appear inconsistent or dates/applicability differ; stop the affected check.
- `SUPERSEDED`: retained for history but not applied to the current design date.

## Japan starting points

- Building Standards Act: `https://laws.e-gov.go.jp/law/325AC0000000201`
- Enforcement Order: `https://laws.e-gov.go.jp/law/325CO0000000338`
- e-Gov law API: `https://laws.e-gov.go.jp/apitop`
- MLIT building legislation: `https://www.mlit.go.jp/jutakukentiku/build/code.html`
- MLIT planning overview: `https://www.mlit.go.jp/toshi/city_plan/toshi_city_plan_tk_000043.html`
- MLIT real-estate/planning information library: `https://www.reinfolib.mlit.go.jp/`

National planning GIS and the real-estate information library are screening sources. Their own notices state that coverage may be incomplete and they are not guaranteed for confirmation/important-explanation procedures. Confirm decisive zoning, district plan, fire zone, roads, and overlays with the responsible local authority.

## Design optimization

Turn verified rules into explicit constraints and objectives, not free-form suggestions. Keep hard gates (site, use, BCR/FAR, height, setbacks, egress, fire, accessibility) separate from soft objectives (area efficiency, daylight, views, cost, material, render quality). Generate alternatives only inside verified hard bounds, list which assumptions changed, and run a new immutable validation record for every alternative.
