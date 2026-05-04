# CorridorRoad V1 Region Surface Transition Plan

Date: 2026-05-03
Status: Draft implementation plan
Depends on:

- `docsV1/V1_MASTER_PLAN.md`
- `docsV1/V1_REGION_MODEL.md`
- `docsV1/V1_REGION_APPLICATION_FLOW_PLAN.md`
- `docsV1/V1_SURFACE_MODEL.md`
- `docsV1/V1_CORRIDOR_MODEL.md`
- `docsV1/V1_DITCH_SHAPE_CONTRACT.md`

## 1. Purpose

This document defines how v1 should implement Region boundary-aware surface build and user-selected Transition Surface ranges.

It exists to make corridor-derived surfaces explainable when Assembly, Structure, Drainage, or Region context changes across stations.

## 2. Scope

This plan covers:

- detecting Region boundary spans in `AppliedSectionSet`
- preserving Region ownership in surface build results
- diagnosing surface continuity quality at Region changes
- allowing users to choose station ranges where Transition Surface should be applied
- generating transition sections as derived results
- showing transition and boundary diagnostics in review/output surfaces

This plan does not cover:

- editing generated TIN vertices directly
- making Region own Assembly or Structure geometry
- replacing `AssemblyModel`, `RegionModel`, or `DrainageModel`
- full hydraulic drainage analysis
- final drawing-sheet production

## 3. Core Rule

Transition Surface intent belongs in source-level transition range records.

Generated transition sections, TIN vertices, triangles, and preview meshes are results and outputs.

Do not store user design intent only inside generated surface geometry.

## 4. Current Behavior

Current v1 behavior:

- `AppliedSectionService` resolves one active Region per station.
- Each `AppliedSection` preserves `region_id`, `assembly_id`, structure context, point rows, and diagnostics.
- `CorridorSurfaceService` creates corridor-level surface families:
  - `design_surface`
  - `subgrade_surface`
  - `daylight_surface`
  - optional `drainage_surface`
- `CorridorSurfaceGeometryService` connects adjacent Applied Sections into surface ribbons or TIN previews.
- Surface rows are not currently split by Region.
- Region boundary spans are not explicitly diagnosed as surface transition spans.

## 5. Target Behavior

Target v1 behavior:

- Region boundary spans are detected before surface geometry is built.
- Surface build results can report which Region produced each surface span.
- Build Corridor review can show Region boundary continuity diagnostics.
- Users can define station ranges where Transition Surface generation should apply.
- Transition Surface ranges can be enabled, disabled, reviewed, and regenerated.
- Transition sections are derived from source models and transition range records.
- Surface previews can show normal spans, Region boundary spans, and transition spans distinctly.

## 6. Object Families

Recommended new source-side object families:

- `SurfaceTransitionModel`
- `SurfaceTransitionRange`
- `SurfaceTransitionDiagnostic`

Recommended result/output-side object families:

- `SurfaceSpanRow`
- `SurfaceTransitionSection`
- `SurfaceTransitionResult`
- `SurfaceBoundaryDiagnostic`

## 7. SurfaceTransitionModel

### 7.1 Purpose

`SurfaceTransitionModel` stores user-approved Transition Surface ranges for one corridor or project.

It is source intent.

It should be rebuilt into generated transition sections and surface spans during Build Corridor.

### 7.2 Root Fields

Recommended fields:

- `schema_version`
- `transition_model_id`
- `project_id`
- `corridor_ref`
- `transition_ranges`
- `diagnostic_rows`
- `source_refs`
- `notes`

## 8. SurfaceTransitionRange

### 8.1 Purpose

`SurfaceTransitionRange` records where the user wants Transition Surface to be applied.

It is station-range based.

It is not limited to exact Region boundary stations.

### 8.2 Fields

Recommended fields:

- `transition_id`
- `station_start`
- `station_end`
- `from_region_ref`
- `to_region_ref`
- `target_surface_kinds`
- `transition_mode`
- `sample_interval`
- `enabled`
- `approval_status`
- `source_ref`
- `notes`

### 8.3 Target Surface Kinds

Initial supported values:

- `design_surface`
- `subgrade_surface`
- `daylight_surface`

Deferred values:

- `drainage_surface`
- `structure_adjacent_surface`
- `clipped_export_surface`

Drainage transition should be deferred until ditch, flowline, inlet, and drainage ownership rules are stable.

## 9. Transition Mode

### 9.1 Purpose

`transition_mode` defines the allowed transformation used inside the selected station range.

It should prevent unsafe automatic geometry guesses.

### 9.2 Initial Modes

Recommended initial modes:

- `interpolate_width`
- `interpolate_matching_roles`
- `manual_required`

### 9.3 interpolate_width

Use this when the user wants a simple geometric taper.

Interpolated values:

- `surface_left_width`
- `surface_right_width`
- `subgrade_depth`
- `daylight_left_width`
- `daylight_right_width`
- `daylight_left_slope`
- `daylight_right_slope`

Do not invent missing component rows.

Do not map ditch points to curb or sidewalk points.

### 9.4 interpolate_matching_roles

Use this when both ends have compatible point roles.

Interpolated point roles:

- `fg_surface`
- `subgrade_surface`
- `side_slope_surface`
- `bench_surface`
- `daylight_marker`

Optional later point roles:

- `ditch_surface`

Only interpolate point rows when role count and ordering are stable.

If roles do not match, emit diagnostics and fall back to `manual_required` behavior for that role.

### 9.5 manual_required

Use this when automatic transition is unsafe.

Examples:

- ditch section to curb/sidewalk section
- normal roadway to bridge gap
- culvert influence start or end with conflicting point roles
- one side has daylight and the other side does not
- point role counts are incompatible

The build should leave the normal direct surface behavior or skip transition generation according to the user setting, and diagnostics must explain why.

## 10. Region Boundary Detection

### 10.1 Boundary Span

A boundary span exists when adjacent applied sections differ in any of these fields:

- `region_id`
- `assembly_id`
- `template_id`
- active structure context
- active drainage context when available

### 10.2 Boundary Span Rows

Recommended `SurfaceSpanRow` fields:

- `span_id`
- `station_start`
- `station_end`
- `from_region_ref`
- `to_region_ref`
- `surface_kind`
- `span_kind`
- `transition_ref`
- `continuity_status`
- `diagnostic_refs`
- `notes`

Recommended `span_kind` values:

- `same_region`
- `region_boundary`
- `transition_surface`
- `gap_or_break`

Recommended `continuity_status` values:

- `ok`
- `needs_review`
- `transition_applied`
- `manual_required`
- `failed`

## 11. Boundary Diagnostics

Boundary diagnostics should compare adjacent sections before surface triangulation.

Recommended diagnostic kinds:

- `region_boundary_width_jump`
- `region_boundary_subgrade_jump`
- `region_boundary_daylight_width_jump`
- `region_boundary_daylight_slope_jump`
- `region_boundary_point_role_mismatch`
- `region_boundary_ditch_mismatch`
- `region_boundary_bench_mismatch`
- `region_boundary_structure_context_change`
- `region_boundary_transition_range_missing`
- `transition_surface_role_mismatch`
- `transition_surface_station_range_invalid`
- `transition_surface_no_boundary_context`

Recommended severity:

- `info` for expected context changes
- `warning` for large but buildable changes
- `error` for invalid transition range settings

## 12. Transition Section Generation

Transition sections are generated result rows inserted between existing Applied Sections during surface build.

They do not replace source Region rows.

Recommended generation flow:

1. Collect station-ordered Applied Sections.
2. Detect Region boundary spans.
3. Load enabled `SurfaceTransitionRange` records.
4. Validate transition ranges against station coverage and Region context.
5. Insert generated transition sections inside selected station ranges.
6. Mark generated sections with `source_kind = transition_surface`.
7. Build surface TINs from the augmented section sequence.
8. Preserve diagnostics and span metadata.

Generated transition section ids should be deterministic.

Example:

`applied-section-a->applied-section-b:transition:transition-01:sta-105`

## 13. Station Range Rules

A transition range may:

- start before a Region boundary station
- end after a Region boundary station
- cover more than one Region boundary if explicitly allowed later

Initial implementation should prefer one transition range per boundary.

Validation should warn when:

- the range does not contain a Region boundary
- multiple boundaries exist inside one range
- start station is greater than or equal to end station
- target surface kind is unsupported
- no matching Applied Sections exist near either end

## 14. UI Direction

Region boundary review and Transition Surface authoring should live in the Build Corridor workflow.

Reason:

- Region boundaries become meaningful surface-build concerns after Applied Sections exist.
- Users need surface preview and build diagnostics when deciding whether a transition range is needed.
- Applied Sections should remain the station-wise section result builder, not the primary surface-transition authoring panel.

Applied Sections may show read-only Region context, but Transition Surface range editing should be handled from Build Corridor.

## 15. Build Corridor Region Boundaries UI

Build Corridor should expose Region Boundaries as a review table.

Each Region should be shown as one row.

Recommended Region row columns:

- Region
- Start STA
- End STA
- Assembly
- Structure
- Drainage
- Surface Status
- Boundary Status
- Diagnostics

Region row station rule:

- When a `RegionModel` source object exists, `Start STA` and `End STA` must come from the source `RegionRow`.
- In the Regions editor, users select only `Start STA` from Stationing values.
- `End STA` is derived from the next Region row's `Start STA`; the last row ends at the final Stationing value.
- Region rows should cover the Stationing range without intentional gaps.
- Applied Section samples must not shrink the displayed Region range.
- If Applied Section samples do not cover the source Region start or end, show a warning diagnostic.
- If adjacent source Region rows have a gap or overlap, show a warning diagnostic.
- If no `RegionModel` source object exists, Build Corridor may fall back to Applied Section contiguous `region_id` groups.

Applied Section and Region boundary rule:

- Applied Sections should be generated from Stationing source rows.
- Source Region start positions should be Stationing values selected in the Regions editor.
- Source Region end positions are derived from the next Region start or final Stationing value.
- Transition control stations should not be merged into Applied Sections automatically.
- Build Corridor may create virtual boundary endpoint sections during surface build/review when a shared boundary station is owned by only one active Applied Section Region.
- Virtual boundary sections are output/review context only; they must not be written back into the Applied Section source result.
- Surface Transition spacing should remain Build Corridor surface-build intent, not Applied Section source intent.

Double-click behavior:

- double-clicking a Region row selects that Region's built object set in the 3D view
- the selected object set should use built Region objects, not focus-time highlight objects
- Build Corridor should create `V1CorridorRegionSurface` output objects per buildable Region and surface role
- surface roles include design, subgrade, slope/daylight, and drainage when available
- Build Corridor should create a `V1CorridorRegionStructure` display object when the Region has active Structure refs
- each object should be linked by `region_id`
- the object set should represent the Region footprint and related surfaces, not only its centerline range
- the display objects should not edit source models or generated surfaces
- the active row should remain selected after returning from 3D view interaction

Recommended 3D display behavior:

- draw start and end station markers
- draw a centerline range segment
- show left/right surface edge preview where available
- use a distinct Region color
- show a compact label with Region id and station range

Region surface object rule:

- `RegionModel` remains source intent and does not become editable geometry
- Build Corridor creates or updates stable `V1CorridorRegionSurface` objects for each buildable reviewed Region
- Build Corridor creates or updates a stable `V1CorridorRegionStructure` object for Structure context in the Region
- the object stores `RegionRef`, station range, section count, surface face count, boundary status, and diagnostics
- the Region Boundaries table double-clicks and `Highlight Region` action select the existing Region object set
- Region row focus must not create temporary single highlight geometry
- the selected Region surface may use a small display Z offset so it remains visible above the full design surface
- a Region with only one sampled Applied Section should still receive a minimal displayable surface object

Recommended actions:

- `Refresh Boundaries`
- `Zoom To Region`
- `Highlight Region`
- `Clear Highlight`
- `Create Transition From Region STA`

`Highlight Region` must select and show the selected Region object set, not create
a separate highlight object. Region surface objects are built from the Region's Applied
Section frames and surface/point offsets. When available, the design surface preview
should remain visible behind the selected Region object set.

Boundary rows should report whether the Region has:

- matching adjacent surface roles
- width jumps at either boundary
- daylight jumps at either boundary
- ditch or bench mismatch at either boundary
- structure or drainage context changes

## 16. Build Corridor Surface Transitions UI

Surface Transitions should be edited in Build Corridor.

Recommended location:

- a `Surface Transitions` table below the Region Boundaries table, or
- a second tab inside the Build Corridor panel

Recommended transition row columns:

- Enabled
- STA
- Spacing
- Sample Count
- From Region
- To Region
- From Surface
- To Surface
- Target Surfaces
- Mode
- Status
- Diagnostics
- Notes

Recommended actions:

- `Update`
- `Apply Transitions`
- `Preview Transition`
- `Remove Transition`
- `Clear Disabled`

Surface Transition authoring should be selected-Region station driven.

Default workflow:

- the user selects a Region row in `Region Boundaries`
- the `Region STA` combo lists every Applied Section station that belongs to the selected Region
- the combo also lists source Region start/end boundary positions
- a combo item may be a local Region station, such as `STA 78.576 | region:2`
- a Region endpoint may still represent a handoff, such as `STA 60.000 | region:1 -> region:2`
- the selected station maps to exactly one `SurfaceTransitionRange.transition_id`
- the user adjusts `sample_interval` for that selected station
- each station-owned `SurfaceTransitionRange` stores its own `sample_interval`
- spacing changes for one station must not modify spacing for another station
- Start STA and End STA are derived from the selected station policy, not edited in the default UI
- raw station range editing is advanced-only and should not be shown in the default Build Corridor panel

When a user selects a Region STA and chooses `Update`, Build Corridor should persist:

- a station range centered on the selected station
- `from_region_ref`
- `to_region_ref`
- default target surfaces
- default transition mode
- the selected station-specific `sample_interval`

`Spacing` is the currently applied transition sample interval.

`Sample Count` is the derived number of transition samples generated from the stored station range and spacing.

Spacing presets may be offered:

- Dense: 1.000 m
- Normal: 2.500 m
- Sparse: 5.000 m
- Custom: user-entered interval

The UI should not expose raw TIN vertices or triangle editing.

## 17. Review Behavior

Build Corridor review should show:

- number of Region boundary spans
- number of transition ranges
- number of transition sections generated
- warnings for unhandled boundary spans
- warnings for unsafe automatic transitions

Surface preview should eventually show:

- normal spans
- Region boundary spans
- transition surface spans
- manual-required spans

## 18. Applied Sections Relationship

Applied Sections should remain upstream of Transition Surface.

Applied Sections responsibilities:

- generate station-wise source/result context
- preserve `region_id`, `assembly_id`, point roles, structure context, and drainage context
- expose enough point rows for surface builders to consume
- optionally show read-only Region context diagnostics

Applied Sections should not be the primary place where users author Transition Surface ranges.

Build Corridor responsibilities:

- detect Region boundaries from Applied Sections
- let users decide where Transition Surface ranges apply
- generate transition sections as surface-build results
- build and preview transition-aware surfaces
- report transition diagnostics

This keeps the boundary clear:

`Applied Sections = evaluated section results`

`Build Corridor = corridor surface/solid build and transition review`

## 19. Output and Exchange Behavior

Surface output should preserve transition context.

Recommended output additions:

- span rows with Region refs
- transition range refs
- transition diagnostics
- surface kind coverage summary

Exchange exporters should consume output contracts.

Do not rebuild transition meaning inside DXF, LandXML, IFC, or SVG exporters.

## 20. Implementation Order

### Phase RST1: Diagnostics Only

Tasks:

- [x] detect adjacent Applied Section Region boundary spans
- [x] compare width, subgrade, daylight, point roles, ditch, bench, and structure context
- [x] emit boundary diagnostics
- [x] show Region Boundaries as one row per Region in Build Corridor
- [x] double-click a Region row to select the Region built surface object in the 3D view
- [x] add contract tests for boundary detection

Acceptance criteria:

- [x] Build Corridor can report Region boundary spans
- [x] Build Corridor can show each Region as a review row
- [x] double-clicking a Region row selects the expected Region footprint object
- [x] diagnostics identify large width/daylight jumps
- [x] diagnostics identify point-role mismatches
- [x] existing surface generation behavior is preserved

### Phase RST2: Span Metadata

Tasks:

- [x] introduce `SurfaceSpanRow` result contract
- [x] attach Region refs and continuity status to surface spans
- [x] map span metadata into `SurfaceOutput`
- [x] add tests for region-ref preservation

Acceptance criteria:

- [x] Surface output can explain which Region owns each span
- [x] Region boundary spans can be filtered or highlighted by consumers

### Phase RST3: Transition Source Model

Tasks:

- [x] add `SurfaceTransitionModel`
- [x] add `SurfaceTransitionRange`
- [x] add validation service for station ranges and modes
- [x] persist transition ranges in a v1 source object
- [x] expose Transition Surface range editing from Build Corridor
- [x] add source model contract tests

Acceptance criteria:

- [x] user-selected transition station ranges round-trip
- [x] user can create a transition range from a selected Region boundary
- [x] invalid ranges produce diagnostics
- [x] transition intent is stored outside generated TIN geometry

### Phase RST4: Transition Section Generation

Tasks:

- [x] link enabled `SurfaceTransitionRange` refs to Region-boundary `SurfaceSpanRow` metadata
- [x] generate deterministic transition sections for `interpolate_width`
- [x] generate deterministic transition sections for `interpolate_matching_roles`
- [x] skip unsafe roles with diagnostics
- [x] feed augmented section rows into surface geometry build
- [x] add tests for generated transition stations and point rows

Acceptance criteria:

- [x] surface span rows identify which Transition Surface range applies
- [x] transition sections are generated only inside enabled ranges
- [x] generated sections preserve source refs and diagnostics
- [x] existing non-transition spans remain unchanged

### Phase RST5: Build Corridor UI and Review

Tasks:

- [x] add Region Boundaries table to Build Corridor
- [x] add Surface Transitions table or tab to Build Corridor
- [x] add boundary detection refresh action
- [x] add 3D Region surface object selection action
- [x] show transition diagnostics in review
- [x] visually distinguish transition spans in surface preview

Acceptance criteria:

- [x] user can select a Region station and adjust its Transition Surface spacing
- [x] user can enable or disable a transition range
- [x] user can inspect a Region footprint object in the 3D view from the Build Corridor table
- [x] user can review why transition generation succeeded or failed

### Phase RST6: Output and Exchange

Tasks:

- [x] include transition span rows in `SurfaceOutput`
- [x] include transition diagnostics in exchange packages
- [x] prepare DXF/SVG consumers to use span metadata

Acceptance criteria:

- [x] exported output can preserve Region boundary and transition context
- [x] exporters do not infer transition meaning from viewer objects

## 21. Testing Plan

Recommended focused tests:

- Region boundary detection with adjacent different `region_id`
- same Region span produces no boundary warning
- Build Corridor Region Boundaries table emits one row per Region
- double-click or activation handler routes selected Region to its 3D built surface object
- width jump diagnostic threshold
- daylight width/slope jump diagnostic threshold
- point-role mismatch diagnostic
- transition range validation
- `interpolate_width` generated sections
- `interpolate_matching_roles` generated sections
- unsafe role mismatch falls back to diagnostics
- surface output preserves `from_region_ref`, `to_region_ref`, and `transition_ref`

Recommended manual QA:

1. Create two Regions with different Assemblies.
2. Build Applied Sections.
3. Build Corridor without transition ranges.
4. Confirm boundary diagnostics are visible.
5. Confirm Build Corridor shows one row per Region.
6. Double-click each Region row and confirm the 3D view selects the expected Region footprint object.
7. Add a Transition Surface range around the boundary from Build Corridor.
8. Rebuild Corridor.
9. Confirm generated transition sections and surface preview behavior.
10. Disable the transition range.
11. Rebuild and confirm the surface returns to direct behavior.

## 22. Non-goals

This plan does not make Transition Surface an editable generated mesh.

This plan does not infer drainage hydraulic meaning from surface transition geometry.

This plan does not automatically solve all Region-to-Region geometry changes.

This plan does not replace explicit transition Regions or Assemblies when engineering intent requires them.

## 23. Final Rule

A Transition Surface range is user-approved source intent for how generated surfaces should bridge a station range.

The generated surface must remain traceable back to:

- the source Regions
- the source Assemblies
- the applied section results
- the transition range record
- the surface build diagnostics
