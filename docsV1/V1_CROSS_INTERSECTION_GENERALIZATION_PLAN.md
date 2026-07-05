# V1 Cross Intersection Generalization Plan

Date: 2026-07-05
Status: Draft
Scope: Cross-intersection and n-leg intersection geometry/result contracts

Depends on:

- `docsV1/V1_INTERSECTION_MODEL.md`
- `docsV1/V1_INTERSECTION_BOUNDARY_LOOP_PLAN.md`
- `docsV1/V1_INTERSECTION_SHARED_BOUNDARY_GRAPH_PLAN.md`
- `docsV1/V1_INTERSECTION_TIE_SLOPE_APPLIED_SECTION_WINDOW_PLAN.md`
- `docsV1/V1_INTERSECTION_UPPER_SLOPE_FACE_RECTANGULAR_PANEL_PLAN.md`

## 1. Purpose

This plan defines how the current T-intersection-oriented implementation should generalize to cross intersections.

The immediate visual problem is that a cross intersection can still produce a rectangular central `Intersection Surface` while the visible curb-return and outside junction boundary are circular or arc-based.

The central pavement surface should follow the accepted curb-return and leg tie-in boundary, not remain a simple rectangular patch.

## 2. Core Rule

Intersection geometry must be generated from `IntersectionModel` source intent and evaluated result contracts.

Generated mesh, preview objects, and manual review highlights must not become source truth.

The cross-intersection implementation must treat T intersections as a 3-leg case and cross intersections as a 4-leg case of the same n-leg intersection model.

## 3. Current Symptoms

The current cross-intersection result can show:

- central `Intersection Surface` as a rectangular patch
- curb-return arc geometry surrounding the rectangular patch
- triangular or fan-like slope panels around the central area
- tie-slope panels that work in T cases but do not fully represent all cross-intersection quadrants
- shared breaklines that are valid for some local panels but not for the complete intersection boundary

The root issue is not only surface triangulation.

The central intersection boundary itself is still too rectangular and T-case biased.

## 4. Desired Result

For a cross intersection:

- four legs are recognized as a single intersection topology
- four curb-return corner arcs are accepted as boundary segments
- leg pavement tie-in edges connect the curb-return arcs
- the final `Intersection Surface` exterior boundary follows the curb-return/tie-in loop
- `Intersection Slope Face Surface` and `Intersection Tie Slope Surface` consume the same shared boundary edges
- Breakline Audit reports a single coherent shared-boundary graph for the intersection envelope

For a T intersection:

- the same n-leg logic handles three legs and two primary curb-return corners
- missing fourth-leg behavior is modeled explicitly as a back/closed boundary, not as a hard-coded T special case

## 5. Architecture Direction

### 5.1 Leg Graph

Create an evaluated leg graph per intersection.

Each leg node should include:

- `leg_id`
- `alignment_ref`
- `profile_ref`
- `centerline3d_ref`
- `approach_station_start`
- `approach_station_end`
- `entry_applied_section_ref`
- `exit_applied_section_ref`
- left/right pavement edge refs
- left/right shoulder or slope-face boundary refs
- leg angle around the intersection anchor

Legs must be sorted angularly around the intersection anchor.

### 5.2 Corner Graph

Create one corner relationship for each adjacent leg pair.

Each corner row should include:

- `corner_id`
- `from_leg_id`
- `to_leg_id`
- `corner_kind`
- `curb_return_policy_ref`
- `curb_return_arc_points`
- `arc_start_ref`
- `arc_end_ref`
- `status`
- `diagnostics`

For cross intersections this normally creates four corners.

For T intersections this normally creates two or three corner candidates, depending on whether the back edge is modeled as a closed boundary or open-side influence edge.

### 5.3 Boundary Segment Graph

Build a canonical ordered boundary from:

- curb-return arc segments
- leg tie-in pavement edges
- corner cap edges
- accepted control-area boundary segments

This graph becomes the source for:

- `Intersection Surface`
- `Intersection Slope Face Surface`
- `Intersection Tie Slope Surface`
- ordinary Design/Slope Face clipping
- shared breakline audit

## 6. Intersection Surface Enhancement Strategy

### 6.1 Problem

The current rectangular central `Intersection Surface` is acceptable only as an internal triangulation seed.

It is not a correct exterior boundary for cross intersections because the real junction perimeter is defined by curb-return arcs and leg tie-ins.

### 6.2 New Boundary Rule

The exterior boundary of `Intersection Surface` must be:

`ordered curb-return arcs + leg pavement/tie-in edges + corner connectors`

The rectangular patch may remain as:

- a grading reference grid
- a triangulation seed
- a center control panel

It must not be the final exterior loop unless diagnostics explicitly mark the intersection as rectangular-only fallback.

### 6.3 Result Contract

Add or harden a result family:

- `intersection_surface_boundary_loop`

Suggested fields:

- `loop_id`
- `intersection_id`
- `loop_kind`
- `leg_count`
- `corner_count`
- `segment_refs`
- `loop_points_xyz`
- `loop_area_xy`
- `orientation`
- `source_mode`
- `status`
- `diagnostics`
- `recommended_action`

Suggested `loop_kind`:

- `curb_return_envelope`
- `t_intersection_envelope`
- `cross_intersection_envelope`
- `rectangular_fallback`

Suggested `source_mode`:

- `ordered_curb_return_and_leg_tie_in_boundary`

### 6.4 Triangulation Rule

Triangulate the enhanced `Intersection Surface` inside the curb-return envelope.

Preferred sequence:

1. Preserve the exterior loop points as fixed breakline vertices.
2. Add internal center/control panel points only as interior constraints.
3. Connect leg centerline/control lines as internal breaklines.
4. Reject triangles outside the exterior loop.
5. Reject triangles that bridge across non-adjacent legs.

Acceptance:

- the visible `Intersection Surface` boundary follows the curb-return envelope
- the central rectangle is not visible as an exterior clipping boundary
- no exterior triangle crosses outside the accepted loop

## 7. Shared Breakline Strategy

Each physical edge must have one canonical breakline identity.

### 7.1 Required Shared Boundaries

For cross intersections, publish shared boundaries for:

- `intersection_surface_to_design_surface`
- `intersection_surface_to_intersection_slope_face`
- `intersection_surface_to_intersection_tie_slope`
- `curb_return_to_intersection_slope_face`
- `leg_tie_slope_to_corridor_slope_face`
- `leg_tie_slope_to_design_surface`
- `intersection_boundary_to_corridor_clip`

### 7.2 Consumer Rules

Consumers must use the same point sequence and orientation-normalized edge reference.

Required consumers:

- `Intersection Surface`
- `Intersection Slope Face Surface`
- `Intersection Tie Slope Surface`
- ordinary `Design Surface`
- ordinary `Slope Face Surface`
- `Corridor Clip`
- Breakline Audit

### 7.3 Audit Rules

Breakline Audit should report:

- missing consumer
- reversed edge
- geometry mismatch
- mesh mismatch
- open cell
- foreign edge
- unowned boundary

The audit should identify whether the issue belongs to:

- leg graph
- corner graph
- boundary loop
- surface triangulation
- downstream preview routing

## 8. Intersection Slope Face And Tie Slope Generalization

### 8.1 Tie Slope

The successful T-intersection tie-slope approach should be generalized as a leg-local applied-section window:

- find the first Applied Section outside the intersection control span
- find the first Applied Section inside or adjacent to the intersection control span
- build a local quadrilateral or strip between those two section boundaries
- keep this as `Intersection Tie Slope Surface`

For cross intersections, run this per leg and per side.

### 8.2 Slope Face

`Intersection Slope Face Surface` should consume:

- curb-return arc edges
- enhanced intersection surface envelope edges
- adjacent tie-slope caps
- upper/lower rectangular panel edges where applicable

It should not use ordinary corridor slope-face generated mesh as source truth.

### 8.3 Upper Panel

The upper rectangular panel strategy should become an n-leg panel strategy.

Instead of one T-specific upper panel, create per-gap rectangular panels between:

- an intersection boundary edge
- the nearest ordinary slope/shoulder edge
- left local cap
- right local cap

Each panel must be bounded and audited as a shared breakline cell.

## 9. Implementation Phases

### Phase CI-001 - Cross Intersection Baseline Diagnostics

Status: Done

Work:

- add diagnostics that count legs, corners, curb-return arcs, boundary segments, and fallback rectangular loops
- expose whether `Intersection Surface` used rectangular fallback or curb-return envelope
- add notes for missing corner arcs or unordered leg graph

Acceptance:

- cross-intersection build explains why the surface is rectangular
- T-intersection diagnostics remain stable

Implementation note:

- `Intersection Surface` preview now exposes `IntersectionSurfaceBoundary*` properties for leg count, corner count, curb-return arc count, boundary loop kind, fallback reason, and diagnostic summary.
- Normalized `IntersectionSurfacePatchResult` diagnostics include the same boundary-review diagnostics so Results notes can explain rectangular or ordered-boundary fallback before the geometry is upgraded.

### Phase CI-002 - N-leg Leg Graph

Status: Done

Work:

- evaluate participating legs for each intersection
- sort legs around the anchor by angle
- preserve primary/secondary role without hard-coding T-only meaning
- attach Applied Section entry/exit references per leg

Acceptance:

- T preset reports `leg_count=3`
- cross preset reports `leg_count=4`
- no leg is inferred from preview mesh

Implementation note:

- `IntersectionTopologyLegSpanRow` now carries `leg_graph_order`, `leg_graph_angle_deg`, `leg_graph_angle_source`, and Applied Section entry/exit lineage placeholders.
- `IntersectionTopologyResult` now exposes `leg_graph_status`, `leg_graph_order_refs`, and `leg_graph_diagnostic_rows`.
- The first slice uses source leg roles for deterministic n-leg ordering and records traceable fallback diagnostics when a leg role has no known angle mapping. It does not read preview geometry or generated meshes.

### Phase CI-003 - Corner Graph And Curb-return Arcs

Status: Done

Work:

- create corner rows for adjacent leg pairs
- attach curb-return policy and sampled arc points
- reject corners with missing endpoint refs
- expose corner diagnostics in Intersections review

Acceptance:

- cross preset produces four corner candidates
- curb-return arcs are available as ordered source/evaluation points

Implementation note:

- `IntersectionTopologyCornerRow` now records ordered adjacent-leg corner candidates, source corner refs when available, curb-return policy refs, radius, start/end points, and sampled arc points.
- `IntersectionTopologyResult` now exposes `corner_graph_status`, `corner_count`, `curb_return_arc_count`, `corner_graph_order_refs`, and `corner_graph_diagnostic_rows`.
- Cross intersections can report four source/evaluation corner candidates from the n-leg graph without reading preview meshes. Missing explicit corner source rows remain traceable warnings until source corner authoring is added.

### Phase CI-004 - Curb-return Envelope Boundary Loop

Status: Done for boundary-loop contract. Surface consumption continues in CI-005.

Work:

- assemble ordered exterior loop from corner arcs and leg tie-in edges
- validate loop closure, orientation, area, and self-crossing
- keep rectangular fallback only as diagnostic fallback

Acceptance:

- cross `Intersection Surface` boundary follows curb-return envelope
- rectangular fallback is not used when complete curb-return envelope exists

Implementation note:

- `evaluate_boundary_loops()` now evaluates the topology corner graph first and builds a `curb_return_envelope` candidate from ordered curb-return arc points.
- The curb-return envelope is validated for closure, area, and self-crossing before it is accepted.
- When the envelope is valid, it becomes the authoritative boundary-loop source instead of the segment-graph rectangle or convex-hull fallback.
- The legacy segment graph and convex-hull paths remain diagnostic fallbacks when source/evaluation corner arcs are incomplete.

### Phase CI-005 - Intersection Surface Triangulation Upgrade

Status: Done for first surface-consumption slice. Further edge constraint refinement continues in CI-006.

Work:

- triangulate inside the enhanced envelope
- preserve envelope as fixed breakline
- insert center/control panel points as internal constraints only
- prevent triangles from escaping outside the envelope

Acceptance:

- central surface no longer appears as a simple exterior rectangle
- curb-return ring and central pavement surface share visible boundary points

Implementation note:

- `_build_intersection_surface_patch_tin()` now evaluates the authoritative `IntersectionBoundaryLoopResult` and uses its ready outer loop as the patch TIN boundary before falling back to the older ordered patch boundary or convex hull.
- The generated TIN records `patch_boundary_source=authoritative_boundary_loop` and authoritative loop point/segment counts in quality rows.
- Surface boundary review now treats `authoritative_boundary_loop` as a valid curb-return envelope source, so cross-intersection diagnostics no longer report it as rectangular fallback when the loop is ready.
- The existing ordered polygon triangulation is reused for the first slice. CI-006 should strengthen shared edge ownership and fixed breakline constraints across all consumers.

### Phase CI-006 - Shared Boundary Graph Upgrade

Status: In progress. Canonical envelope role mapping is implemented.

Work:

- publish canonical shared boundary refs from the enhanced envelope
- connect Intersection Surface, Slope Face, Tie Slope, Design Surface, and corridor clips to the same refs
- update Breakline Audit display for cross-intersection edge ownership

Acceptance:

- Breakline Audit shows no geometry mismatch on accepted envelope edges
- consumers report the same edge count for shared boundaries

Implementation note:

- Boundary-loop shared breakline promotion now normalizes internal curb-return envelope segment roles before publishing to the shared boundary graph.
- `curb_return_envelope_arc` is exposed as `curb_return_to_intersection_slope_face`.
- `curb_return_envelope_connector` is exposed as `patch_to_design_surface`.
- The canonical roles reuse the existing expected-consumer map, so `Intersection Surface`, `Design Surface`, and `Intersection Slope Face Surface` can consume the same graph edge refs where appropriate.
- Surface constraint quality rows now include `shared_breakline_boundary_loop_constraint_role_summary`.
- Build Parametric Breakline Audit notes expose `boundary_loop_constraint_roles=...`, making role-level boundary-loop consumption visible to users.
- Boundary-loop graph fill QA now reports consumer-family coverage separately for `Intersection Surface`, `Design Surface`, `Intersection Slope Face Surface`, ordinary `Slope Face Surface`, and `Intersection Tie Slope Surface`.
- Shared boundary graph audit now detects when one authoritative boundary-loop or curb-return envelope segment is split into multiple graph edges across consumers. This prevents matching edge counts from hiding a broken shared-boundary identity.

### Phase CI-007 - N-leg Tie Slope And Slope Face Panels

Status: In progress. Upper panel coverage review has started.

Work:

- generate tie-slope panels per leg and side
- generate rectangular slope-face panels per gap around the intersection
- remove T-specific assumptions from panel selection
- report upper panel coverage by alignment/side group so cross-intersection gaps are visible before mesh review
- replace T-specific first-unused upper panel edge fallback with nearest source-breakline matching when alignment/side metadata is incomplete
- validate that a synthetic cross-intersection upper panel source set produces accepted candidates for all four alignment/side groups

Acceptance:

- cross intersection has panels around all four legs
- T intersection still preserves the completed tie-slope behavior
- Results notes identify missing upper panel alignment/side groups
- upper panel candidate rows expose exact/nearest match mode for traceable n-leg fallback
- contract tests prove four alignment/side groups can be generated without falling back to T-specific pairing

Implementation notes:

- Upper panel candidate selection now prefers exact `alignment_ref` and `side` matches and falls back to nearest source breakline only as traceable diagnostic behavior.
- Upper panel coverage is summarized by `alignment_ref:side`, so cross-intersection gaps can be detected before manual 3D mesh review.
- A synthetic cross-intersection contract test covers `primary:left`, `primary:right`, `secondary:left`, and `secondary:right` panel candidates.
- Upper panel coverage now compares generated candidates against expected `alignment_ref:side` groups from source shared breaklines, so a missing direction is reported even when no candidate row was generated for that direction.
- Preview properties and Results/Intersections review notes now expose `expected_groups`, allowing manual QA and smoke tests to confirm that cross-intersection upper panel coverage is evaluated against all expected leg/side groups.

### Phase CI-008 - UI And Manual QA

Status: In progress. Intersections review notes now expose topology and boundary-mode context.

Work:

- add clear Intersections review notes for `leg_count`, `corner_count`, `surface_boundary_mode`, and `fallback_reason`
- add manual QA steps for T and cross presets
- update wiki Intersections page after behavior is stable
- keep topology and boundary-loop rows compact enough for table review while exposing the key n-leg/cross diagnostics

Acceptance:

- user can confirm whether a cross intersection used curb-return envelope mode
- manual QA documents expected visual result
- topology row shows intersection kind, leg count, corner count, curb-return arc count, and graph readiness
- boundary-loop row shows surface boundary mode, loop kind, and fallback reason when present

Implementation notes:

- Intersections `topology` notes now include `kind`, `legs`, `corners`, `curb_return_arcs`, `leg_graph`, and `corner_graph`.
- Intersections `boundary_loop` notes now include `surface_boundary_mode`, `surface_boundary_loop`, and `fallback_reason` when available from the generated Intersection Surface preview.

## 10. Test Plan

Add or update tests for:

- T-intersection still ready after n-leg refactor
- cross-intersection leg graph has four legs
- cross-intersection corner graph has four curb-return corners
- enhanced boundary loop is closed and non-self-crossing
- `Intersection Surface` uses `curb_return_envelope` when available
- rectangular fallback is diagnostic and traceable
- shared breakline audit remains ready or reports targeted diagnostics

Run:

- focused Python contract tests
- FreeCADCmd smoke for T preset
- FreeCADCmd smoke for cross preset
- manual QA in FreeCAD GUI

## 11. Non-goals

- Do not implement roundabout-specific logic in this pass.
- Do not generate cross intersections by repairing generated meshes.
- Do not merge ordinary `Slope Face Surface` and `Intersection Slope Face Surface`.
- Do not make preview highlight geometry source truth.
- Do not hide rectangular fallback; it must be diagnostic if used.

## 12. Acceptance Summary

The plan is complete when:

- cross intersections are represented as four-leg n-leg intersections
- central `Intersection Surface` follows curb-return envelope boundaries
- T intersections still work as a three-leg case
- slope/tie panels are generated per leg and per gap
- shared breakline audit uses the same canonical boundary edges across surface families
- Intersections review explains the boundary mode and any fallback reason
