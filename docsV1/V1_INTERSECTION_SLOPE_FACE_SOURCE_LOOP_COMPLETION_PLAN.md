# V1 Intersection Slope Face Source Loop Completion Plan

Date: 2026-06-28  
Status: In progress  
Scope: make the missing Slope Face Surface around intersections generate from Applied Section side-slope boundaries and accepted intersection source/result contracts

## Purpose

This plan addresses the visible gap around the intersection perimeter where `Slope Face Surface` or dedicated `Intersection Slope Face Surface` is not generated.

The previous plan, `V1_INTERSECTION_SLOPE_FACE_SURFACE_READY_LOOP_PLAN.md`, completed the safety and review layer:

- explain why `Intersection Slope Face Surface` is missing
- prevent warning/error loops from generating hidden repair triangles
- generate a dedicated preview when a complete ready-loop contract exists
- expose Results, Visibility, highlight, and manual QA diagnostics

That work is related, but it does not yet solve the actual perimeter fill problem.

The remaining product problem is:

- the default T intersection preset does not produce accepted, closed, non-degenerate Slope Face loop contracts
- ordinary `Slope Face Surface` is clipped or suppressed near the intersection footprint
- dedicated `Intersection Slope Face Surface` is skipped because ready loop count is zero
- the user sees a gap around the curb-return and side-slope tie-in area

## Core Rule

Do not fill the gap with mesh repair triangles.

The fix must make source/result contracts complete enough for the surface builder to generate the perimeter surface.

The source chain should be:

```text
IntersectionModel
  -> TopologyResult
  -> EdgeNetworkResult
  -> SurfaceZoneResult
  -> AppliedSectionSet side-slope boundary rows
  -> IntersectionSlopeFaceLoopResult ready loop rows
  -> V1CorridorIntersectionSlopeFaceSurfacePreview
```

Generated preview geometry, ordinary Slope Face mesh fragments, or deleted/hid tree objects must not become source truth.

## Current Observed Failure

In the current T intersection preset case before the boundary-strip fix:

- `V1CorridorIntersectionSurfacePreview` can be generated.
- ordinary `Slope Face Surface` exists outside the control area.
- central pavement and curb-return/intersection surface are visible.
- the perimeter slope area around the intersection is not filled.
- `Intersection Slope Face Surface` remains missing.

The current FreeCADCmd smoke revealed a critical root cause:

- preset edge-network rows can be accepted as source rows but still have degenerate endpoint coordinates such as `(0,0,0) -> (0,0,0)`
- degenerate edge rows produce `slope_face_loop_degenerate_edge_refs`
- loop point count collapses to `1`
- loop remains `diagnostic_only:blocked`
- no dedicated surface is generated

This means the remaining task is not a display toggle issue.

It is a source/result geometry handoff issue.

After the first ready-loop pipeline slice, FreeCADCmd could create `V1CorridorIntersectionSlopeFaceSurfacePreview`, but user visual QA still showed no meaningful perimeter fill.

That exposed a second failure:

- the preview-object smoke only proved that an object and triangles existed
- the temporary Applied Section `best strip group` loop did not represent the intersection perimeter
- the generated geometry followed a longitudinal side-slope strip rather than the gap between the Intersection Surface boundary and the Applied Section side-slope boundary
- therefore the actual visible curb-return perimeter gap remained

The real acceptance condition must be perimeter coverage, not object existence.

## Design Direction

Intersection-owned Slope Face should use Applied Section side-slope boundaries as the geometry carrier where edge-policy source rows alone do not provide sufficient endpoints.

The evaluator should preserve source ownership:

- Intersection source rows own which legs, control areas, curb returns, and edge families participate.
- Applied Sections own evaluated side-slope/daylight boundary geometry at stations.
- Surface Zone rows own which boundary families should form an intersection-owned slope perimeter.
- Slope Face Loop rows own the closed loop contract consumed by the dedicated surface builder.

## Expected Result

For a valid T intersection preset after Build Sections and Build Parametric:

- at least one `slope_face_loop` row is `ready`
- ready loop rows have `generation=surface_candidate:ready`
- ready loop rows have `closed_xy=yes`
- `V1CorridorIntersectionSlopeFaceSurfacePreview` exists
- Results row `Intersection Slope Face Surface` is `ready`
- Visibility checkbox is enabled
- the dedicated surface fills the intersection perimeter side-slope area without entering central pavement
- ordinary `Slope Face Surface` remains separate and does not fill the intersection pavement/control-area interior

## Non-goals

- Do not restore forced rectangular white boundary patches.
- Do not append arbitrary fan/repair triangles from preview geometry.
- Do not use ordinary Slope Face mesh as input source.
- Do not make warning/error loop rows generate accepted surface triangles.
- Do not merge ordinary `Slope Face Surface` and dedicated `Intersection Slope Face Surface`.

## Phase 1 - Confirm Source Geometry Gaps

Status: Done

Goal:

- identify exactly where preset source rows lose usable endpoint geometry.

Tasks:

| Task id | Status | Work item | Primary files | Acceptance criteria |
| --- | --- | --- | --- | --- |
| ISFC-001 | Done | Add diagnostics for degenerate edge-network endpoint rows. | `intersection_evaluation_service.py`, tests | Edge Network rows report which source policy/leg/control area produced zero-length endpoints. |
| ISFC-002 | Done | Record station span and alignment refs on degenerate edge diagnostics. | `intersection_evaluation_service.py` | Diagnostics include leg ref, alignment ref, station start/end, edge family, and source policy ref. |
| ISFC-003 | Done | Expose degenerate edge summary in Build Parametric `Intersections` notes. | `cmd_build_corridor.py` | User can see that loop failure is caused by degenerate edge endpoints, not surface visibility. |

Implementation note:

- edge-network diagnostics now emit `edge_network_endpoint_degenerate` with policy ref, leg ref, alignment ref, control-area ref, edge family, station span, and endpoint xyz.
- those diagnostics flow into surface-zone and slope-face-loop review notes, so a missing loop can be traced to source endpoint geometry rather than visibility.

## Phase 2 - Applied Section Side-Slope Boundary Extraction

Status: Done

Goal:

- extract source-traceable side-slope perimeter candidates from Applied Sections inside or near the intersection control area.

Tasks:

| Task id | Status | Work item | Primary files | Acceptance criteria |
| --- | --- | --- | --- | --- |
| ISFC-010 | Done | Add helper to collect Applied Section side-slope boundary segments by intersection, control area, leg, alignment, and side. | `intersection_evaluation_service.py` or new service | Returned rows preserve Applied Section id, station, alignment id, active intersection id, control area id, leg id, side, start/end point refs, and xyz endpoints. |
| ISFC-011 | Done | Prefer Applied Section `subassembly_link_rows` with `surface_role=side_slope_surface`. | Applied Section result consumers | Boundary extraction does not use Subassembly designer template preview rows. |
| ISFC-012 | Done | Fall back only to evaluated Applied Section point roles when link rows are missing. | Applied Section result consumers | Fallback is diagnostic and source/result traceable. |
| ISFC-013 | Done | Unit-test extraction for primary and side-road legs. | `tests/contracts/v1/` | Extracted boundary segments match Applied Section side-slope geometry and do not cross unrelated alignments. |

Implementation note:

- extraction consumes evaluated Applied Section `subassembly_link_rows` with `side_slope_surface` or `slope_face_surface` roles.
- the helper resolves link endpoints from evaluated Applied Section point rows and builds longitudinal strip loops across stations.
- Subassembly designer/template preview geometry is not consumed.

## Phase 3 - Surface Zone Boundary Completion

Status: Partial

Goal:

- complete `IntersectionSurfaceZoneRow` slope-face boundary refs using accepted Applied Section side-slope boundary candidates.

Tasks:

| Task id | Status | Work item | Primary files | Acceptance criteria |
| --- | --- | --- | --- | --- |
| ISFC-020 | Partial | Add slope-face boundary candidate rows linked to surface zones. | `intersection_surface_zone.py`, `intersection_evaluation_service.py` | Surface-zone result can reference Applied Section side-slope boundaries as boundary candidates. |
| ISFC-021 | Partial | Match candidates by intersection id, control area ref, leg ref, alignment ref, and station overlap. | evaluation service | Primary and side road candidates do not stitch across unrelated scopes. |
| ISFC-022 | Partial | Attach curb-return contact refs where the Applied Section boundary meets the curb-return arc/edge. | evaluation service | Boundary candidates have explicit curb-return tie-in refs or diagnostics explaining why contact is missing. |
| ISFC-023 | Done | Add diagnostics when candidate station coverage is incomplete. | evaluation service, Build Parametric notes | Missing start/end coverage blocks ready loops with actionable diagnostics. |

Implementation note:

- slope-face loop evaluation can complete degenerate surface-zone edge refs from accepted Applied Section boundary candidates.
- the earlier `best strip group` completion is retained as a diagnostic/prototype path, not as proof of visual perimeter coverage.
- explicit curb-return contact refs are still a follow-up; current boundary-strip output uses `IntersectionSlopeFaceBoundaryResult` inner/outer points.

## Phase 4 - Closed Loop Assembly From Applied Boundaries

Status: Partial

Goal:

- construct ready closed Slope Face loops from Applied Section side-slope boundary segments plus intersection edge/tie-in contracts.

Tasks:

| Task id | Status | Work item | Primary files | Acceptance criteria |
| --- | --- | --- | --- | --- |
| ISFC-030 | Partial | Extend `evaluate_slope_face_loops()` to consume completed boundary candidates. | `intersection_evaluation_service.py` | Loop rows use Applied Section boundary endpoints when edge-network endpoints are degenerate or insufficient. |
| ISFC-031 | Partial | Build endpoint graph from Applied Section boundary, curb-return contact, and pavement/daylight tie candidates. | evaluation service | Unordered candidates produce one deterministic closed loop when endpoints match within tolerance. |
| ISFC-032 | Done | Reject loops that remain open, self-crossing, or too skinny. | evaluation service | Rejected loops remain `diagnostic_only:blocked` with explicit diagnostics. |
| ISFC-033 | Done | Preserve `source_applied_section_refs`, `source_surface_zone_refs`, and `source_edge_network_refs`. | result dataclasses/tests | Ready loop row can be traced back to source/evaluation contracts. |
| ISFC-034 | Done | Unit-test T intersection closed loop assembly from Applied Section side-slope boundaries. | `tests/contracts/v1/` | Ready loop count is nonzero and loop has `generation=surface_candidate:ready`. |

Implementation note:

- when the source edge graph is degenerate or open, Applied Section strip completion can replace boundary refs with `applied-section-boundary:*` refs.
- completed loop rows preserve source Applied Section refs, edge-network refs, and surface-zone refs.
- this path alone does not satisfy visual perimeter coverage; it must be paired with `IntersectionSlopeFaceBoundaryResult` strip output.

## Phase 5 - Dedicated Surface Generation

Status: Partial

Goal:

- generate the visible intersection perimeter Slope Face surface from ready loop rows.

Tasks:

| Task id | Status | Work item | Primary files | Acceptance criteria |
| --- | --- | --- | --- | --- |
| ISFC-040 | Partial | Feed completed ready loops into existing dedicated surface builder only when they carry an intersection-owned perimeter source. | `cmd_build_corridor.py` | Ordinary Applied Section side-slope loops are not promoted to a dedicated Intersection Slope Face Surface. |
| ISFC-041 | Done | Ensure ordinary `Slope Face Surface` suppression does not remove the dedicated surface footprint. | `cmd_build_corridor.py`, surface geometry service | Ordinary surface and dedicated surface remain separate and non-overlapping. |
| ISFC-042 | Done | Add quality metadata for generated perimeter loops. | `cmd_build_corridor.py` | Preview records ready loop count, triangle count, source loop refs, and rejected loop refs. |
| ISFC-043 | Done | Confirm Visibility and Results rows update automatically. | UI helpers/tests | Results row remains `missing` and Visibility remains unavailable when no dedicated perimeter loop exists. |
| ISFC-044 | Done | Suppress visible strip triangles from `IntersectionSlopeFaceBoundaryResult` pavement tie-in rows. | `cmd_build_corridor.py` | T preset smoke confirms no dedicated preview is created from pavement tie-in boundary rows. |
| ISFC-045 | Done | Create true dedicated perimeter strips from curb-return exterior arcs to Applied Section side-slope/daylight points. | `cmd_build_corridor.py`, tests | FreeCADCmd T preset smoke requires curb-return perimeter strips and rejects pavement tie-in visible strips. |

Implementation note:

- dedicated `V1CorridorIntersectionSlopeFaceSurfacePreview` is no longer created from ordinary Applied Section side-slope loops or pavement tie-in boundary strips.
- `IntersectionSlopeFaceBoundaryResult` currently preserves primary/secondary left/right pavement tie-in rows as metadata, but those rows are not valid visible slope-face strip sources because their inner edge is inside the curb-return/pavement patch.
- previous partial implementation selected one best pavement tie-in segment, then four pavement tie-in segments; both produced visually misleading internal strips. Those visible strip triangles are now suppressed.
- dedicated preview now creates visible `curb_return_to_slope_face_perimeter` strips from `IntersectionBoundarySegmentResult` curb-return arcs to source Applied Section side-slope/daylight points.
- skinny fan quality is counted but no longer prevents preview generation when the loop is otherwise valid.

## Phase 6 - Regression And Manual QA

Status: Partial

Goal:

- prove the actual user-visible gap is closed, not merely diagnosed.

Tasks:

| Task id | Status | Work item | Primary files | Acceptance criteria |
| --- | --- | --- | --- | --- |
| ISFC-050 | Done | Update FreeCADCmd T preset smoke to require the real preset pipeline to create the dedicated surface directly. | `tests/regression/smoke_intersection_t_slope_face_surface.py` | Smoke no longer injects a synthetic ready-loop contract. |
| ISFC-051 | Done | Add contract tests for degenerate edge fallback to Applied Section boundaries. | `tests/contracts/v1/` | Degenerate edge-network endpoints do not prevent ready loops when accepted Applied Section boundaries are available. |
| ISFC-052 | Done | Add manual QA checklist for perimeter fill around both curb returns. | `docsV1/V1_INTERSECTION_MANUAL_QA.md` | QA asks user to inspect ordinary/dedicated surface separation and curb-return side-slope tie-ins. |
| ISFC-053 | Done | Capture known limitation for non-T presets. | docs/tests | Cross, Skewed, and Y now have FreeCADCmd readiness smoke coverage; Roundabout, Urban Curb/Gutter, and Drainage-Sensitive Sag remain specialized follow-up scopes. |
| ISFC-054 | Done | Strengthen T preset smoke beyond object existence. | `tests/regression/smoke_intersection_t_slope_face_surface.py` | Smoke requires dedicated curb-return perimeter strips and confirms pavement tie-in boundary strips remain metadata-only. |
| ISFC-055 | Done | Add coverage-oriented smoke metrics. | regression tests | Smoke compares generated strip bbox/area against the intersection patch boundary vicinity. |

Implementation note:

- `tests/regression/smoke_intersection_t_slope_face_surface.py` no longer injects synthetic ready-loop rows.
- FreeCADCmd validates that the T preset creates a dedicated preview from curb-return perimeter strips while keeping pavement tie-in boundary rows metadata-only.
- FreeCADCmd now validates that the dedicated Intersection Slope Face Surface has measurable bbox/area coverage in the intersection patch vicinity, so tiny leftover triangle groups do not satisfy the smoke.
- `tests/regression/smoke_intersection_non_t_slope_face_readiness.py` validates Cross, Skewed, and Y starter presets through the same Build Parametric path and requires truthful Results-row readiness for their dedicated Intersection Slope Face Surface state.
- Roundabout, Urban Curb/Gutter, and Drainage-Sensitive Sag remain specialized follow-up scopes because they carry additional circulatory, curb/gutter, inlet, and sag-drainage intent beyond this slope-face readiness slice.

## Acceptance Criteria

The work is complete when:

- the default T intersection preset can create accepted source/result prerequisites without synthetic ready-loop injection
- `evaluate_slope_face_loops()` returns at least one `ready` loop for the T preset
- `V1CorridorIntersectionSlopeFaceSurfacePreview` is created by Build Parametric only when a dedicated curb-return-to-slope-face perimeter loop exists
- the generated dedicated surface fills the visible perimeter gap near curb returns and side-slope tie-ins
- ordinary `Slope Face Surface` remains separate and does not fill the central pavement footprint
- Results and Visibility tabs reflect actual object existence and readiness
- FreeCADCmd smoke passes under FreeCAD 1.1.1

## Open Questions

- Should Applied Section side-slope boundary extraction happen inside `IntersectionEvaluationService`, or should it become a small dedicated boundary service consumed by intersections and future ramps?
- Should ready-loop triangulation remain center-fan for the first slice, or move directly to constrained strip triangulation once the loop boundary is complete?
- Should `IntersectionSurfaceZoneRow` store boundary candidate refs directly, or should a separate `IntersectionSlopeFaceBoundaryResult` become the formal handoff contract?

## Current Follow-Up

- Verify in FreeCAD GUI that `curb_return_to_slope_face_perimeter` strips sit outside the curb-return arc and not inside the central pavement patch.
- Add specialized Roundabout, Urban Curb/Gutter, and Drainage-Sensitive Sag regression coverage after their source contracts are accepted for slope-face completion semantics.

The immediate implementation generates source-traceable curb-return perimeter strips for the T preset. Manual FreeCAD review should confirm the strips occupy the actual exterior side-slope gap.
