# V1 Intersection Shared Boundary Graph Plan

Date: 2026-06-29  
Status: Planned  
Scope: canonical shared-boundary graph for intersection surface ownership and tie-in continuity

## Purpose

This plan fixes the current intersection surface continuity problem at its root.

The previous `Intersection Slope Face Cell` work made dedicated cell surfaces visible and traceable, but the visual QA result still shows that adjacent surfaces do not reliably meet on one shared boundary.

The next step is to introduce a canonical intersection shared-boundary graph.

Every surface around the intersection must consume the same named boundary edges instead of independently generating similar-looking lines.

## Current Failure

The current result can report ready cells while the 3D view still shows:

- duplicated cyan/yellow boundary lines
- small gaps between `Intersection Surface`, `Design Surface`, ordinary `Slope Face Surface`, and dedicated `Intersection Slope Face Surface`
- overlapping triangles near the main-road / side-road contact area
- upper transition cells that are subdivided for triangulation but are not yet true shared topology cells

The root issue is not triangle generation.

The root issue is that each surface still owns or derives too much of its boundary independently.

## Core Rule

Shared boundary first, surface second.

Do not create or repair a surface boundary from generated mesh triangles.

The authoritative boundary must be a result contract derived from source/evaluation data:

- `IntersectionModel`
- `IntersectionTopologyResult`
- `IntersectionEdgeNetworkResult`
- `IntersectionSurfaceZoneResult`
- `IntersectionBoundarySegmentResult`
- `IntersectionSlopeFaceBoundaryResult`
- Applied Section side-slope/daylight rows
- `SharedBreaklineResult`

Surface builders may consume the graph.

Surface builders must not become the owners of shared edge identity.

## Target Model

Add a dedicated result contract:

`IntersectionSharedBoundaryGraphResult`

### Graph Node

`IntersectionSharedBoundaryNodeRow`

Fields:

- `node_id`
- `intersection_id`
- `node_role`
- `x`
- `y`
- `z`
- `source_refs`
- `source_status`
- `diagnostics`

Node roles:

- `patch_corner`
- `curb_return_arc_point`
- `design_tie_point`
- `corridor_slope_tie_point`
- `main_side_contact_point`
- `upper_split_point`

### Graph Edge

`IntersectionSharedBoundaryEdgeRow`

Fields:

- `edge_id`
- `intersection_id`
- `edge_role`
- `from_node_ref`
- `to_node_ref`
- `point_refs`
- `consumer_refs`
- `left_owner`
- `right_owner`
- `source_refs`
- `source_status`
- `diagnostics`

Edge roles:

- `patch_to_intersection_slope_face`
- `intersection_slope_face_to_design_surface`
- `intersection_slope_face_to_corridor_slope_face`
- `main_side_slope_face_tie`
- `curb_return_to_intersection_slope_face`
- `upper_transition_internal_seam`
- `design_to_intersection_surface`
- `ordinary_slope_to_intersection_boundary`

### Graph Cell

`IntersectionSharedBoundaryCellRow`

Fields:

- `cell_id`
- `intersection_id`
- `cell_role`
- `boundary_edge_refs`
- `owner_surface_ref`
- `adjacent_surface_refs`
- `source_refs`
- `closed`
- `self_crossing`
- `status`
- `diagnostics`

Cell roles:

- `upper_left_transition_cell`
- `upper_mid_transition_cell`
- `upper_right_transition_cell`
- `main_to_side_left_tie_cell`
- `main_to_side_right_tie_cell`
- `curb_return_perimeter_cell`
- `ordinary_slope_transition_cell`

## Ownership Rules

### Intersection Surface

Consumes:

- `patch_to_intersection_slope_face`
- `design_to_intersection_surface`
- `curb_return_to_intersection_slope_face`

Does not own:

- ordinary slope-face outer boundary
- dedicated slope-face triangles

### Dedicated Intersection Slope Face Surface

Consumes:

- `patch_to_intersection_slope_face`
- `intersection_slope_face_to_design_surface`
- `intersection_slope_face_to_corridor_slope_face`
- `main_side_slope_face_tie`
- `curb_return_to_intersection_slope_face`
- `upper_transition_internal_seam`

Does not own:

- central pavement
- curb-return pavement interior
- ordinary corridor slope-face cells outside the graph boundary

### Ordinary Slope Face Surface

Consumes:

- `intersection_slope_face_to_corridor_slope_face`
- `ordinary_slope_to_intersection_boundary`

Does not own:

- dedicated intersection slope-face cells

### Design Surface

Consumes:

- `intersection_slope_face_to_design_surface`
- `design_to_intersection_surface`

Does not independently recreate:

- the same shoulder/design edge with a different id

## Implementation Phases

### Phase 1 - Contract Definition

Status: Done

Tasks:

- add `IntersectionSharedBoundaryGraphResult`
- add node, edge, and cell rows
- keep the contract under `freecad/Corridor_Road/v1/models/result`
- add unit tests for closed graph cells and missing consumer diagnostics

Acceptance criteria:

- a graph can represent the T-intersection upper transition boundary without generating geometry
- edge consumers are explicit
- source refs are preserved

Progress:

- Added `IntersectionSharedBoundaryGraphResult`.
- Added node, edge, and cell row contracts.
- Added contract tests for closed graph cells and missing-consumer/open-cell diagnostics.

### Phase 2 - Graph Builder

Status: Done

Tasks:

- build the graph from existing intersection evaluation results and Applied Section side-slope rows
- convert existing `SharedBreaklineResult` rows into canonical graph edges
- merge duplicate/parallel edges that represent the same boundary
- create upper split nodes as graph nodes, not just sampled points inside a surface builder
- create `upper_transition_internal_seam` edges for left/mid/right cell separation

Acceptance criteria:

- T-intersection graph has unique edge ids for each shared boundary
- duplicated cyan/yellow edge families are reduced to one canonical edge per boundary
- upper left/mid/right cells are graph-closed by edge refs

Progress:

- Added a first graph builder that converts intersection `SharedBreaklineResult` rows into canonical graph nodes and edges.
- Added expected-consumer diagnostics for core intersection slope-face boundary roles.
- Added duplicate/parallel edge detection keyed by role and snapped endpoint nodes.
- Mapped existing `IntersectionSlopeFaceCellResult` boundary refs into graph cell edge refs as a migration bridge for Phase 3.
- Added contract tests for ready graph conversion and duplicate/missing-consumer warnings.
- Added `upper_transition_internal_seam` graph edges from shared upper transition cell loop segments.
- Attached graph result metadata to the dedicated `Intersection Slope Face Surface` preview.
- Added graph counts and recommended action integration to the Breakline Audit summary/display path.
- Expanded Breakline Audit display rows with graph edge and graph cell detail rows.
- Exposed graph edge/cell contracts in the Intersections contract review rows.

### Phase 3 - Surface Consumer Refactor

Status: Complete for the T-intersection smoke scope

Tasks:

- update `IntersectionSlopeFaceCellResult` to consume graph cell refs
- update dedicated `Intersection Slope Face Surface` builder to triangulate from graph cell edges
- update ordinary `Slope Face Surface` suppression to consume graph boundary edges
- update `Intersection Surface` and `Design Surface` metadata so they consume the same graph edge ids

Acceptance criteria:

- surface triangles are generated from graph edge refs
- no surface invents its own duplicate boundary edge
- `Intersection Surface`, `Design Surface`, ordinary `Slope Face Surface`, and dedicated `Intersection Slope Face Surface` expose common consumed graph edge refs

Progress:

- Added evaluated loop points to graph cell rows as output derived from canonical graph edge refs.
- Updated the dedicated `Intersection Slope Face Surface` builder to generate upper transition cells from `IntersectionSharedBoundaryGraphResult` first.
- Kept legacy `IntersectionSlopeFaceCellResult` generation as fallback for non-upper cells during migration.
- Added graph-surface quality metadata for generation mode, triangle count, generated cell refs, and diagnostics.
- Added a FreeCADCmd-covered contract test proving upper graph cells can generate TIN triangles.
- Attached graph edge-consumption metadata to ordinary `Slope Face Surface` for `slope_face_surface` consumers.
- Added consumed-edge count to Breakline Audit graph rows so ordinary and dedicated slope-face graph consumption can be compared.
- Added a contract test for consumer-filtered graph edge refs.
- Attached graph edge-consumption metadata to `Design Surface` for `design_surface` consumers.
- Attached graph edge-consumption metadata to `Intersection Surface` for `intersection_surface` consumers.
- Extended the consumer-filter test to cover design, intersection, ordinary slope-face, and dedicated intersection slope-face consumers.
- Added graph consumer-pair audit for adjacent surface pairs that must share the same graph edge id.
- Surfaced pair-missing counts and notes in Breakline Audit summary/display rows.
- Added a FreeCADCmd-covered contract test for graph pair audit success and missing-consumer-pair warnings.
- Added graph pair detail rows so Breakline Audit shows the missing edge role and surface pair directly.
- Added a parser and display-row test for `pair_match` / `pair_missing` graph audit notes.

### Phase 4 - Shared Boundary Audit

Status: Complete for the T-intersection smoke scope

Tasks:

- add graph-level audit rows
- validate each edge has the expected consumers
- validate endpoint equality by node id
- validate mesh vertices are snapped to canonical graph nodes
- detect duplicate parallel edges with different ids
- detect cell loops that are closed geometrically but not graph-closed

Progress:

- Added graph-level audit rows for endpoint mismatch, duplicate canonical node, missing consumer, duplicate parallel edge, and graph-open cell diagnostics.
- Attached endpoint mismatch and not-snapped counts to preview metadata and Breakline Audit rows.
- Included graph endpoint/snap counts in Breakline Audit summary and Recommended Action logic.
- Added a FreeCADCmd-covered contract test for ready graph audit and intentionally broken endpoint/snap cases.
- Added consumer ownership audit so a surface row warns when it references a graph edge not owned by its expected consumer.
- Surfaced `shared_boundary_surface_owns_foreign_edge` diagnostics in Breakline Audit notes and summary counts.
- Added graph-closed cell validation using boundary-edge node degree, so cells marked closed but not actually closed by graph connectivity warn as `shared_boundary_cell_not_graph_closed`.

Diagnostics:

- `shared_boundary_edge_missing_consumer`
- `shared_boundary_edge_duplicate_parallel`
- `shared_boundary_edge_endpoint_mismatch`
- `shared_boundary_consumer_not_snapped`
- `shared_boundary_cell_not_graph_closed`
- `shared_boundary_surface_owns_foreign_edge`

Acceptance criteria:

- audit can fail even when geometry distances are near zero if consumer edge ids are not shared
- audit explains which surface must be rebuilt or which source edge is missing

### Phase 5 - UI And Highlight

Status: Complete for the T-intersection smoke scope

Tasks:

- add a `Shared Boundary Graph` section or row group to Breakline Audit
- show graph status at the top:
  - `Ready`
  - `Warnings`
  - `Errors`
- expose node count, edge count, cell count, duplicate edge count, missing consumer count, and not-snapped count
- double-click graph edge rows to highlight the canonical edge
- double-click graph cell rows to highlight the full graph loop

Acceptance criteria:

- users can identify whether a visual gap is caused by missing source, duplicate boundary, or surface consumer mismatch
- highlighted graph edge matches the visible boundary expected in 3D

Progress:

- Breakline Audit already expands surface rows with a `Shared Boundary Graph` row group and graph edge/cell detail rows.
- Added canonical graph segment rows to preview metadata so graph edge ids can be highlighted directly.
- Added double-click/focus support for graph edge and graph cell rows using `Intersection Shared Boundary Graph Highlight`.
- Added regression coverage for graph display rows carrying highlight edge refs and segment coordinates.
- Added Breakline Audit summary notes for Shared Boundary Graph status, node/edge/cell counts, consumed edge count, and graph issue counts.

### Phase 6 - Regression Smoke

Status: Complete for the T-intersection smoke scope

Tasks:

- extend the T-intersection smoke
- assert graph edge roles exist
- assert expected consumers for:
  - `patch_to_intersection_slope_face`
  - `intersection_slope_face_to_design_surface`
  - `intersection_slope_face_to_corridor_slope_face`
  - `main_side_slope_face_tie`
  - `curb_return_to_intersection_slope_face`
- assert zero duplicate parallel graph edges
- assert all dedicated slope-face cells are graph-closed
- assert ordinary and dedicated slope-face surfaces consume the same shared edge at their contact boundary

Acceptance criteria:

- FreeCADCmd smoke fails if surfaces only look close but do not share graph edge ids
- FreeCADCmd smoke passes on FreeCAD 1.1.1

Progress:

- Extended the T-intersection dedicated slope-face smoke with canonical graph edge-role checks.
- Asserted expected consumers for patch/design/corridor-slope/main-side/curb-return graph edge roles.
- Asserted zero duplicate graph edges, zero endpoint mismatch, zero unsnapped nodes, and zero open graph cells.
- Asserted ordinary and dedicated Slope Face surfaces consume the same canonical graph edge at their contact boundary.
- Added `cell_closure_internal_seam` graph edges so evaluated main/side and transition cells are graph-closed without relying on generated mesh repair.
- Exposed dedicated `IntersectionSharedBoundaryGraphRefs` and `IntersectionSharedBoundaryGraphSurfaceTriangleCount` on the dedicated intersection slope-face preview.
- Added coverage-oriented bbox/area smoke metrics so generated graph/cell/perimeter triangles must occupy the intersection patch vicinity, not merely exist as small fragments.
- Added a non-T readiness smoke for Cross, Skewed, and Y presets so dedicated Intersection Slope Face Surface readiness stays truthful beyond the default T preset.
- Validated with FreeCADCmd 1.1.1:
  - `tests/regression/smoke_intersection_t_slope_face_surface.py`
  - `tests/regression/smoke_intersection_non_t_slope_face_readiness.py`
  - `tests/contracts/v1/test_intersection_shared_boundary_graph_builder.py`

## Migration From Current Cell Work

The current `IntersectionSlopeFaceCellResult` remains useful.

It should be changed from:

```text
cell -> loop_points_xyz -> surface triangles
```

to:

```text
shared boundary graph -> graph cell refs -> evaluated loop points -> surface triangles
```

`loop_points_xyz` may remain as evaluated output.

It must not be the source of cell identity.

## Manual QA Checklist

1. Build T Intersection preset.
2. Build Applied Sections.
3. Build Parametric.
4. Open Breakline Audit.
5. Confirm `Shared Boundary Graph` status is ready.
6. Confirm duplicate edge count is zero.
7. Confirm missing consumer, endpoint mismatch, not-snapped, foreign-edge, and graph-open-cell counts are zero.
8. Confirm the summary includes graph node, edge, cell, and consumed-edge counts.
9. Double-click `patch_to_intersection_slope_face`; confirm it matches the intersection / slope-face contact.
10. Double-click `intersection_slope_face_to_corridor_slope_face`; confirm ordinary and dedicated slope-face surfaces meet there.
11. Double-click `curb_return_to_intersection_slope_face`; confirm the curb-return boundary is shared with the dedicated slope-face surface.
12. Double-click each upper transition graph cell; confirm left/mid/right cells share internal seams and do not overlap.
13. Double-click each main/side graph cell; confirm it is closed by graph edges and touches the side-road tie-in without detached rectangles.
14. Toggle ordinary `Slope Face Surface` and dedicated `Intersection Slope Face Surface`; confirm no duplicated boundary line appears.

## Non-Goals

- do not infer graph edges from generated mesh triangles
- do not use preview highlight geometry as source
- do not hide duplicated edges with display styling
- do not merge surfaces into one monolithic intersection mesh
- do not let ordinary `Slope Face Surface` own dedicated intersection slope-face cells

## Completion Criteria

This plan is complete when:

- all intersection tie-in boundaries are represented by canonical graph edges
- each graph edge has expected surface consumers
- upper transition cells are graph-closed
- main/side contact cells share graph edges
- Breakline Audit reports duplicate edge count and missing consumer count
- visual QA no longer shows duplicated boundary linework around the intersection
- FreeCADCmd smoke validates graph topology, not just triangle counts

Current T-intersection smoke status:

- canonical graph edge roles are validated
- expected consumers are validated
- duplicate edges, endpoint mismatch, not-snapped nodes, and graph-open cells are asserted as zero
- ordinary and dedicated slope-face surfaces are asserted to consume the same contact graph edge
- remaining broader coverage: skewed intersections, X/Y intersection presets, and non-default curb-return policy variants
