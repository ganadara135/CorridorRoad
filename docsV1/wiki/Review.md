# Review

Review panels are read-only review and handoff surfaces.

They should expose context and diagnostics, not become the source of engineering intent.

## Cross Section Viewer

Use Cross Section Viewer to inspect station-level section results.

It can help review:

- finished-grade shape
- ditch and side-slope behavior
- bench behavior
- daylight context
- source references and handoff hints

## Plan/Profile Connection Review

Use Plan/Profile Connection Review to verify:

- station coverage
- Alignment/Profile relationship
- profile and station diagnostics

## 3D Centerline

Use 3D Centerline after Plan/Profile review to create the shared station/offset/elevation baseline used by downstream review and preview tools.

3D Centerline can show or hide evaluated station markers. Structures, Drainage, Applied Sections, Build Corridor, and Watertight Solids should prefer this shared result before falling back to older Alignment-only or Applied Section frame paths.

## Drainage Review

Use Drainage Review after authoring Drainage source rows.

It can review:

- Drainage Elements and Flow Routes
- Structure-backed pipeline candidates and pipeline segments
- pipeline networks and junctions
- Region assignment context
- Applied Section ditch context

## Earthwork Viewer

Use Earthwork Viewer to review:

- cut/fill area and volume results
- balance rows
- mass-haul rows
- diagnostics
- handoff back to station and section review

## Handoff Rule

When a review panel identifies an issue, return to the owning source editor, update the source, and rebuild the generated result.
