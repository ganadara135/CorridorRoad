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

The 3D Centerline display can be reviewed with these curve modes:

- `Source Geometry`
- `B-spline`
- `Polyline`

`Source Geometry` is the preferred review mode because it keeps the generated preview closest to the Alignment and Profile source geometry.

Use `B-spline` only as a visual smoothing fallback.

Use `Polyline` when checking the exact sampled point sequence.

Build Parametric now prefers the same Source Geometry path for its `Corridor 3D Centerline` preview.

The expected object property is:

`PreviewSource = centerline3d_source_geometry`

If the preview reports `centerline3d_result_fallback`, rebuild or inspect the 3D Centerline source geometry before trusting downstream surfaces.

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
