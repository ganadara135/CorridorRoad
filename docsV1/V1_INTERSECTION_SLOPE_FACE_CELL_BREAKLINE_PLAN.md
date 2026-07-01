# V1 Intersection Slope Face Cell Breakline Plan

Date: 2026-06-29  
Status: Done  
Scope: rebuild `Intersection Slope Face Surface` from source-owned slope-face cells and shared breakline boundaries

## Purpose

This plan replaces the current strip/fan patching approach around intersections with a cell-based ownership model.

The immediate visual QA state is:

- the false rectangular patches under the curb-return interior have been removed
- the upper side of the intersection now exposes three visible gap areas
- the main-road / side-road contact area still does not behave as a shared-boundary surface system
- shared breakline metadata exists, but it is not yet the source of the dedicated `Intersection Slope Face Surface` cells

The goal is to make each intersection-owned slope-face area a closed, source-traceable cell whose boundaries are shared breaklines consumed by adjacent surfaces.

## Core Rule

Do not fill gaps by widening triangles.

Every visible `Intersection Slope Face Surface` triangle must belong to an explicit cell.

Each cell must be derived from:

- `IntersectionModel`
- `IntersectionTopologyResult`
- `IntersectionEdgeNetworkResult`
- `IntersectionSurfaceZoneResult`
- `IntersectionBoundarySegmentResult`
- `IntersectionSlopeFaceBoundaryResult`
- Applied Section side-slope/daylight rows
- `SharedBreaklineResult`

Generated preview meshes, highlight geometry, and existing surface fragments must not become source truth.

## Current Failure

### 1. Upper Gap Count Increased

The upper side now has three gaps instead of the earlier two.

Reason:

- lower/side temporary strips were suppressed correctly
- but the remaining upper transition is still represented as one broad strip row
- the strip does not know the actual ownership cells between:
  - left ordinary corridor slope face
  - left upper transition
  - central intersection patch edge
  - right upper transition
  - right ordinary corridor slope face

### 2. Main / Side Road Contact Boundary Is Not Shared Enough

The current shared breakline metadata proves some breakline refs are consumed.

It does not yet prove that the main-road slope-face cells and side-road slope-face cells meet on the same boundary.

The missing piece is a shared breakline family for the intersection slope-face cell sides.

### 3. Temporary Boundary Strips Are Still Too Coarse

The current `IntersectionSlopeFaceBoundaryResult` row can describe a long boundary strip.

That is not enough for intersection slope-face completion.

The builder needs smaller cells with explicit left/right tie boundaries, otherwise it cannot know which parts are slope-face ownership and which parts are pavement, shoulder, curb-return, or ordinary corridor ownership.

## Desired Ownership Model

`Intersection Slope Face Surface` owns only slope-face transition cells inside the intersection influence area.

It must not own:

- central pavement
- curb-return pavement interior
- ordinary corridor slope face outside the intersection influence boundary
- design/shoulder surface cells

Adjacent surface ownership:

| Boundary | Surface A | Surface B |
| --- | --- | --- |
| patch-to-intersection-slope-face | `Intersection Surface` | `Intersection Slope Face Surface` |
| intersection-slope-to-corridor-slope | `Intersection Slope Face Surface` | ordinary `Slope Face Surface` |
| intersection-slope-to-design | `Intersection Slope Face Surface` | `Design Surface` / shoulder |
| main-side-slope-tie | main-road intersection slope cell | side-road intersection slope cell |
| curb-return-to-intersection-slope | curb-return perimeter | `Intersection Slope Face Surface` |

## New Result Contract

Add a dedicated result contract:

`IntersectionSlopeFaceCellResult`

### Row Fields

Each `IntersectionSlopeFaceCellRow` should include:

- `cell_id`
- `intersection_id`
- `cell_role`
- `alignment_ref`
- `leg_ref`
- `side`
- `inner_breakline_ref`
- `outer_breakline_ref`
- `left_breakline_ref`
- `right_breakline_ref`
- `arc_breakline_ref`
- `source_applied_section_refs`
- `source_intersection_refs`
- `consumer_surface_ref`
- `status`
- `diagnostics`
- `notes`

### Cell Roles

Required first roles:

- `upper_left_transition_cell`
- `upper_mid_transition_cell`
- `upper_right_transition_cell`
- `main_to_side_left_tie_cell`
- `main_to_side_right_tie_cell`
- `curb_return_left_perimeter_cell`
- `curb_return_right_perimeter_cell`

Optional future roles:

- `skew_upper_transition_cell`
- `multi_leg_transition_cell`
- `island_transition_cell`

## Shared Breakline Families To Add

### 1. `patch_to_intersection_slope_face`

Boundary between central `Intersection Surface` and dedicated `Intersection Slope Face Surface`.

Consumer refs:

- `intersection_surface`
- `intersection_slope_face_surface`

### 2. `intersection_slope_face_to_corridor_slope_face`

Boundary between dedicated intersection slope face and ordinary corridor slope face.

Consumer refs:

- `intersection_slope_face_surface`
- `slope_face_surface`

### 3. `intersection_slope_face_to_design_surface`

Boundary between dedicated intersection slope face and design/shoulder surface.

Consumer refs:

- `intersection_slope_face_surface`
- `design_surface`

### 4. `main_side_slope_face_tie`

Boundary where main-road and side-road intersection slope-face cells meet.

Consumer refs:

- `intersection_slope_face_surface`

This is an internal cell seam for the dedicated surface, but it must still be traceable.

### 5. `curb_return_to_intersection_slope_face`

Boundary between curb-return perimeter and dedicated slope-face cells.

Consumer refs:

- `intersection_surface`
- `intersection_slope_face_surface`

## Implementation Phases

### Phase 1 - Contract Definition

Status: Done

Tasks:

- add `IntersectionSlopeFaceCellRow`
- add `IntersectionSlopeFaceCellResult`
- keep the contract under `models/result`
- add source refs and diagnostics fields

Progress:

- Added `IntersectionSlopeFaceCellRow`.
- Added `IntersectionSlopeFaceCellResult`.
- Added contract coverage for ready closed cells and open missing-edge cells.

Acceptance criteria:

- the result can represent a closed cell without generating geometry
- missing cell edges are reported diagnostically
- no preview mesh is used as source

### Phase 2 - Shared Breakline Role Expansion

Status: Done

Tasks:

- extend `corridor_intersection_shared_breakline_result`
- add the new breakline roles listed above
- map each breakline to explicit consumer refs
- preserve Applied Section and Intersection source refs

Acceptance criteria:

- T intersection produces shared breakline rows for:
  - upper transition boundaries
  - main/side tie boundaries
  - curb-return-to-intersection-slope boundaries
- Breakline Audit can list the new roles

Progress:

- Added shared breakline role rows for `patch_to_intersection_slope_face`.
- Added shared breakline role rows for `intersection_slope_face_to_corridor_slope_face`.
- Added shared breakline role rows for `intersection_slope_face_to_design_surface`.
- Added shared breakline role rows for `curb_return_to_intersection_slope_face`.
- Added `main_side_slope_face_tie` shared breakline rows.
- Kept these rows traceable to `intersection_slope_face_cell_result`.
- T-intersection smoke now validates the required shared breakline role families.

### Phase 3 - Cell Builder

Status: Done

Tasks:

- build `IntersectionSlopeFaceCellResult` from shared breakline rows
- create separate upper cells instead of one long strip
- create main/side tie cells around the side-road contact
- reject cells that overlap central pavement or curb-return interior
- report gaps as missing cell edges

Acceptance criteria:

- the upper three gaps are represented as explicit cells
- no cell is created inside the curb-return pavement interior
- each ready cell has a closed boundary loop

Progress:

- Added `corridor_intersection_slope_face_cell_result`.
- The builder groups `patch_to_intersection_slope_face`, `intersection_slope_face_to_corridor_slope_face`, and `intersection_slope_face_to_design_surface` rows into upper transition cell candidates.
- The builder reports open cells and missing cell edges through `IntersectionSlopeFaceCellResult`.
- Added `main_side_slope_face_tie` shared breakline rows from side-road tie-in boundary segments.
- Added `main_to_side_left_tie_cell` / `main_to_side_right_tie_cell` candidates from main/side tie and curb-return breaklines.
- Main/side tie fallback records a diagnostic when primary alignment must be inferred.
- Current T-intersection smoke validates ready upper-left, upper-mid, and upper-right transition cells plus ready left/right main-side tie cells.
- The builder keeps a single upper transition cell as a diagnostic-compatible fallback when the shared breakline source cannot be subdivided.

### Phase 4 - Cell-Based Surface Triangulation

Status: Done

Tasks:

- replace broad boundary-strip triangulation with cell triangulation
- triangulate only ready cell loops
- preserve triangle kind:
  - `intersection_slope_face_cell_triangle`
  - `intersection_slope_face_upper_transition_cell`
  - `intersection_slope_face_main_side_tie_cell`
  - `intersection_slope_face_curb_return_cell`
- keep curb-return perimeter strip logic only as a cell edge source, not as a free surface filler

Acceptance criteria:

- `Intersection Slope Face Surface` triangles are generated only from ready cells
- source refs include cell ids and shared breakline ids
- no broad temporary boundary strip remains in the visible output

Progress:

- Added cell-based strip triangulation for ready `IntersectionSlopeFaceCellResult` rows.
- Connected upper transition cells and main/side tie cells into `Intersection Slope Face Surface`.
- Added preview metadata for cell result id, cell count, ready cell count, cell triangle count, cell refs, and diagnostics.
- Updated T-intersection smoke coverage to assert cell-based triangles and main/side tie cell refs.
- Broad boundary strip rows now remain as compatibility metadata only when ready cells exist.
- T-intersection smoke now asserts boundary-strip triangle count is zero and cell triangles carry the visible transition output.
- T-intersection smoke now asserts the dedicated surface triangle count is composed from explicit curb-return perimeter, metadata-only boundary strip count, and cell triangles.

### Phase 5 - Shared Breakline Audit Integration

Status: Done

Tasks:

- attach cell consumed breakline refs to the dedicated surface
- audit each cell boundary
- expose:
  - missing cell edge count
  - open cell count
  - shared breakline mismatch count
  - generated cell triangle count

Acceptance criteria:

- Breakline Audit reports ready when all cell boundaries are consumed
- main/side contact is validated as a shared boundary, not just nearby geometry

Progress:

- Added `IntersectionSlopeFaceCellOpenCount` and `IntersectionSlopeFaceCellMissingEdgeCount` preview metadata.
- Shared Breakline Audit rows now include cell count, ready cell count, open cell count, missing edge count, and cell triangle count.
- Shared Breakline Audit summary treats open/missing-edge cells as issues.
- Shared Breakline Audit display rows now include a dedicated `Cell Audit: Intersection Slope Face` row.
- Recommended Action now points users to review Intersection Slope Face cells when open or missing-edge cells exist.
- T-intersection smoke now asserts zero open cells and zero missing cell edges.
- Added cell-level audit rows with cell id, cell role, status, open flag, missing edge count, point count, boundary refs, and diagnostics.
- Shared Breakline Audit display rows now expand cell-level detail rows below the `Cell Audit: Intersection Slope Face` summary row.
- T-intersection smoke now asserts that cell-level audit rows are exposed.
- T-intersection smoke now validates `SharedBreaklineAuditStatus=ready` and zero mesh mismatch for the dedicated surface.

### Phase 6 - UI / Results / Visibility

Status: Done

Tasks:

- Results tab reports:
  - cell count
  - ready cell count
  - open cell count
  - cell triangle count
- Visibility tab keeps ordinary `Slope Face Surface` and dedicated `Intersection Slope Face Surface` separate
- Intersections tab can highlight a selected cell and its breaklines

Progress:

- Results tab now appends `Intersection Slope Face Surface` cell status, cell count, ready/open/missing-edge counts, and cell triangle count to the row notes.
- Intersections tab now exposes `slope_face_cell` contract rows from `IntersectionSlopeFaceCellAuditRows`.
- Cell rows carry status, source status, boundary refs, diagnostics, output path, and focus target.
- Added contract coverage so users can distinguish ready cells from open or missing-edge cells in the table.
- Double-click focus for `slope_face_cell` rows now highlights the matching shared breakline segments from `Intersection Slope Face Surface`.

Acceptance criteria:

- user can see which cell is missing when a gap remains
- user can focus a shared breakline or cell from the table

### Phase 7 - Regression Smoke

Status: Done

Tasks:

- update T intersection FreeCADCmd smoke
- assert:
  - no temporary broad boundary-strip output
  - upper transition cells exist
  - main/side tie cells exist
  - curb-return internal false patches do not exist
  - shared breakline audit is ready

Acceptance criteria:

- FreeCADCmd smoke passes on FreeCAD 1.1.1
- tests validate contracts and counts, not only object existence

Progress:

- T-intersection FreeCADCmd smoke validates cell triangle output, zero broad boundary-strip triangles, main/side tie cell refs, cell audit rows, and ready shared breakline audit.
- Added FreeCADCmd contract validation for Results and Intersections tab cell metadata.
- T-intersection FreeCADCmd smoke now validates ready upper transition cells, left/right main-side tie cells, required shared breakline role families, slope-face-cell Intersections tab rows, and cell double-click/focus highlight output.

## Manual QA Checklist

1. Build T Intersection preset.
2. Build Applied Sections.
3. Build Parametric.
4. Show only:
   - `Intersection Surface`
   - `Intersection Slope Face Surface`
   - `Design Surface`
   - `3D Centerline`
5. Confirm the curb-return interior has no rectangular false surfaces.
6. Confirm upper left, upper middle, and upper right gap areas are filled.
7. Show ordinary `Slope Face Surface`.
8. Confirm ordinary and dedicated slope-face surfaces meet without overlap.
9. Open Breakline Audit.
10. Confirm main/side contact breaklines are ready.
11. Double-click each cell row and confirm the highlighted boundary matches the visible cell.

## Diagnostics To Add

- `intersection_slope_face_cell_edge_missing`
- `intersection_slope_face_cell_open`
- `intersection_slope_face_cell_self_crossing`
- `intersection_slope_face_cell_overlaps_pavement`
- `intersection_slope_face_cell_overlaps_curb_return_interior`
- `intersection_slope_face_main_side_tie_missing`
- `intersection_slope_face_upper_gap_cell_missing`
- `intersection_slope_face_shared_breakline_unconsumed`
- `intersection_slope_face_shared_breakline_mismatch`

## Non-Goals

- do not infer cells from existing preview mesh triangles
- do not restore broad fan triangulation
- do not make ordinary `Slope Face Surface` own intersection slope-face cells
- do not hide gaps with decorative filler surfaces

## Completion Criteria

This plan is complete when:

- upper gap areas are closed by explicit `IntersectionSlopeFaceCellRow` cells
- main-road and side-road contact areas share named breaklines
- dedicated `Intersection Slope Face Surface` consumes cell breaklines
- ordinary and dedicated slope-face surfaces do not overlap
- curb-return interior false patches remain removed
- Breakline Audit reports ready for the T intersection preset
- FreeCADCmd regression smoke validates the behavior

## Current Completion Status

Status: Complete for the T-intersection preset smoke scope.

Done:

- main-road and side-road contact areas share named `main_side_slope_face_tie` breaklines
- dedicated `Intersection Slope Face Surface` consumes cell breaklines
- broad temporary boundary-strip triangles are suppressed when cell output exists
- curb-return interior false patches remain removed in the T-intersection smoke
- Breakline Audit reports ready for the T-intersection preset
- FreeCADCmd regression smoke validates cell rows, shared breakline roles, and cell double-click/focus highlight
- upper transition is split into ready left/middle/right cells when source breaklines provide enough local subdivision
