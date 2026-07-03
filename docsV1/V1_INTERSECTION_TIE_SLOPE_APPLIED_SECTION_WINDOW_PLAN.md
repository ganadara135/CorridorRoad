# V1 Intersection Tie Slope Applied Section Window Plan

Last updated: 2026-07-03

## Purpose

Define a simpler source-driven plan for `Intersection Tie Slope Surface`.

The new rule is:

- find where Applied Sections enter or leave an active Intersection
- use the adjacent Applied Sections before and after that transition
- build local Tie Slope cells from those Applied Section side-slope edges
- do not use Intersection internal edges, edge-network preview, boundary-loop preview, surface-zone mesh, or generated surfaces as source truth

This replaces the earlier over-complex Region/control-area and boundary-loop driven attempts for this specific transition surface.

## Scope

This plan applies to the small side-slope transition strips between:

- ordinary road Applied Sections
- intersection-active Applied Sections

It covers both primary and secondary roads.

It does not cover:

- central pavement patch generation
- curb-return interior filling
- ordinary corridor `Slope Face Surface`
- dedicated curb-return `Intersection Slope Face Surface`
- drainage or edge-network visualization

## Core Rule

`Intersection Tie Slope Surface` is generated only from Applied Section context transitions.

For each alignment:

1. Sort Applied Sections by station.
2. Find the first adjacent pair where `active_intersection_id` changes from empty/non-target to the target intersection id.
3. Find the first adjacent pair where `active_intersection_id` changes from the target intersection id to empty/non-target.
4. For each transition, use one Applied Section pair at the transition and one additional pair toward the intersection side.
5. Build left and right Tie Slope cells from Applied Section side-slope edges.

## Design Goals

- Keep the rule explainable to users.
- Avoid reconstructing Tie Slope from generated meshes.
- Avoid using Intersection internal geometry as the Tie Slope source.
- Avoid broad fan triangles and remote Alignment-side panels.
- Keep Primary and Secondary roads on the same algorithm.
- Preserve the current successful Applied Section window location.
- Make surface generation a direct promotion of accepted Applied Section window cells.

## Object Families

### Candidate Result

Add a result contract such as `IntersectionTieSlopeWindowResult`.

Each row should represent one local cell candidate.

Required row fields:

- `candidate_id`
- `intersection_id`
- `alignment_ref`
- `road_role`
- `transition_role`
- `side`
- `cell_role`
- `outer_applied_section_ref`
- `inner_applied_section_ref`
- `outer_station`
- `inner_station`
- `outer_edge_xyz`
- `inner_edge_xyz`
- `start_cap_edge_xyz`
- `end_cap_edge_xyz`
- `loop_points_xyz`
- `loop_area_xy`
- `status`
- `diagnostics`

Suggested `transition_role` values:

- `entry`
- `exit`

Suggested `cell_role` values:

- `transition_pair`
- `intersection_adjacent_pair`

### Highlight Preview

The temporary `Intersection Tie Slope Transition Gap Highlight` review object is no longer needed after the generated `Intersection Tie Slope Surface` became available.

Candidate rows should remain source/result metadata consumed by the generated surface and review rows, not by a separate highlight object.

### Surface Output

A visible `Intersection Tie Slope Surface` should be created only after candidate rows are accepted.

It must remain separate from:

- ordinary `Slope Face Surface`
- dedicated `Intersection Slope Face Surface`

## Implementation Order

| ID | Status | Task | Acceptance Criteria |
| --- | --- | --- | --- |
| ITS-WIN-001 | Superseded | Preserve current highlight behavior. | The temporary cyan highlight was used to confirm Applied Section transition locations and has now been removed. |
| ITS-WIN-002 | Complete | Remove or quarantine ineffective Region/control-area Tie Slope generation attempts. | Legacy single-station Tie Slope surface generation remains disabled while the Applied Section window path is isolated as source/result candidate logic. |
| ITS-WIN-003 | Complete | Add Applied Section transition scanner. | `_intersection_tie_slope_applied_section_window_rows` now returns entry/exit transition rows by detecting `active_intersection_id` changes in station order. |
| ITS-WIN-004 | Complete | Add one intersection-adjacent pair per transition. | Each transition can report `transition_pair` and `intersection_adjacent_pair` window rows for surface and review QA. |
| ITS-WIN-005 | Complete | Build candidate rows from Applied Section side-slope edges. | Window rows now carry Applied Section side-slope outer/inner edges, start/end cap edges, loop points, loop area, status, and diagnostics without using Intersection internal geometry. |
| ITS-WIN-006 | Complete | Validate candidate loops. | Window rows now run loop safety diagnostics for missing edges, open loops, zero area, self-crossing loops, and long-fan geometry before they can be accepted as surface candidates. |
| ITS-WIN-007 | Superseded | Move highlight rendering to candidate rows. | The temporary highlight path has been removed. Accepted Applied Section window rows now feed the generated `Intersection Tie Slope Surface` directly. |
| ITS-WIN-008 | Complete | Expose candidate diagnostics in Results and Intersections. | Results and Intersections rows now report Applied Section window candidate counts, accepted/warning counts, source mode, cell-role counts, and diagnostics. |
| ITS-WIN-009 | Complete | Generate `Intersection Tie Slope Surface` from accepted rows only. | `V1CorridorIntersectionTieSlopeSurfacePreview` now triangulates accepted Applied Section window rows and records `IntersectionTieSlopeGeometrySource=accepted_applied_section_window_rows`. |
| ITS-WIN-010 | Complete | Add shared breakline roles for accepted cells. | Accepted Applied Section window cells now emit `intersection_tie_slope_window_outer`, `intersection_tie_slope_window_inner`, `intersection_tie_slope_window_start_cap`, and `intersection_tie_slope_window_end_cap` shared breaklines consumed by `intersection_tie_slope`. |
| ITS-WIN-011 | Complete | Update Breakline Audit. | Breakline Audit now exposes a compact `intersection_tie_slope_window` handoff row with source mode, consumed role counts, and missing-role status while preserving source/result contract refs. |
| ITS-WIN-012 | Complete | Update FreeCADCmd smoke. | Regression now verifies accepted surface rows, shared breakline handoff, bounded surface envelopes, two-triangle window cells, consistent winding, and absence of broad fan panels. |
| ITS-WIN-013 | Complete | Update manual QA. | QA now describes how to verify the Applied Section window method from top and bottom views, including Results, Intersections, Breakline Audit, visibility, and failure interpretation checks. |

## Candidate Selection Algorithm

For each alignment participating in the intersection:

1. Build `sections = AppliedSections where alignment_id == target alignment`.
2. Keep only sections that have usable side-slope edge points for the requested side.
3. Sort by station.
4. Scan adjacent pairs:
   - `ordinary -> intersection`: entry transition
   - `intersection -> ordinary`: exit transition
5. For entry:
   - `transition_pair = ordinary_before -> intersection_start`
   - `intersection_adjacent_pair = intersection_start -> next_intersection_section`
6. For exit:
   - `transition_pair = intersection_end -> ordinary_after`
   - `intersection_adjacent_pair = previous_intersection_section -> intersection_end`
7. Repeat for left and right sides.

The algorithm must not sample or infer from generated TIN triangles.

## Acceptance Rules

A candidate row can become `accepted` only when:

- both Applied Sections are from the same alignment
- the pair is adjacent in station order after filtering for usable side-slope edges
- at least one section in the pair has the target `active_intersection_id`
- the pair follows the transition role direction
- left/right side-slope edge points are present
- the loop has four meaningful edges
- the loop area is positive
- the loop is local to the transition window
- the loop centroid is not inside the central patch interior
- the loop centroid is not inside curb-return interior
- the loop does not create a long fan away from the intersection

Rows that fail these checks must remain diagnostic and must not generate visible surface triangles.

## Shared Breakline Plan

For accepted candidate cells:

- `outer_edge` is shared with ordinary `Slope Face Surface` when adjacent to ordinary corridor.
- `inner_edge` is shared with `Intersection Slope Face Surface` or the adjacent Tie Slope cell.
- `start_cap` and `end_cap` are shared with neighboring candidate cells or remain boundary caps.

Suggested roles:

- `intersection_tie_slope_window_outer`
- `intersection_tie_slope_window_inner`
- `intersection_tie_slope_window_start_cap`
- `intersection_tie_slope_window_end_cap`

These roles should be source/result contract refs, not preview-object refs.

## UI and Review Plan

### Results Tab

Add or update `Intersection Tie Slope Surface` result row:

- status: `missing`, `warning`, or `ready`
- notes include candidate count, accepted count, rejected count
- notes state that the source is Applied Section transition windows

### Intersections Tab

Expose only user-meaningful rows:

- `intersection_tie_slope_window`

Do not expose low-level edge-network, surface-zone, or preview-derived rows as generation sources.

### Visibility Tab

Keep separate toggles:

- `Intersection Slope Face Surface`
- `Intersection Tie Slope Surface`

Temporary `Intersection Tie Slope Highlight` review objects are no longer generated.

## Manual QA

### Setup

1. Create a T-intersection preset.
2. Build Applied Sections.
3. Build Parametric.
4. In Visibility, enable:
   - `Intersection Surface`
   - `Intersection Slope Face Surface`
   - `Intersection Tie Slope Surface`
   - `Slope Face Surface`
   - `Breaklines` or diagnostics only when inspecting handoff rows

### Expected Objects

After Build Parametric, confirm these objects or rows exist:

- `V1CorridorIntersectionTieSlopeSurfacePreview`
- label similar to `Intersection Tie Slope - intersection:<id>`
- `V1CorridorIntersectionTieSlopeSurfacePreview`
- Results row `Intersection Tie Slope Surface`
- Intersections row `intersection_tie_slope_window`
- Breakline Audit row `Intersection Tie Slope Window Handoff`

The surface object should report:

- `IntersectionTieSlopeGeometrySource=accepted_applied_section_window_rows`

The generated surface must use the accepted Applied Section window source. No separate highlight object should be created or used as source truth.

### Top View Checks

Confirm each participating road has local transition cells at:

- ordinary-to-intersection entry
- one adjacent Applied Section pair toward the intersection
- intersection-to-ordinary exit
- one adjacent Applied Section pair toward the intersection

The accepted cells should fill only the small road/intersection transition windows that sit between ordinary corridor slope face and intersection slope face.

Reject the result if any of these are visible:

- cells inside the central pavement patch
- cells inside curb-return interiors
- broad fan panels pointing toward Alignment or remote station geometry
- long disconnected panels outside the local Applied Section window
- panels that cross through the intersection center instead of following the local side-slope boundary

### Bottom View Checks

Inspect from below as well as from top view.

Expected:

- each accepted rectangular window is triangulated as two local triangles
- the underside footprint matches the top-view footprint
- no hidden large triangular sheet exists under the intersection
- no orphan panel is attached to Alignment, edge-network review geometry, or preview-only objects

### Shared Boundary Checks

In Breakline Audit, inspect `Intersection Tie Slope Window Handoff`.

Expected:

- source mode is `applied_section_context_transition_window`
- `missing_roles=none`
- outer boundary aligns with ordinary `Slope Face Surface`
- inner boundary aligns with `Intersection Slope Face Surface` or the next accepted Tie Slope cell
- start and end caps are local caps between the two Applied Section rows
- shared boundaries are source/result contract refs, not preview-object refs

### Results And Diagnostics Checks

In the Results tab:

- `Intersection Tie Slope Surface` should be `ready` when accepted window rows are present.
- Notes should include candidate, accepted, and rejected counts.
- Notes should state that the source is Applied Section transition windows.

In the Intersections tab:

- user-facing Tie Slope rows should be shown as `intersection_tie_slope_window`.
- low-level edge-network, surface-zone, and preview-derived rows should not be required for generation review.

### Failure Interpretation

If candidate notes exist but the surface is missing:

- inspect the Results row for accepted count.
- inspect the Intersections row for rejected window notes.
- do not patch the gap from generated surface triangles.

If Breakline Audit reports missing roles:

- rebuild Applied Sections first.
- then rebuild Build Parametric.
- inspect whether the transition window lost one of outer, inner, start cap, or end cap boundaries.

If panels appear on the Alignment side or form broad fan shapes:

- reject the result.
- check whether a row used edge-network, boundary-loop, or preview geometry instead of accepted Applied Section window rows.
- check whether the row crossed an intersection context boundary instead of using only adjacent Applied Section pairs.

If cells appear inside the central patch or curb-return interior:

- reject the result.
- the candidate selector is consuming intersection-internal geometry instead of ordinary-to-intersection transition windows.

### Acceptance

Manual QA passes when:

- Results reports `Intersection Tie Slope Surface` as `ready`.
- The generated surface envelope remains local to the expected Tie Slope windows in top and bottom views.
- Tie Slope cells appear only in the local transition windows around each road/intersection contact.
- Breakline Audit reports `missing_roles=none` for `Intersection Tie Slope Window Handoff`.
- No central patch, curb-return interior, remote Alignment, or broad fan filler panels are created.

## Non-goals

- Do not solve all intersection boundary-loop sharing in this plan.
- Do not use generated mesh triangles as source.
- Do not revive edge-network preview as a source.
- Do not merge ordinary `Slope Face Surface` and `Intersection Tie Slope Surface`.
- Do not create synthetic ready loops to pass tests.

## Next Step

Run the Manual QA checklist in FreeCAD.

If QA fails, fix the accepted Applied Section window scanner or row acceptance diagnostics first. Do not patch the gap from generated meshes or preview objects.
