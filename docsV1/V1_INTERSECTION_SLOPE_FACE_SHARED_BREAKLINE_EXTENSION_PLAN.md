# V1 Intersection Slope Face Shared Breakline Extension Plan

Date: 2026-06-29  
Status: In progress  
Scope: extend `Intersection Slope Face Surface` coverage at main-road/side-road tie-in areas using shared breakline ownership boundaries

## Purpose

This plan addresses the remaining visual and contract gap around intersections after the dedicated `Intersection Slope Face Surface` was introduced.

Current work can generate:

- curb-return to side-slope perimeter strips
- central intersection boundary to Applied Section side-slope strips
- dedicated `Intersection Slope Face Surface` preview rows and visibility metadata

However, user visual QA still shows incomplete coverage where the main road, side road, ordinary corridor surfaces, and intersection-owned surfaces meet. The surface is generated near the central intersection boundary, but it does not extend far enough sideways into the transition areas where ordinary `Slope Face Surface`, `Design Surface`, `Intersection Surface`, and `Intersection Slope Face Surface` must share a precise boundary.

The next step is not to simply widen triangles. The next step is to define the shared boundary between surface ownership domains as source-traceable breakline contracts.

## Core Rule

Do not use generated preview meshes as source truth.

The intersection slope-face extension must be derived from:

- `IntersectionModel` source rows
- `IntersectionTopologyResult`
- `IntersectionEdgeNetworkResult`
- `IntersectionSurfaceZoneResult`
- `IntersectionBoundarySegmentResult`
- `IntersectionSlopeFaceBoundaryResult`
- Applied Section side-slope/daylight boundary rows
- Shared breakline contracts consumed by both adjacent surfaces

Generated `Mesh::Feature`, `Part::Feature`, ordinary corridor TIN fragments, or manually visible highlight objects must not become source truth.

## Problem Statement

The current implementation creates visible dedicated intersection slope-face triangles, but those triangles mostly cover:

- curb-return perimeter strips
- central tie-in strips close to the intersection patch boundary
- Applied Section side-slope loop fans

The remaining gap is the transition area between:

- main-road ordinary slope face and intersection slope face
- side-road ordinary slope face and intersection slope face
- intersection pavement/control surface and intersection slope face
- curb-return perimeter and straight tie-in perimeter

These areas need shared breaklines so the adjacent surfaces meet on the same boundary coordinates.

Two specific visual failures must be handled explicitly:

- **Curb-return interior false surfaces**: rectangular or slab-like `Intersection Slope Face Surface` patches can appear inside the curb-return / pavement interior when boundary-strip rows are consumed too broadly. These are not slope-face ownership areas and must be excluded from the dedicated surface.
- **Upper left/right transition gaps**: the top side of the main-road intersection can still have missing `Intersection Slope Face Surface` coverage near the left and right transition areas. These gaps require shared breakline extension from the intersection boundary to the ordinary corridor slope-face boundary.

## Desired Ownership Model

Surface ownership should be explicit.

| Surface | Owns |
| --- | --- |
| `Intersection Surface` | central pavement, curb-return pavement, accepted intersection patch/control area |
| `Intersection Slope Face Surface` | side-slope transition area inside the intersection influence/control area |
| ordinary `Slope Face Surface` | corridor side-slope outside the intersection-owned influence boundary |
| ordinary `Design Surface` / `Subgrade Surface` | road body surfaces outside the intersection patch/control ownership |

Where two surfaces meet, they should share a breakline instead of independently guessing edge points.

## Required Shared Breakline Families

### 1. Patch-To-Intersection-Slope-Face Breakline

Boundary between:

- `Intersection Surface`
- `Intersection Slope Face Surface`

Source:

- accepted intersection patch boundary
- tie-in boundary segments
- curb-return boundary segments

Consumer requirements:

- `Intersection Surface` must keep this as an outer/side boundary.
- `Intersection Slope Face Surface` must consume it as an inner boundary.

### 2. Intersection-Slope-Face-To-Corridor-Slope-Face Breakline

Boundary between:

- `Intersection Slope Face Surface`
- ordinary `Slope Face Surface`

Source:

- Applied Section side-slope/daylight boundary rows
- intersection influence/control area station extents
- region transition boundaries where available

Consumer requirements:

- `Intersection Slope Face Surface` consumes it as an outer boundary.
- ordinary `Slope Face Surface` uses it as a suppression/void boundary and does not overlap inside it.

### 3. Main-To-Side Tie-In Transition Breakline

Boundary around the area where the side road ties into the main road.

Source:

- intersection leg control areas
- lane connection / edge-network rows
- Applied Section side-slope points from both main and side alignments

Consumer requirements:

- intersection-owned slope-face strips must connect main-road and side-road boundaries without leaving triangular gaps.
- ordinary corridor surfaces must stop at the same boundary.

### 4. Curb-Return-To-Slope-Face Perimeter Breakline

Boundary around curb-return arcs.

Source:

- `IntersectionBoundarySegmentResult` arc rows
- projected Applied Section side-slope/daylight points

Consumer requirements:

- keep the current successful curb-return perimeter behavior.
- register it as a shared breakline so audit can validate continuity.

## Implementation Phases

### Phase 1 - Audit Current Boundary Contracts

Status: Pending

Goal:

- identify which current rows already represent usable shared boundaries and which are only display/highlight artifacts.

Tasks:

- inspect `IntersectionSlopeFaceBoundaryResult` rows for main and side roads.
- inspect `IntersectionBoundarySegmentResult` tie-in and arc rows.
- map current `Intersection Contract Highlight` rows back to source/result contracts.
- record which row should become:
  - inner boundary
  - outer boundary
  - transition/tie-out boundary
  - diagnostic-only highlight

Acceptance criteria:

- every visible highlight used for slope-face review has a source/result row.
- no plan step depends on highlight object geometry as source truth.

### Phase 2 - Define Shared Breakline Rows

Status: Pending

Goal:

- create explicit shared breakline rows for intersection slope-face ownership boundaries.

Tasks:

- add or extend a result contract for intersection slope-face shared breaklines.
- include fields for:
  - `breakline_id`
  - `intersection_id`
  - `breakline_family`
  - `from_surface_role`
  - `to_surface_role`
  - `alignment_ref`
  - `leg_ref`
  - `side`
  - `points_xyz`
  - `source_contract_refs`
  - `consumer_surface_refs`
  - `status`
  - `diagnostics`
- ensure rows can represent both straight tie-in segments and curb-return arcs.

Acceptance criteria:

- a T intersection can produce breakline rows for main-road and side-road slope-face transitions.
- rows preserve source refs to Applied Sections and intersection boundary contracts.

### Phase 3 - Extend Intersection Slope Face Boundary Generation

Status: Pending

Goal:

- expand `IntersectionSlopeFaceBoundaryResult` from central tie-in strips to full intersection influence transition strips.

Tasks:

- use control area / influence range extents to find transition start and end.
- include side-road tie-in transition boundaries.
- include main-road left/right transition boundaries beyond the central patch edge.
- prevent duplicate rows where curb-return perimeter already owns the boundary.
- classify rows:
  - `central_tie_in_strip`
  - `main_transition_strip`
  - `side_transition_strip`
  - `curb_return_perimeter`
- classify and suppress non-slope ownership rows:
  - `pavement_interior`
  - `curb_return_interior`
  - `intersection_patch_interior`

Acceptance criteria:

- boundary rows cover the main-road and side-road connection area.
- each ready row has at least two inner points and two outer points.
- each row has traceable source Applied Section refs.
- rows whose inner/outer points fall inside the curb-return or pavement patch interior are diagnostic-only and do not generate visible `Intersection Slope Face Surface` triangles.
- upper left/right transition boundaries on the main road are represented as explicit ready rows, not as accidental loop fans.

### Phase 4 - Build Dedicated Surface From Breakline Pairs

Status: In progress

Goal:

- make `Intersection Slope Face Surface` consume shared breakline pairs, not just closed loop fans.

Tasks:

- triangulate strip rows between matched inner/outer breaklines.
- avoid fan triangulation where paired strip triangulation is available.
- keep curb-return perimeter generation as a separate proven path.
- preserve `triangle_kind` values:
  - `intersection_slope_face_boundary_strip`
  - `intersection_slope_face_transition_strip`
  - `intersection_slope_face_curb_return_perimeter`
- add quality rows for generated transition strips.
- skip boundary rows classified as `pavement_interior`, `curb_return_interior`, or `intersection_patch_interior`.
- prioritize paired strip triangulation for top/side transition gaps over closed-loop fan triangulation.

Acceptance criteria:

- `Intersection Slope Face Surface` includes central, main transition, side transition, and curb-return perimeter triangles.
- generated triangles remain in the dedicated intersection surface object.
- ordinary `Slope Face Surface` does not receive these triangles.
- no rectangular/slab-like `Intersection Slope Face Surface` patches are generated inside the curb-return or central pavement interior.
- the upper left and upper right main-road transition gaps are filled by `intersection_slope_face_transition_strip` or equivalent shared-breakline strip triangles.

Progress:

- Applied Section-completed slope-face loops are now retained as consumed source refs but suppressed from fan triangulation when explicit curb-return perimeter or boundary strip triangles are available.
- The T intersection smoke test now asserts that the dedicated surface is composed from explicit curb-return perimeter and boundary strip triangles, not interior loop fan patches.
- Boundary rows now use the active intersection Applied Section station range as the source-driven transition extent instead of only the short tie-in edge plus a fixed local extension.
- Boundary strip triangles are classified as `intersection_slope_face_transition_strip` when the row is owned by `main_transition_strip` or `side_transition_strip`.
- The T intersection smoke test now asserts transition strip counts and transition strip triangle counts.
- Lower/side temporary boundary strips are suppressed for the T preset; only the upper main-road transition strip remains visible alongside curb-return perimeter strips.
- `Intersection Slope Face Surface` now receives `SharedBreaklineResult` metadata through the dedicated `intersection_slope_face_surface` consumer.
- Dedicated `Intersection Slope Face Surface` shared-breakline audit now treats normalized constraint-segment coverage as the primary proof. Zero-distance mesh drift on a contract-matched segment is reported as `mesh_constraint_covered` instead of a mismatch.
- FreeCADCmd smoke now asserts the dedicated surface shared-breakline audit is ready and has zero mesh mismatches.
- Remaining work in this phase is manual visual QA against the user's scene and, if needed, splitting transition strips into separate left/right rows for more detailed audit display.

### Phase 5 - Ordinary Surface Suppression By Shared Boundary

Status: Pending

Goal:

- ensure ordinary corridor surfaces stop at the same shared boundary consumed by the dedicated intersection surface.

Tasks:

- include the expanded intersection slope-face footprint in ordinary `Slope Face Surface` suppression.
- use shared breakline rows as suppression evidence.
- avoid suppressing ordinary corridor slope face outside the intersection influence area.
- record suppression counts and source refs in TIN quality rows.

Acceptance criteria:

- ordinary `Slope Face Surface` and dedicated `Intersection Slope Face Surface` do not overlap in the transition area.
- ordinary surface clipping is diagnostic and traceable.

### Phase 6 - Shared Breakline Audit Integration

Status: Pending

Goal:

- expose whether the surface boundary connection is valid.

Tasks:

- add audit rows for intersection slope-face shared breaklines.
- check:
  - missing consumer
  - geometry mismatch
  - reversed edge
  - duplicate ownership
  - open boundary
  - unconsumed breakline
- add Recommended Action text.

Acceptance criteria:

- Breakline Audit tab can report whether `Intersection Surface`, `Intersection Slope Face Surface`, and ordinary `Slope Face Surface` share the same boundary.
- failures tell the user whether to rebuild Applied Sections, rebuild Intersection, or inspect source rows.

### Phase 7 - Results, Visibility, and Manual QA

Status: Pending

Goal:

- make the new ownership visible and testable.

Tasks:

- Results tab should report:
  - transition strip count
  - shared breakline count
  - consumed breakline refs
  - mismatch count
- Visibility tab should keep `Intersection Slope Face Surface` separate from ordinary `Slope Face Surface`.
- update manual QA steps.

Acceptance criteria:

- user can show only `Intersection Slope Face Surface` and inspect transition coverage.
- user can show Breakline Audit and confirm no shared-boundary mismatch.

### Phase 8 - Regression Smoke

Status: Pending

Goal:

- prevent regressions in T intersection preset behavior.

Tasks:

- extend FreeCADCmd smoke for T intersection.
- assert:
  - dedicated surface exists
  - central strips exist
  - transition strips exist
  - curb-return perimeter strips exist
  - shared breakline rows exist
  - ordinary slope-face suppression consumes the dedicated footprint
- keep tests contract-level where possible.

Acceptance criteria:

- FreeCADCmd smoke passes on FreeCAD 1.1.1.
- object existence alone is not enough; counts and source refs must be checked.

## Diagnostics To Add

Recommended diagnostic names:

- `intersection_slope_face_shared_breakline_missing`
- `intersection_slope_face_transition_boundary_missing`
- `intersection_slope_face_transition_strip_open`
- `intersection_slope_face_transition_strip_duplicate_owner`
- `intersection_slope_face_shared_breakline_geometry_mismatch`
- `intersection_slope_face_ordinary_surface_overlap`
- `intersection_slope_face_breakline_unconsumed`
- `intersection_slope_face_boundary_row_inside_pavement`
- `intersection_slope_face_boundary_row_inside_curb_return`
- `intersection_slope_face_upper_transition_gap`
- `intersection_slope_face_transition_owner_missing`

## Manual QA Checklist

1. Build T Intersection preset sources.
2. Build Applied Sections.
3. Build Parametric.
4. Enable only:
   - `Intersection Surface`
   - `Intersection Slope Face Surface`
   - `3D Centerline`
5. Confirm the main-road/side-road tie-in slope-face area is covered.
6. View from below and confirm no rectangular/slab-like `Intersection Slope Face Surface` patches exist inside the curb-return or central pavement interior.
7. View from above and confirm the upper left and upper right transition gaps are filled.
8. Enable ordinary `Slope Face Surface`.
9. Confirm ordinary slope face does not overlap the dedicated intersection slope-face transition area.
10. Open Breakline Audit.
11. Confirm shared breakline status is ready or clearly diagnostic.

## Risks

- over-expanding intersection ownership can remove ordinary corridor slope face too far from the intersection.
- reusing highlight geometry as source would violate v1 source/result separation.
- fan triangulation can fill the wrong polygon even when counts look correct.
- duplicate breakline ownership can make audit counts look better while surfaces still overlap.

## Completion Criteria

This plan is complete when:

- the top, bottom, left, and right transition areas around a T intersection are covered by `Intersection Slope Face Surface`
- adjacent surfaces share explicit breakline rows
- Breakline Audit reports the shared boundary status
- ordinary and dedicated slope-face surfaces remain separate
- false rectangular/slab-like surfaces inside the curb-return or central pavement interior are not generated
- upper left/right transition gaps on the main road are covered by shared-breakline driven strips
- FreeCADCmd regression smoke validates the behavior
