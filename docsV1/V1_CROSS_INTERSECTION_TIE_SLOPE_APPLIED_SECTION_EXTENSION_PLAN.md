# V1 Cross Intersection Tie Slope Applied Section Extension Plan

Last updated: 2026-07-06

## Purpose

Define the revised source-driven plan for extending `Intersection Tie Slope Surface` in Cross intersections.

The target is to extend Tie Slope panels from the current transition windows inward to the end points of the intersection supplemental Applied Sections.

This intentionally allows Tie Slope panels to enter the curb-return influence area when the source Applied Sections prove that the transition belongs there.

## Problem

The current Cross intersection output can build useful `Intersection Tie Slope Surface` panels along some approach windows, but it still leaves gaps near the curb-return and the rectangular intersection supplemental Applied Section corners.

Earlier attempts treated curb-return interior overlap as something to avoid. That rule is too restrictive for the desired Cross behavior.

For Cross intersections, the user-visible target is:

- use the supplemental Applied Sections that were generated for the intersection
- extend `Intersection Tie Slope Surface` to the supplemental Applied Section end points
- reach the rectangular corner/edge positions near the curb-return area
- keep the surface source-driven and deterministic

## Corrected Core Rule

`Intersection Tie Slope Surface` may enter the curb-return influence area when it is generated from valid intersection supplemental Applied Section rows.

The limit is not the curb-return circle.

The limit is the source/evaluation context:

- same intersection id
- same alignment or leg ownership
- same side
- ordered Applied Section station sequence
- valid side-slope edge rows
- no intrusion into the central pavement/intersection surface ownership area

In short:

> Do not use curb-return geometry as a hard clipping boundary for Tie Slope. Use intersection supplemental Applied Section extent as the Tie Slope reach boundary.

## Non-Goals

- Do not use generated TIN mesh, preview objects, or tree objects as source truth.
- Do not infer Tie Slope from already-created `Intersection Slope Face Surface` triangles.
- Do not restore the earlier broad internal rectangular patches.
- Do not merge ordinary `Slope Face Surface`, `Intersection Slope Face Surface`, and `Intersection Tie Slope Surface`.
- Do not use Intersections-tab highlight geometry as input.
- Do not build synthetic fallback panels when Applied Section edge data is missing.

## Source Inputs

Required:

- `IntersectionModel`
- participating leg/alignment refs
- `AppliedSectionSet`
- station-ordered Applied Section rows
- `active_intersection_id`
- supplemental/source Applied Section classification
- side-slope boundary or terminal edge rows for each side

Preferred:

- control-area refs
- leg refs
- road role, for example `primary` and `secondary`
- transition role, for example `entry` and `exit`
- shared breakline result rows for accepted Tie Slope windows

Diagnostic-only:

- curb-return boundary segment metadata
- existing `Intersection Slope Face Surface` and ordinary `Slope Face Surface` preview metadata
- Breakline Audit notes

## Design Direction

For every Cross intersection leg and side:

1. Collect Applied Sections for the participating alignment.
2. Sort by station.
3. Identify the first and last Applied Sections that belong to the target intersection.
4. Identify supplemental Applied Sections inside that intersection range.
5. Build Tie Slope windows from the ordinary/intersection transition toward the supplemental Applied Section end point nearest the curb-return influence area.
6. Repeat independently for:
   - primary entry left/right
   - primary exit left/right
   - secondary entry left/right
   - secondary exit left/right

The generated object remains:

`Intersection Tie Slope Surface`

## Target Geometry Meaning

The desired Cross behavior is not a circular curb-return fill.

It is a set of Applied Section strip cells that reach the intersection supplemental Applied Section end points.

Each cell is a quadrilateral strip between two adjacent Applied Sections:

- outer boundary: previous Applied Section side-slope edge
- inner boundary: next Applied Section side-slope edge
- start/end caps: side edges connecting the two section boundaries

The final accepted strip in each direction may lie inside the curb-return influence area if both boundaries are owned by intersection supplemental Applied Sections.

## Candidate Row Roles

Keep using accepted Applied Section window rows, but refine Cross semantics.

Recommended roles:

- `transition_pair`
  - ordinary Applied Section to first intersection Applied Section
- `intersection_supplemental_pair`
  - pair between adjacent intersection supplemental Applied Sections
- `supplemental_endpoint_pair`
  - final pair reaching the intersection supplemental end point nearest the curb-return/rectangular corner

Avoid reusing `intersection_adjacent_pair` for visible Cross output unless it is explicitly redefined and guarded. The old meaning produced unwanted internal rectangular patches.

Each candidate row should record:

- `intersection_id`
- `intersection_kind`
- `alignment_ref`
- `road_role`
- `leg_ref`
- `side`
- `transition_role`
- `cell_role`
- `outer_applied_section_ref`
- `inner_applied_section_ref`
- `outer_station`
- `inner_station`
- `outer_edge_xyz`
- `inner_edge_xyz`
- `loop_points_xyz`
- `loop_area_xy`
- `is_supplemental_outer`
- `is_supplemental_inner`
- `status`
- diagnostics

## Selection Algorithm

For each participating alignment:

1. Build `sections` from `AppliedSectionSet.sections`.
2. Keep only sections matching the target alignment.
3. Keep only sections with usable side-slope edge points for the requested side.
4. Sort by station.
5. Mark sections with `active_intersection_id == target intersection`.
6. Inside the active intersection span, identify supplemental Applied Sections.
7. For each entry direction:
   - start at the ordinary-to-intersection transition pair
   - walk inward through adjacent active-intersection section pairs
   - stop at the supplemental Applied Section end point intended for the curb-return-adjacent rectangular corner
8. For each exit direction:
   - start at the intersection-to-ordinary transition pair
   - walk inward in the opposite station direction
   - stop at the matching supplemental Applied Section end point
9. Reject any pair that changes alignment, side, leg ownership, or target intersection id.

The first implementation may use a bounded walk count, but it must report when the selected end point was limited by the cap.

## Acceptance Rules

A row can become visible geometry only if:

- both Applied Sections are from the same alignment
- both edges exist for the same side
- at least one section is active for the target intersection
- the station order matches the entry/exit direction
- the loop has four valid corners
- the loop area is positive
- the loop does not self-cross
- the loop span is local compared with the station spacing
- the loop does not overlap the central pavement/intersection surface ownership polygon

Important correction:

- the loop may overlap the curb-return influence area
- the loop may reach inside the curb-return circle
- this is accepted only when the inner boundary is an intersection supplemental Applied Section edge

## Shared Breakline Rule

Every accepted cell must emit shared breakline rows.

Suggested roles:

- `intersection_tie_slope_transition_outer`
- `intersection_tie_slope_transition_inner`
- `intersection_tie_slope_supplemental_outer`
- `intersection_tie_slope_supplemental_inner`
- `intersection_tie_slope_supplemental_endpoint`
- `intersection_tie_slope_start_cap`
- `intersection_tie_slope_end_cap`

The shared breakline refs must be tied to Applied Section window rows and source/result contract refs, not preview geometry.

Breakline Audit should make it clear when a Tie Slope edge is:

- shared with ordinary `Slope Face Surface`
- shared with `Intersection Slope Face Surface`
- local to another `Intersection Tie Slope Surface` cell
- an endpoint cap at the intersection supplemental boundary

## Implementation Phases

### Phase XITS-001 - Remove Obsolete Cross Tie-Slope Assumptions

- Remove or quarantine code that treats curb-return interior as an automatic Tie Slope rejection condition.
- Keep protection against central pavement/intersection surface intrusion.
- Keep old broad internal rectangular-patch generation disabled.

Acceptance:

- No code path rejects a valid Cross Tie Slope candidate only because it is inside the curb-return influence area.
- Old rectangular internal patches do not return.

### Phase XITS-002 - Supplemental Applied Section Extent Diagnostics

- Add diagnostics that list, per alignment/side:
  - first active intersection section
  - last active intersection section
  - supplemental section count
  - selected supplemental endpoint section
  - rejected reason if no endpoint is found

Acceptance:

- Intersections or Results notes show the selected supplemental endpoint refs.
- Manual QA can compare those refs against visible Applied Section preview rows.

### Phase XITS-003 - Candidate Window Expansion

- Extend accepted Cross Tie Slope candidate generation beyond the first transition window.
- Walk through adjacent active-intersection Applied Section pairs until the selected supplemental endpoint is reached.
- Generate `intersection_supplemental_pair` and `supplemental_endpoint_pair` rows.

Acceptance:

- Candidate row count increases for Cross intersections.
- Rows remain leg/side/station ordered.
- Rejected rows include explicit diagnostics.

### Phase XITS-004 - Surface Generation

- Promote accepted supplemental window rows into `Intersection Tie Slope Surface` triangles.
- Generate two triangles per valid quadrilateral window.
- Preserve separate output object ownership.

Acceptance:

- `Intersection Tie Slope Surface` extends to the rectangular supplemental Applied Section corners.
- Curb-return-adjacent gaps are reduced without creating remote panels.
- No central intersection pavement intrusion is observed.

### Phase XITS-005 - Shared Breakline Handoff

- Add shared breakline rows for the new supplemental and endpoint cells.
- Add consumed refs to the Tie Slope output surface.
- Update Breakline Audit role summaries.

Acceptance:

- Breakline Audit reports zero geometry mismatch, mesh mismatch, and missing consumer for accepted rows.
- The endpoint cap role is visible and traceable.

### Phase XITS-006 - Regression Tests

- Add focused FreeCADCmd tests for Cross:
  - primary entry/exit extension
  - secondary entry/exit extension
  - supplemental endpoint selected
  - no old rectangular internal patch role emitted
  - no central surface overlap
  - accepted shared breakline roles exist

Acceptance:

- Cross smoke passes.
- Existing T intersection Tie Slope behavior is unchanged.

### Phase XITS-007 - Manual QA

Manual checks:

1. Create Cross Intersection preset.
2. Build Applied Sections with supplemental rows enabled.
3. Show Applied Section preview.
4. Build Parametric.
5. Enable:
   - `Intersection Surface`
   - `Intersection Slope Face Surface`
   - `Intersection Tie Slope Surface`
   - Applied Section preview
6. Confirm Tie Slope reaches the intersection supplemental Applied Section rectangular corner/end point.
7. Confirm Tie Slope may enter curb-return influence area where supplemental sections support it.
8. Confirm central pavement/intersection surface is not covered by Tie Slope.
9. Confirm ordinary `Slope Face Surface`, `Intersection Slope Face Surface`, and `Intersection Tie Slope Surface` remain distinct.
10. Check Breakline Audit for mismatch counts.

Acceptance:

- The gaps shown near Cross curb-return/rectangular corners are visibly reduced.
- The previous unwanted internal rectangular patches do not return.

## Risks

- Applied Section supplemental density may not include a usable endpoint near every curb-return corner.
- Cross skew or unequal road widths may require per-leg endpoint selection rather than fixed walk counts.
- Side-slope edge orientation may flip between legs.
- A supplemental endpoint may visually sit inside the curb-return circle but still conflict with central pavement ownership; this must remain rejected.

## Fallback Policy

Fallbacks are diagnostic only.

If the supplemental endpoint cannot be selected, report:

`intersection_tie_slope_supplemental_endpoint_missing`

If a selected endpoint would overlap central pavement ownership, report:

`intersection_tie_slope_supplemental_endpoint_intrudes_central_surface`

Do not create synthetic geometry from preview objects.

## Current Status

- [x] XITS-001 - Remove obsolete Cross Tie-Slope assumptions
- [x] XITS-002 - Supplemental Applied Section extent diagnostics
- [x] XITS-003 - Candidate window expansion
- [x] XITS-004 - Surface generation
- [x] XITS-005 - Shared breakline handoff
- [x] XITS-006 - Regression tests
- [ ] XITS-007 - Manual QA

## Implementation Notes

### 2026-07-06 - XITS-001/XITS-002

- Confirmed that the current Cross Tie Slope approach walker does not use curb-return influence as a hard rejection boundary.
- Added supplemental Applied Section extent diagnostics to Cross approach rows.
- Existing `curb_return_approach_pair` rows now also expose:
  - `supplemental_extent_role`
  - `supplemental_endpoint_ref`
  - `supplemental_endpoint_station`
  - `outer_is_supplemental`
  - `inner_is_supplemental`
- Informational diagnostics are prefixed with `info:` so accepted geometry rows do not become warnings only because trace metadata is present.
- Kept the legacy `curb_return_approach_pair` role name for compatibility. XITS-003 can introduce the refined `intersection_supplemental_pair` and `supplemental_endpoint_pair` roles after the endpoint selection is validated.

### 2026-07-06 - XITS-003

- Replaced the fixed three-pair Cross approach walk with a source-driven walk to the furthest valid supplemental Applied Section endpoint in the selected direction.
- The walker remains bounded by same alignment, same intersection id, same side edge availability, and same control-area context.
- If no supplemental endpoint is available, the walker falls back to a short diagnostic-compatible window instead of generating synthetic endpoint geometry.
- Kept `cell_role=curb_return_approach_pair` for existing surface/breakline compatibility, and exposed the refined meanings through:
  - `supplemental_extent_role=intersection_supplemental_pair`
  - `supplemental_extent_role=supplemental_endpoint_pair`
- Added regression coverage that verifies endpoint rows stop on supplemental Applied Sections.

### 2026-07-06 - XITS-004

- Promoted accepted supplemental/endpoint Applied Section window rows into the existing dedicated `Intersection Tie Slope Surface` TIN path.
- Fixed the surface builder so informational diagnostics prefixed with `info:` do not reject otherwise accepted window rows.
- Added TIN quality rows for:
  - `intersection_tie_slope_window_supplemental_endpoint_count`
  - `intersection_tie_slope_window_supplemental_inner_count`
- Exposed those counts on the preview object as:
  - `IntersectionTieSlopeSupplementalEndpointCount`
  - `IntersectionTieSlopeSupplementalInnerCount`
- Added regression coverage that verifies supplemental endpoint rows are consumed by the preview surface and that each accepted window still triangulates as two triangles.

### 2026-07-06 - XITS-005

- Added supplemental and endpoint-aware shared breakline roles for accepted Cross Tie Slope window rows:
  - `intersection_tie_slope_supplemental_outer`
  - `intersection_tie_slope_supplemental_inner`
  - `intersection_tie_slope_supplemental_endpoint`
  - `intersection_tie_slope_supplemental_start_cap`
  - `intersection_tie_slope_supplemental_end_cap`
- The TIN boundary refs and Shared Breakline rows now use the same row-role resolver so surface metadata and Breakline Audit stay aligned.
- Fixed shared breakline handoff so informational `info:` diagnostics do not reject otherwise accepted window rows.
- Added regression coverage for supplemental shared breakline role emission.

### 2026-07-06 - XITS-006

- Extended Cross regression smoke to verify:
  - primary and secondary road endpoint windows exist for entry/exit and both sides
  - intermediate supplemental Applied Section pair rows exist
  - endpoint rows stop on supplemental Applied Sections
  - endpoint rows expose selected supplemental endpoint refs
  - old Cross `intersection_adjacent_pair` rows do not return
  - supplemental endpoint rows are consumed by the dedicated preview surface
  - supplemental shared breakline roles are emitted
- Extended T regression smoke to verify that Cross-only supplemental shared breakline roles do not appear in T intersection output.
- Verified both focused FreeCADCmd smoke tests after the assertions were added.

### 2026-07-06 - Manual QA Correction: Control-Area Walk Boundary

- Manual QA showed that Cross Intersection Tie Slope became smaller after XITS-003.
- Root cause: the supplemental Applied Section walker stopped whenever adjacent Applied Sections changed `active_intersection_control_area_id`.
- That guard was too strict for Cross intersections because the target supplemental endpoint can legitimately sit across a control-area boundary while still belonging to the same alignment, same intersection, and same side-slope edge chain.
- Relaxed the hard same-control-area stop.
- Kept the source-driven safety boundary at:
  - same alignment
  - same intersection id
  - same side edge availability
  - station-adjacent Applied Section order
- Added trace metadata for allowed control-area transitions:
  - `outer_control_area_ref`
  - `inner_control_area_ref`
  - `control_area_transition_allowed`
  - `info:intersection_tie_slope_control_area_transition_allowed:<outer>-><inner>`
- Added `control_area_transitions=<count>` to the Tie Slope window summary note so manual QA can confirm whether the extension crossed a control-area boundary.

### 2026-07-06 - Rejected Attempt: Boundary Cap Consumption

- A Cross-only attempt consumed `corridor_intersection_tie_slope_result()` local boundary cap loops directly into the visible `Intersection Tie Slope Surface`.
- Manual QA rejected this direction.
- Problem: the cap loops connect curb-return boundary segments directly to Applied Section terminal edges and create large fan/wedge surfaces.
- This does not match the intended behavior.
- The intended behavior remains Applied Section based:
  - find the intersection supplemental Applied Section range
  - extend Tie Slope by adjacent Applied Section cells
  - do not add direct curb-return-boundary-to-road-edge fan caps
- The boundary cap consumption code and preview property were removed.

### 2026-07-06 - Cleanup: Cross Adjacent Pair Suppression

- Removed Cross `intersection_adjacent_pair` candidate generation from the non-zero transition-span path.
- Reason: for Cross intersections this row duplicates the first `curb_return_approach_pair` span and reintroduces the older internal-adjacent patch ambiguity.
- Cross Tie Slope candidates should be expressed as:
  - `transition_pair`
  - `curb_return_approach_pair`
  - `supplemental_extent_role=intersection_supplemental_pair`
  - `supplemental_extent_role=supplemental_endpoint_pair`
- Manual QA should no longer see `intersection_adjacent_pair` in Cross `intersection_tie_slope_window` notes.
