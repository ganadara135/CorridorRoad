# V1 Intersection Boundary Loop Plan

Date: 2026-06-29
Status: In progress
Scope: source-driven outer intersection boundary loop and shared-breakline ownership

## Purpose

This plan promotes the visible cyan perimeter requested in manual QA into an authoritative v1 result contract.

The current intersection work can generate several surface pieces, but the intersection does not yet have a single explicit outer boundary that all adjacent surfaces consume.

That is the root problem.

The correct order is:

```text
Intersection source/evaluation data
-> Intersection Boundary Loop
-> Shared Boundary Graph / Shared Breaklines
-> Intersection Surface, Intersection Slope Face Surface, Design Surface, ordinary Slope Face Surface
-> Preview
```

Surface generation must not define the intersection boundary.

## Core Rule

The intersection boundary loop is source/result truth.

Generated meshes, preview objects, and visually convenient cleanup triangles must not become the source of the boundary.

If the loop cannot be built from source/evaluation contracts, the system must return diagnostics instead of silently drawing a replacement boundary.

## Current Failure

The current implementation still shows:

- no reliable outer intersection perimeter
- surface pieces that appear close but do not share boundary identity
- gaps between dedicated `Intersection Slope Face Surface` and ordinary corridor surfaces
- overlaps near main-road / side-road tie-in areas
- temporary upper or lower cells that solve a local fill but do not express the full intersection boundary

This happens because each surface builder still has too much freedom to derive its own edge.

Manual QA on 2026-06-30 exposed a deeper boundary-loop failure:

- the expected cyan/teal perimeter is not drawn in the intended stair-stepped outer intersection shape
- the dedicated `Intersection Slope Face Surface` cannot fill the missing upper tie-in areas because the authoritative perimeter is not available
- current smoke checks can pass even when the displayed perimeter is wrong
- `evaluate_boundary_loops()` still uses a convex-hull style boundary candidate, which creates a broad outer shell rather than tracing source-owned perimeter segments

Therefore, surface fill and residual clipping work must pause until the boundary loop evaluator is repaired.

## Target Contract

Add a dedicated result contract:

`IntersectionBoundaryLoopResult`

### Boundary Loop Row

`IntersectionBoundaryLoopRow`

Fields:

- `loop_id`
- `intersection_id`
- `loop_role`
- `status`
- `closed`
- `source_status`
- `point_count`
- `segment_count`
- `area_xy`
- `bbox_xy`
- `source_refs`
- `segment_refs`
- `consumer_roles`
- `diagnostics`
- `recommended_action`

Loop roles:

- `outer_intersection_boundary`
- `pavement_patch_boundary`
- `slope_face_transition_boundary`
- `curb_return_outer_boundary`
- `main_side_tie_boundary`

### Boundary Segment Row

`IntersectionBoundarySegmentRow`

Fields:

- `segment_id`
- `intersection_id`
- `loop_ref`
- `segment_role`
- `from_point_ref`
- `to_point_ref`
- `from_xyz`
- `to_xyz`
- `source_refs`
- `expected_consumers`
- `shared_breakline_ref`
- `graph_edge_ref`
- `diagnostics`

Segment roles:

- `patch_to_design_surface`
- `patch_to_intersection_slope_face`
- `intersection_slope_face_to_corridor_slope_face`
- `curb_return_to_intersection_slope_face`
- `main_road_tie`
- `side_road_tie`
- `control_area_outer`

Expected consumers:

- `intersection_surface`
- `intersection_slope_face_surface`
- `design_surface`
- `slope_face_surface`

## Source Inputs

Build the boundary loop from these sources, in this order:

1. `IntersectionModel`
2. `IntersectionTopologyResult`
3. `IntersectionEdgeNetworkResult`
4. `IntersectionSurfaceZoneResult`
5. `IntersectionSlopeFaceBoundaryResult`
6. Applied Section side-slope and daylight result rows
7. Control-area station spans and leg tie-in ranges

Fallback may be used only when it is:

- diagnostic
- traceable
- marked as fallback
- not persisted as accepted source intent

## Boundary Construction Strategy

### 1. Collect Candidate Segments

Collect candidate perimeter segments from:

- control-area outer edges
- curb-return exterior arcs
- pavement patch tie edges
- Applied Section side-slope outer boundaries
- daylight contact boundaries
- main-road and side-road tie-in station boundaries

Each candidate must preserve source refs.

### 2. Normalize Endpoints

Snap endpoints by tolerance into canonical boundary nodes.

Diagnostics:

- `intersection_boundary_endpoint_not_snapped`
- `intersection_boundary_duplicate_node`
- `intersection_boundary_endpoint_missing`

### 3. Assemble Closed Loop

Create one deterministic outer loop for the intersection.

Rules:

- every node in the final loop must have degree 2
- the loop must be closed in XY and 3D within tolerance
- self-crossing loops are rejected
- loops with tiny area are rejected
- internal patch seams are not allowed to masquerade as outer boundary
- convex-hull assembly is not allowed as the accepted primary boundary
- convex hull may be used only as a diagnostic fallback, with warning/error status and explicit diagnostics
- the accepted loop must preserve source segment order and non-convex perimeter shape where the intersection source requires it

Diagnostics:

- `intersection_boundary_loop_open`
- `intersection_boundary_loop_self_crossing`
- `intersection_boundary_loop_area_too_small`
- `intersection_boundary_internal_edge_used_as_outer`
- `intersection_boundary_convex_hull_fallback`
- `intersection_boundary_graph_degree_invalid`
- `intersection_boundary_graph_chain_unclosed`

### 4. Assign Ownership

Classify each boundary segment by which surfaces should consume it.

Examples:

```text
patch_to_intersection_slope_face:
  intersection_surface
  intersection_slope_face_surface

intersection_slope_face_to_corridor_slope_face:
  intersection_slope_face_surface
  slope_face_surface

patch_to_design_surface:
  intersection_surface
  design_surface
```

This ownership map becomes the input for Shared Boundary Graph rows.

### 5. Emit Shared Breaklines

Every accepted boundary segment must emit or reference one shared breakline edge.

Adjacent surfaces must consume the same breakline id, not a geometrically similar line.

## Integration Points

### Evaluation Service

Add an evaluation function:

```text
evaluate_intersection_boundary_loops(intersection_model, topology, edge_network, surface_zones, slope_face_boundaries, applied_sections)
```

This function returns `IntersectionBoundaryLoopResult`.

### Shared Boundary Graph

`IntersectionSharedBoundaryGraphResult` should consume `IntersectionBoundaryLoopResult`.

The graph should not invent outer boundary identity if the loop result is missing or blocked.

### Surface Builders

Surface builders must change from:

```text
surface-specific boundary inference
```

to:

```text
consume boundary loop segment refs
```

Required behavior:

- `Intersection Surface` stops at the loop boundary.
- `Intersection Slope Face Surface` fills only loop-owned transition cells.
- ordinary `Design Surface` is clipped outside the boundary.
- ordinary `Slope Face Surface` stops at shared slope-face boundary edges.

### Build Parametric UI

Expose a boundary loop row group in the `Intersections` tab:

- row group: `boundary_loop`
- status: ready / warning / error
- loop id
- closed state
- segment count
- area
- diagnostics
- recommended action

Double-click should highlight only the authoritative cyan boundary loop.

### Breakline Audit

Add boundary-specific checks:

- boundary segment has shared breakline ref
- expected consumers are present
- adjacent surfaces consume the same edge id
- no surface owns an edge outside the boundary loop

## Implementation Phases

### Phase 1 - Contract Definition

Status: Done

Tasks:

| Task id | Status | Work item | Primary files | Acceptance criteria |
| --- | --- | --- | --- | --- |
| IBL-001 | Done | Add `IntersectionBoundaryLoopResult` dataclasses. | `models/result/` | Boundary loop and segment rows serialize cleanly and preserve source refs. |
| IBL-002 | Done | Export the result contract from the v1 result package. | `models/result/__init__.py` | Imports work from command and tests. |
| IBL-003 | Done | Add parser/formatter helpers for review rows. | `cmd_build_corridor.py` or helper module | Rows can be displayed in Intersections and Breakline Audit tabs. |

Progress:

- Added `IntersectionBoundaryLoopResult`, `IntersectionBoundaryLoopRow`, and `IntersectionBoundarySegmentRow`.
- Exported the contract from the v1 result package.
- Added Intersections-tab rows for `boundary_loop`.

### Phase 2 - Candidate Extraction

Status: Partial

Tasks:

| Task id | Status | Work item | Primary files | Acceptance criteria |
| --- | --- | --- | --- | --- |
| IBL-010 | Partial | Extract control-area outer candidate segments. | `intersection_evaluation_service.py` | T preset produces main and side-road outer tie candidates. |
| IBL-011 | Partial | Extract curb-return exterior arc candidate segments. | `intersection_evaluation_service.py` | Curb-return arc participates in the outer boundary, not only in local surface cells. |
| IBL-012 | Done | Extract Applied Section side-slope/daylight boundary candidates. | `intersection_evaluation_service.py` | Boundary candidates come from Applied Section results, not Subassembly preview rows. |
| IBL-013 | Partial | Preserve source refs and expected consumer roles on every candidate. | result contract/tests | Candidate diagnostics identify missing source ownership. |

Progress:

- Boundary evaluation first tries surface-zone edge refs.
- Degenerate edge-network endpoints are ignored instead of becoming a false boundary.
- When edge-network candidates are insufficient, ready `IntersectionSlopeFaceLoopResult` rows supply Applied Section-derived boundary candidate points.
- Candidate source is diagnostic and traceable through loop, surface-zone, edge-network, and Applied Section refs.

### Phase 3 - Loop Assembly

Status: Partial

Tasks:

| Task id | Status | Work item | Primary files | Acceptance criteria |
| --- | --- | --- | --- | --- |
| IBL-020 | Partial | Snap candidate endpoints into canonical boundary nodes. | evaluation service | Duplicate endpoint coordinates collapse into one node id. |
| IBL-021 | Reopened | Assemble deterministic closed outer loop. | evaluation service | T preset produces one `outer_intersection_boundary` loop from connected source segments, not convex-hull shortcuts. |
| IBL-022 | Partial | Reject open, self-crossing, tiny-area, and internal-edge loops. | evaluation service/tests | Invalid loops stay diagnostic and do not drive surface generation. |
| IBL-023 | Reopened | Add contract tests for the cyan perimeter shape around the T preset. | `tests/contracts/v1/` | Expected segment roles are present, closed, and not accepted when produced only by convex hull. |
| IBL-024 | Partial | Replace primary convex-hull boundary assembly with segment-graph loop tracing. | `intersection_evaluation_service.py` | Accepted `outer_intersection_boundary` is assembled from connected source segments. |
| IBL-025 | Partial | Classify and exclude internal/diagonal/shortcut candidate edges before loop acceptance. | evaluation service/tests | Explicit internal/shortcut/diagnostic/preview candidate segments are filtered before tracing and reported with exclusion diagnostics. |
| IBL-026 | Partial | Add diagnostics for graph degree, open chains, fallback use, and rejected shortcuts. | evaluation service/tests | Candidate graph diagnostics now report segment/node/component counts plus open and branch nodes before loop tracing. |
| IBL-027 | Partial | Strengthen T preset contract/smoke checks to validate the displayed perimeter shape. | tests | T smoke now fails if the ready boundary loop degenerates to a simple bbox/convex-hull-style perimeter. |
| IBL-028 | Pending | Route boundary-loop highlight from accepted segment rows and verify expected cyan outline. | highlight helpers/tests | Double-click produces one visible perimeter following source segment order. |
| IBL-029 | Partial | Resolve edge-network source endpoints from topology anchor, station spans, and edge policy offsets. | evaluation service/tests | Leg and curb-return edge rows are no longer degenerate `(0,0,0)` placeholders. |
| IBL-030 | Partial | Promote ready `IntersectionSlopeFaceLoopResult` loop segments into boundary graph candidates. | evaluation service/tests | Applied Section side-slope loop segments are visible to boundary tracing before hull fallback. |
| IBL-031 | Partial | Split competing slope-face loop components before selecting the outer perimeter. | evaluation service/tests | Multiple closed side-slope strip loops are now diagnosed as competing closed components instead of being merged into one invalid graph or accepted as the outer perimeter. |
| IBL-032 | Partial | Select or construct the authoritative outer perimeter from competing source components. | evaluation service/tests | T preset now constructs a ready rectilinear edge-network envelope from leg pavement/daylight and curb-return source edges before competing strip-loop fallback. |
| IBL-033 | Partial | Prevent rectilinear envelope fallback from being accepted for skew/non-axis source edges. | evaluation service/tests | Non-axis-aligned edge-network rows skip the bbox-union envelope and remain diagnostic until a leg-frame source polygon builder is available. |
| IBL-034 | Partial | Build source perimeter polygons in leg-local frames for skewed intersections. | evaluation service/tests | Skewed leg pavement/daylight source edge pairs can produce an accepted non-rectilinear boundary without using preview meshes. |
| IBL-035 | Partial | Preserve curb-return arc source samples on edge-network rows. | result model/evaluation service/tests | Curb-return edge rows expose source-derived `arc_center_xyz` and ordered `arc_points_xyz` for later boundary-loop consumption. |
| IBL-036 | Partial | Consume curb-return arc samples in the authoritative boundary loop. | evaluation service/tests | Segment-graph boundary-loop assembly expands `arc_points_xyz` into curb-return arc segment rows; rectilinear envelope substitution is guarded so unsafe replacements cannot shrink the accepted perimeter. |
| IBL-037 | Partial | Diagnose unsafe rectilinear curb-arc substitution with perimeter extents. | evaluation service/tests | Rejected arc substitution reports original and replacement bbox extents so ownership splits can be reviewed. |
| IBL-038 | Partial | Split rectilinear envelope spans by perimeter owner before arc substitution. | evaluation service/tests | Rectilinear side refs now prefer the rectangle that owns that outer side, and arc replacement candidates are scored by lowest mixed ownership before mutation. |
| IBL-039 | Partial | Route curb-return bridge gaps into the shared-boundary graph instead of the outer loop. | `cmd_build_corridor.py` / contract tests | Missing curb bridge diagnostics become direction-deduped diagnostic shared breakline candidates and `curb_return_bridge_cell` rows for `Intersection Slope Face Surface` closure without changing authoritative outer-loop readiness. |

Progress:

- Added deterministic convex-hull outer loop assembly for the first boundary-loop slice.
- Added area, bbox, closed-state, source refs, segment refs, consumer roles, and recommended action metadata.
- Added FreeCADCmd-covered contract tests for closed-loop creation and insufficient-point failure.
- 2026-06-30 manual QA found that this convex-hull loop is not the required authoritative intersection perimeter. Phase 2 is reopened and convex hull is now fallback-only.
- Boundary loop evaluation now attempts connected segment-graph tracing before hull fallback.
- Convex-hull fallback loops are marked `warning`/`fallback_warning`, carry explicit diagnostics, and are not promoted to shared breakline handoff.
- Added contract coverage to prevent convex-hull fallback from being accepted as an authoritative outer boundary.
- Edge-network evaluation now resolves leg and curb-return edge endpoints from topology anchor/station context instead of leaving `(0,0,0)` placeholders.
- Contract tests now assert that leg and curb-return edge rows are non-degenerate and do not emit `edge_network_endpoint_degenerate`.
- Ready `IntersectionSlopeFaceLoopResult` loops are now promoted into boundary graph candidates as source-derived segments with Applied Section/source-zone refs.
- Contract tests now assert that a single closed slope-face loop can be promoted into an accepted boundary-loop segment graph.
- Competing closed side-slope loop components are now diagnosed instead of being merged into one overloaded graph or accepted as the outer perimeter.
- T preset edge-network source envelopes now produce a ready non-convex rectilinear boundary loop from leg pavement/daylight and curb-return source edges.
- Rectilinear source envelopes are now skipped for non-axis-aligned edge-network rows so skewed intersections cannot be accepted from an XY bbox shortcut.
- Skewed leg pavement/daylight source edges now have a first-pass leg-frame polygon union path. It splits source polygon edges at intersections, removes internal edge fragments, and traces the accepted outer perimeter without using generated meshes.
- Curb-return edge-network rows now preserve source-derived arc center and sampled arc points as result contract fields.
- Boundary-loop segment-graph assembly now expands curb-return `arc_points_xyz` into sampled curb-return segment rows.
- Rectilinear T source-envelope assembly now attempts curb-return arc substitution only when the replacement preserves the accepted perimeter extents; unsafe bbox-changing replacements are diagnosed and rejected.
- Unsafe rectilinear curb-arc substitutions now report both original and replacement bbox extents, making it clear when adjacent leg-owned perimeter spans would be removed.
- Rectilinear curb-arc substitution now checks candidate span ownership before mutation. Mixed curb/leg-owned spans are rejected with `intersection_boundary_curb_arc_span_mixed_ownership`.
- Rectilinear perimeter side refs now come from the source rectangle that actually owns each exterior side instead of blindly inheriting every overlapping cell ref.
- Curb-return arc replacement candidate selection now prioritizes zero mixed-ownership spans before longer or curb-ref-heavy paths.
- Boundary-loop tracing now filters explicit internal, shortcut, diagonal, diagnostic, preview, highlight, and seam candidate segments before outer-loop assembly.
- Contract coverage now verifies that an explicit shortcut segment cannot appear in accepted boundary-loop segment source refs.
- Boundary-loop evaluation now emits candidate graph diagnostics with segment count, node count, component count, degree-1 node count, and branch-node count before tracing.
- T intersection smoke now checks that the ready boundary loop has a non-trivial point/segment count and is not accepted from convex-hull fallback.
- Curb-return arc substitution now reports candidate span counts, best mixed-owner row count, best span length, and a dedicated `intersection_boundary_curb_arc_pure_span_missing` warning when no safe curb-owned perimeter span exists.
- Curb-return arc substitution now also reports the missing rectilinear bridge segments that would be required before a pure curb-owned span can be promoted into the authoritative loop.
- Missing curb-return bridge diagnostics are now split to subspan precision, and bridge promotion is blocked when the mixed span contains outer bbox owner edges that would be removed from the authoritative perimeter.
- Missing curb-return bridge diagnostics are now preserved as direction-deduped `curb_return_bridge_to_intersection_slope_face` shared breakline candidates. These candidates are diagnostic shared-graph inputs, not accepted outer boundary-loop segments.
- `IntersectionSlopeFaceCellResult` now consumes those bridge candidates as `curb_return_bridge_cell` rows paired with the nearest curb-return slope-face breakline, giving the dedicated surface builder a traceable closure input for the curb bridge gap.
- Bridge-to-curb pairing now prefers shared endpoints before nearest-distance matching, so the cell closure follows shared breakline identity when a bridge candidate touches an existing curb-return boundary segment.
- The T intersection dedicated Slope Face Surface smoke now asserts that a ready `curb_return_bridge_cell` is exposed in both cell refs and audit rows, preventing the bridge closure handoff from silently disappearing.
- Boundary-loop segment role classification now uses source refs for side-road tie caps. T preset `leg:02` outer cap segments are classified as `side_road_tie` instead of falling through to the generic lower-horizontal curb-return role.
- Rectilinear perimeter segments now preserve path-aware owner markers in `source_refs`, such as `intersection-boundary-owner:leg:01:north` and `intersection-boundary-owner:leg:02:south`. Arc substitution, bridge diagnostics, and future shared-breakline consumers can now identify which source group and side owns each accepted outer-boundary span without re-guessing from generated geometry.
- Breakline Audit `graph_boundary_loop` rows now expose those owner markers as `owner_refs=...` in the row notes. This makes the shared-boundary graph review surface show which leg/side owns each boundary-loop edge instead of hiding ownership inside a long source-ref list.
- Breakline Audit `graph_boundary_loop` rows now also expose `owner_consumers=owner->consumer+consumer...`, so QA can see which surfaces consume each owner-tagged boundary segment before moving on to visual surface gaps.
- Owner-tagged boundary-loop rows now report `owner_missing_consumers=owner->consumer+consumer...` and become warning rows when an expected surface consumer is absent. This makes side-road tie and main-road tie handoff failures visible before checking the 3D surface fill.
- Breakline Audit now adds `graph_boundary_owner` summary rows grouped by `intersection-boundary-owner:*`. These rows aggregate edge count, roles, consumers, graph refs, and missing consumers per owner span so users can review `leg:01`, `leg:02`, and curb-return ownership without opening every edge row.
- Dedicated `Intersection Slope Face Surface` preview objects now expose `IntersectionBoundaryOwnerStatus`, owner counts, owner refs, owner audit rows, and an owner summary. This lets QA separate boundary-owner handoff readiness from remaining surface fill or cell-generation gaps.
- Dedicated `Intersection Slope Face Surface` preview objects now expose `IntersectionSlopeFaceOwnerFillReadinessStatus` and summary metadata. This compares ready boundary-owner handoff against generated triangle components, making it clear when remaining gaps are cell/strip generation issues rather than shared-boundary ownership issues.
- Dedicated `Intersection Slope Face Surface` preview objects now expose graph-fill linkage diagnostics for owner spans: `IntersectionSharedBoundaryGraphSurfaceBoundaryRefs`, `IntersectionSlopeFaceOwnerGraphFillLinkStatus`, `IntersectionSlopeFaceOwnerGraphFillBoundaryRefCount`, `IntersectionSlopeFaceOwnerGraphFillLinkedRefs`, and `IntersectionSlopeFaceOwnerGraphFillUnlinkedRefs`. Graph-fill cells may be built from transition/cell-closure edges rather than direct owner-boundary edges, so zero direct owner links is reported as `not_applicable` when graph boundary refs exist instead of being treated as a surface failure.
- Current remaining blocker: replacing rectilinear curb spans with true arcs requires path-aware perimeter ownership so arc substitution does not remove adjacent main-road or side-road outer boundary spans.

### Phase 4 - Shared Breakline Handoff

Status: Partial

Tasks:

| Task id | Status | Work item | Primary files | Acceptance criteria |
| --- | --- | --- | --- | --- |
| IBL-030 | Done | Emit shared breakline rows from boundary loop segments. | `cmd_build_corridor.py` / shared breakline builder | Every accepted boundary segment has a shared breakline ref. |
| IBL-031 | Done | Feed boundary loop refs into `IntersectionSharedBoundaryGraphResult`. | graph builder | Graph edge identity originates from boundary loop segments. |
| IBL-032 | Done | Add audit rows for missing consumers and foreign surface edges. | Breakline Audit helpers | Audit fails if adjacent surfaces do not consume the same boundary edge id. |

Progress:

- `corridor_intersection_shared_breakline_result()` now promotes accepted `IntersectionBoundaryLoopResult` segment rows into `SharedBreaklineRow` records.
- Boundary loop segment roles now pass through `IntersectionSharedBoundaryGraphResult` instead of being discarded as review-only linework.
- T preset regression now checks shared-breakline role summary and graph consumer rows for boundary-loop roles.
- Shared Boundary Graph audit rows now preserve source refs, so boundary-loop-derived graph edges are visible as `graph_boundary_loop` detail rows in Breakline Audit.

### Phase 5 - Surface Consumer Refactor

Status: Partial

Tasks:

| Task id | Status | Work item | Primary files | Acceptance criteria |
| --- | --- | --- | --- | --- |
| IBL-040 | Partial | Make `Intersection Surface` consume loop boundary edges. | `cmd_build_corridor.py` | Intersection patch stops at boundary loop. |
| IBL-041 | Partial | Make dedicated `Intersection Slope Face Surface` consume loop-owned transition segments. | `cmd_build_corridor.py` | Dedicated surface fills the perimeter band but does not create internal curb-return rectangles. |
| IBL-042 | Partial | Clip ordinary `Design Surface` and ordinary `Slope Face Surface` against loop-owned edges. | corridor surface builders | Ordinary surfaces stop at the same edge id. |
| IBL-043 | Partial | Remove or demote local patch logic superseded by boundary loop ownership. | surface builders | No temporary cell can override the authoritative boundary. |

Progress:

- `Intersection Surface` now applies shared breakline constraint-edge coverage before running its shared breakline audit.
- Boundary-loop-derived shared breakline refs are exposed on the Intersection Surface preview as `SharedBreaklineBoundaryLoopRefs`.
- Constraint coverage stats are exposed as preview metadata, so audit/QA can confirm boundary-loop handoff before deeper clipping work.
- Dedicated `Intersection Slope Face Surface` now carries boundary-loop-derived shared breakline refs in both `boundary_refs` and preview metadata.
- Dedicated `Intersection Slope Face Surface` now treats boundary-loop transition rows as metadata-only handoff rows. The authoritative boundary-loop shared breaklines remain traceable for coverage/audit, but transition rows no longer emit visible strip or corner-fill triangles because those strips created alignment-direction artifacts.
- Boundary-loop transition row counts, refs, generation mode, row diagnostics, and diagnostics are exposed on the dedicated surface preview. Visible transition role/width summaries intentionally remain empty unless a future source-owned local cell generator explicitly emits transition mesh.
- Curb-return perimeter generation now limits Applied Section side-slope candidate selection to the local curb-return search envelope. Remote side-slope points are rejected instead of being projected into long perimeter fans.
- Shared-boundary `upper_*_transition_cell` rows remain contract/audit rows but no longer emit visible graph-cell surface triangles. Visible upper alignment-side surfaces must come from a future explicit local cell contract, not broad graph handoff rows.
- `main_to_side_*_tie_cell` rows remain contract/audit rows but no longer emit visible cell triangles, because their inferred tie span can extend away from the intersection and create long alignment-side wedge artifacts.
- When the local curb-return search envelope has no suitable Applied Section side-slope candidate, the dedicated surface reports `no_curb_return_perimeter_strip` with an `outer_point_missing` diagnostic instead of creating remote alignment-direction geometry.
- Dedicated `Intersection Slope Face Surface` now exposes `IntersectionBoundaryLoopTransitionQAStatus`, notes, and recommended action. If this status is ready but a visual gap remains, QA should inspect ordinary Design/Slope Face boundary-loop ownership and near-boundary kept triangles rather than the dedicated transition consumer contract.
- Ordinary `Design Surface` and ordinary `Slope Face Surface` previews now expose boundary-loop shared refs and shared-breakline constraint coverage metadata, so QA can confirm that adjacent surfaces are consuming the same loop-owned edge ids.
- Shared-breakline constraint generation now separately reports boundary-loop segment count, preserved edge count, and refs for every consumer surface.
- Ordinary surface intersection exclusion now prefers the ready `outer_intersection_boundary` loop as the clipping polygon before falling back to practical or patch-boundary exclusion.
- Exclusion quality now reports the boundary-loop result id, loop id, point count, and segment count for ordinary surface QA.
- Broad `patch_to_design` fallback breakline generation is now suppressed when a ready authoritative boundary loop exists; per-contact patch/design breaklines remain available for traceable tie-in review.
- Raw ready-loop fan generation for dedicated `Intersection Slope Face Surface` is suppressed when preferred source-driven perimeter/cell/graph/boundary-loop transition components already generated geometry; the source loops remain traceable through preview metadata.
- Shared-boundary graph internal seams now expose separate count/ref metadata so cell closure aids are distinguishable from authoritative outer boundary edges.
- Breakline Audit display rows now expose shared-boundary graph internal seams as `graph_internal_seam` rows with dedicated highlight refs and recommended action text, separate from authoritative boundary-loop edge rows.
- Breakline Audit graph highlights now use a separate internal-seam highlight object, label, diagnostic kind, and amber styling so closure aids do not look like authoritative outer boundary edges.
- Breakline Audit display rows now include `Boundary Loop Handoff` detail rows with boundary-loop ref, constraint segment, and constraint edge counts. A surface with boundary-loop refs but no constraint edges is shown as warning.
- T intersection smoke now asserts that the Breakline Audit exposes ready `Boundary Loop Handoff` rows for Intersection, Design, and ordinary Slope Face consumers.
- Ordinary Design and Slope Face previews now expose `IntersectionBoundaryLoopOwnershipStatus`/notes that require boundary-loop exclusion source, boundary-loop refs, preserved constraint edges, and valid loop points to be ready.
- Ordinary surface exclusion metadata now exposes tested triangle count and clip ratio, and ownership notes include tested/clipped/boundary-crossing diagnostics for boundary-loop clipping review.
- Breakline Audit `Boundary Loop Handoff` rows now show clipping coverage in the role summary as clipped/tested, boundary crossing count, and clip ratio.
- Ordinary surface exclusion metadata now reports near-boundary kept triangle count and max kept-boundary distance so residual geometry near the authoritative boundary can be diagnosed without treating mesh fragments as source truth.
- Breakline Audit now raises a conservative warning for ordinary Design/Slope Face consumers when near-boundary kept triangles are excessive: at least 50% of tested triangles and at least 30 triangles.
- Ordinary surface exclusion metadata now stores near-boundary kept triangle centroid rows, and Breakline Audit can show an orange 3D residual marker highlight for those clipped-surface QA candidates.
- Existing T and non-T smoke checks pass with the new handoff metadata.

### Phase 6 - UI, Highlight, And Manual QA

Status: Planned

Tasks:

| Task id | Status | Work item | Primary files | Acceptance criteria |
| --- | --- | --- | --- | --- |
| IBL-050 | Done | Add `boundary_loop` rows to the Intersections tab. | `cmd_build_corridor.py` | Users see ready/warning/error before surface rows. |
| IBL-051 | Done | Add double-click highlight for the cyan outer boundary loop. | highlight helpers | 3D View shows one continuous cyan perimeter and exposes loop metadata for QA. |
| IBL-052 | Done | Add Breakline Audit detail rows for boundary loop consumers. | audit helpers | User can see which surface is missing from a shared boundary. |
| IBL-053 | Done | Update manual QA with boundary loop inspection steps. | `V1_INTERSECTION_MANUAL_QA.md` | QA asks user to inspect outer loop before judging surfaces. |

Progress:

- Added `boundary_loop` rows to Build Parametric > Intersections.
- Added focus/double-click highlight using a cyan perimeter polyline.
- T preset smoke verifies the row and highlight object.
- Boundary-loop highlights now expose `BoundaryLoopRole`, closed state, point count, segment count, segment refs, segment role summary, source refs, area, bbox, diagnostics, and recommended action on the highlight object.
- Boundary-loop highlights now also expose shared handoff metadata: `BoundaryLoopSharedBreaklineRefs`, `BoundaryLoopGraphEdgeRefs`, `BoundaryLoopGraphConsumerSummary`, and `BoundaryLoopGraphMissingConsumerCount`. This lets QA verify that the cyan perimeter is not only drawn, but also promoted into shared graph edges consumed by adjacent surfaces.
- Boundary-loop focus highlights are routed to Review > Issues, not Alignment/Profile containers.
- Curb-return arc replacement now rejects self-crossing rebuilt boundary loops and falls back to the source-derived rectilinear edge-network envelope. This prevents `outer_intersection_boundary` from becoming an error row when the arc substitution order crosses itself.
- The T preset smoke now verifies the accepted outer boundary loop contains the expected mixed segment roles: `patch_to_design_surface`, `intersection_slope_face_to_corridor_slope_face`, `main_road_tie`, and `side_road_tie`. Curb-return handoff remains verified through shared graph/cell rows rather than the outer boundary role summary.
- Manual QA now asks the user to inspect the boundary loop before judging surface fill.

### Phase 7 - Regression

Status: Partial

Tasks:

| Task id | Status | Work item | Primary files | Acceptance criteria |
| --- | --- | --- | --- | --- |
| IBL-060 | Done | Add FreeCADCmd T preset boundary loop smoke. | `tests/regression/` | Smoke fails if no closed outer boundary loop exists. |
| IBL-061 | Done | Extend Cross, Skewed, and Y readiness smoke with boundary loop checks. | `tests/regression/` | non-T presets expose truthful boundary readiness. |
| IBL-062 | Done | Add graph consumer regression for boundary loop shared edge ids. | contract tests | Adjacent surfaces must consume the same boundary edge ids. |

Progress:

- `smoke_intersection_t_slope_face_surface.py` now requires a ready `outer_intersection_boundary` row and focus highlight.
- `smoke_intersection_non_t_slope_face_readiness.py` now requires ready boundary-loop rows for Cross, Skewed, and Y presets.
- `test_intersection_shared_boundary_graph_builder.py` now verifies that boundary-loop segments promoted to shared breaklines are exposed as the same graph edge ids across all expected surface consumers.
- Dedicated `Intersection Slope Face Surface` preview now reports boundary-loop graph coverage: `IntersectionBoundaryLoopGraphCoverageStatus`, graph edge count, consumer edge count, filled edge count, missing edge count, non-consumer edge count, role summary, and edge ref lists. This separates source handoff failures from actual fill-generation gaps and shows which boundary-loop roles are intentionally outside dedicated slope-face ownership.
- Dedicated `Intersection Slope Face Surface` preview now also reports `IntersectionBoundaryLoopGraphNonConsumerEdgeRows`. Each row preserves edge id, edge role, left/right owners, consumers, authoritative boundary-loop segment refs, and owner refs so QA can identify exactly which perimeter segments are excluded from dedicated slope-face ownership before changing consumer policy.
- Outer `patch_to_design_surface` boundary-loop segments are now treated as shared intersection perimeter handoff edges for `Intersection Slope Face Surface` as well as `Intersection Surface` and `Design Surface`. This makes the dedicated slope-face preview consume and fill all authoritative T preset boundary-loop graph edges instead of leaving the patch-to-design portion outside its ownership.

## Acceptance Criteria

The plan is complete when:

- the T preset produces one highlighted cyan `outer_intersection_boundary` loop
- the loop is closed, non-self-crossing, and has meaningful area
- every boundary segment has source refs
- every boundary segment has expected consumer roles
- every boundary segment has a shared breakline or graph edge ref
- `Intersection Surface`, `Intersection Slope Face Surface`, `Design Surface`, and ordinary `Slope Face Surface` consume the same boundary edge ids where they meet
- Breakline Audit reports missing consumers clearly
- surface generation no longer relies on local patch cleanup to define the intersection edge

## Non-goals

- Do not solve full roundabout production geometry in this plan.
- Do not infer boundary loops from preview meshes.
- Do not make generated triangles the source of boundary truth.
- Do not hide failed boundary assembly by drawing cosmetic perimeter lines.

## Current Recommendation

Start with Phase 1 and Phase 2 for the T preset only.

Do not continue refining surface fill logic until the boundary loop contract can produce and highlight the cyan perimeter reliably.
