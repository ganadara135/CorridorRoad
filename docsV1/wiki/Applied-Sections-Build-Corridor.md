# Applied Sections and Build Corridor

Applied Sections and Build Corridor are generated result stages.

## Applied Sections

Applied Sections evaluate source intent at stations.

They resolve:

- Alignment frame
- Profile elevation
- matching 3D Centerline rows for the active Alignment, when available
- active Region
- Assembly Subassemblies
- SubAssembly Designer definitions referenced by Assembly rows
- Superelevation effective lane/shoulder crossfall
- Structure context
- drainage/ditch point rows where available
- terrain/daylight behavior

Applied Sections are results. They are not the primary editing surface.

Applied Section rows preserve Subassembly ownership when available.

Applied Section Subassembly rows also preserve preset trace fields when Assembly rows came from Subassembly presets.

The preserved fields include preset reference, preset version, preset status, and source instance reference.

Generated point, link, shape, quantity, surface, watertight solid, exchange, and simulation package outputs should use `subassembly_ref` as the preferred traceability field.

Active v1 result rows use Subassembly ownership as the user-facing source owner.

When an Assembly row references a Designer definition, Build Sections resolves the definition, applies row-local parameter overrides, evaluates point/link/shape rows, and stores the evaluated rows in the Applied Section result.

Applied Sections use the placed Assembly/Subassembly rows as the section source.

This means the evaluated Applied Section should match the Assembly/Subassembly Section Preview after the Assembly source has been applied.

Designer definition parameters are merged with row-local overrides before evaluation.

Percent slope parameters from reusable definitions are normalized before geometry is created.

Trapezoid ditch definitions may be inferred from `top_width`, `bottom_width`, and `depth` when a legacy `shape` field is absent.

Ditch points start from the finished-grade edge elevation of the preceding lane or shoulder.

This keeps shoulder-to-ditch and lane-to-ditch connections aligned with the section preview instead of snapping the ditch back to the raw frame elevation.

Designer surface role aliases are normalized during evaluation:

- `design`, `finished_grade`, `fg` -> `design_surface`
- `subgrade` -> `subgrade_surface`
- `slope_face`, `daylight` -> `slope_face_surface`
- `drainage` -> `drainage_surface`

The `Build Sections` action validates source handoff readiness and then builds result rows.

There is no separate user-facing `Validate` button in this result stage. Validation still runs automatically before Applied Sections are written.

Drainage readiness includes:

- every Drainage element row with an `Element ID` must have a `Region` assigned
- missing Drainage Region assignment is reported as `drainage_element_missing_region_ref`
- correction happens in the Drainage editor, not in Applied Sections

## Build Corridor

Build Corridor consumes Applied Sections and creates corridor preview surfaces and diagnostics.

Build Corridor does not evaluate Superelevation directly.

Build Corridor also does not evaluate SubAssembly Designer expressions directly. It consumes evaluated Applied Section point, link, and shape rows.

Superelevation must be applied before Applied Sections. Applied Sections then store the effective crossfall and `fg_surface` point rows that Build Corridor uses for Design Surface generation.

Typical outputs include:

- centerline context
- design surface preview
- subgrade surface preview
- slope face / daylight preview
- intersection surface preview
- intersection slope face preview
- intersection tie slope preview when accepted Applied Section window rows are available
- drainage surface preview where ditch surface rows exist

The Guided Review table includes Subassembly-kind rows after `Design Surface`.

These rows summarize evaluated Assembly/Subassembly output rows by kind and surface role.

Typical rows include `Lane`, `Shoulder`, `Ditch`, `Gutter`, `Curb`, and `Side Slope` when those kinds exist in the evaluated Applied Sections.

Build Parametric creates reusable Subassembly-kind review objects for these rows.

Double-clicking a Subassembly-kind row shows the centerline, design surface, slope face surface, and drainage surface together and displays the matching 3D review object for that specific kind.

The review object includes evaluated Subassembly links and closed shape outlines where shape rows exist, so lane, shoulder, ditch, gutter, curb, and side-slope geometry can be checked separately.

The review object stores `SubassemblyKind`, `SectionCount`, `LinkCount`, `ShapeCount`, and `SurfaceRoles` as object properties.

When a row came from a preset-backed Assembly row, the review object also stores `PresetRefs`, `PresetStatuses`, and `SourceInstanceRefs`.

Use these properties to confirm whether the generated surface came from a linked preset, a modified preset row, a detached snapshot, a missing preset, or an outdated preset.

If a `ditch` Subassembly is present but no `drainage_surface` links are available, the row reports a warning. Correct the Subassembly definition or Assembly placement, rebuild Applied Sections, and then rebuild Build Corridor.

If a `side_slope` Subassembly is present but no `slope_face_surface` links or surface patches are available, check that the side-slope row has valid width or daylight/bench inputs. Correct the source row, rebuild Applied Sections, and then rebuild Build Corridor.

Build Parametric output objects are exposed in the FreeCAD tree under:

`04_Parametric Model / Build Parametric Outputs`

This folder is for generated preview and review objects from the Build Parametric stage. Users can hide/show these objects from the tree and inspect their FreeCAD properties without reopening the task panel.

For intersections, Build Parametric keeps the generated output families separate:

- `Intersection Surface`
- `Intersection Slope Face Surface`
- `Intersection Tie Slope Surface`

`Intersection Tie Slope Surface` is generated from accepted Applied Section window rows.
It is not built from temporary highlight objects or generated mesh repair.

Use the `Breakline Audit` tab to review shared boundary handoff rows.
The compact `Intersection Tie Slope Window Handoff` row confirms that the accepted window edges were consumed by the generated tie-slope surface.

## Supplemental Sampling

Applied Sections can add supplemental sections between source station rows.

These rows are result-only Applied Sections.

They do not add editable source station rows.

They do not edit Alignment, Profile, Region, Assembly, or Subassembly source data.

They help generated surfaces follow the reviewed `3D Centerline` curve when the source station list is sparse.

Use the `Supplemental Sections` controls in the Applied Sections panel.

Use the Applied Sections `Density` slider to control the approximate maximum spacing between generated supplemental sections.

Higher density creates more Applied Sections on curved 3D Centerlines.

Lower density creates fewer Applied Sections and may be faster.

Supplemental section frames are resolved from `Centerline3DResult` when available.

Each supplemental section evaluates the same Assembly/Subassembly rows as ordinary Applied Sections.

This means lane, shoulder, ditch, side slope, drainage, and slope-face surface roles are available before Build Corridor runs.

Build Parametric consumes the resulting AppliedSectionSet.

It no longer exposes a supplemental density slider.

It also no longer creates hidden supplemental frames during normal surface generation.

If an older project has an AppliedSectionSet without supplemental sections, Build Parametric may use a temporary compatibility fallback and asks the user to rebuild Applied Sections.

Build Parametric keeps supplemental-section consumption as result provenance on the generated preview objects.

It no longer shows a separate `2a. Supplemental Sections` Guided Review row.

Supplemental section markers are review aids only.

If marker display is available, the marker object is:

`V1CorridorSupplementalFrameMarkers`

Each marker shows the supplemental section frame location and tangent direction.

Supplemental section consumption is normally checked through generated preview object properties, not through a Guided Review row.

The density control is an approximate spacing policy, not an unlimited subdivision request.

The current default is intentionally less dense than early prototypes.

At the default density, the approximate maximum spacing is about `45 m`.

Recursive supplemental sampling stops once an interval is already shorter than the requested maximum spacing.

This prevents straight or mildly curved spans from being overfilled with nearly duplicate sections.

Increase density when a curve needs more local surface fidelity.

Decrease density when the generated Applied Section set is too heavy or visually too dense.

After changing density, rebuild Applied Sections first and then rebuild Build Corridor.

If changing Applied Sections density does not change the generated corridor surface on a visibly curved 3D Centerline:

1. Confirm `3D Centerline` has been built and reviewed.
2. Rebuild Applied Sections with `Supplemental Sections` enabled.
3. Check the Applied Sections summary for a larger supplemental section count.
4. Rebuild Build Corridor.
5. Inspect the generated Build Parametric preview object properties for consumed supplemental section counts.
6. If compatibility fallback appears, rebuild Applied Sections again so Build Parametric consumes explicit result rows.

## 3D Centerline Source Geometry Handoff

3D Centerline is the preferred shared baseline for downstream station, tangent, and elevation context.

Build Parametric should consume the same reviewed 3D Centerline result that the 3D Centerline panel displays.

For the generated `Corridor 3D Centerline` preview object, the expected preferred source is:

`PreviewSource = centerline3d_source_geometry`

If source geometry cannot be built, Build Parametric may fall back to:

`PreviewSource = centerline3d_result_fallback`

Fallback is a diagnostic condition.

When fallback appears, review the 3D Centerline panel source geometry settings and rebuild the 3D Centerline before rebuilding Applied Sections and Build Corridor.

## Region Boundaries

The Build Corridor panel includes a `Region Boundaries` table.

Each row represents one source Region range.

For multi-alignment Intersections, Region rows are read from all participating Region source models. The table shows an `Alignment` column so primary-road and side-road Regions can be reviewed separately.

Double-click a Region row, or select a row and use `Highlight Region`, to display the selected Region's built objects in the 3D view.

The Region display is based on the selected Region's corridor objects, not a separate sketch-only highlight. It can include:

- design surface
- subgrade surface
- slope/daylight surface
- drainage surface
- structure object context where Applied Sections resolved active Structure rows

The Structure and Drainage columns are read-only resolved summaries from Applied Sections. They are not Region source fields.

If only part of the Region appears, rebuild Applied Sections and Build Corridor, then check the Region row's surface, structure, and drainage diagnostics.

## Surface Transitions

Surface Transitions are edited in Build Corridor.

Use `Region STA` to choose the Region boundary or Region station context to update.

Use `Spacing` to control the transition sample interval.

`Sample Count` in the Surface Transitions table is derived from the stored transition range and the current spacing.

Use `Update` to create or update the selected transition record.

Use `Toggle Enabled` to enable or disable the selected transition range.

Build Corridor uses the stored transition records when rebuilding corridor surfaces. Applied Sections should be generated first, then Build Corridor applies the transition settings during the surface build.

## Diagnostics

Use Build Corridor diagnostics to find missing or partial result rows before relying on downstream review or output.

The Subassembly guided review should expose preset status counts before output generation.

Review `linked`, `modified`, `snapshot`, `missing_preset`, and `preset_outdated` counts before treating Build Corridor outputs as accepted.

If a Superelevation change does not appear in the Design Surface:

1. Apply Superelevation.
2. Rebuild Applied Sections.
3. Rebuild Build Corridor.
4. Check the Applied Sections `Superelevation` column before investigating Build Corridor.

If a Subassembly preset change does not appear in generated surfaces:

1. Apply the SubAssembly Designer library.
2. Refresh or update affected Assembly rows.
3. Rebuild Applied Sections.
4. Rebuild Build Corridor.
5. Check Subassembly guided review rows for preset status counts and surface roles.
