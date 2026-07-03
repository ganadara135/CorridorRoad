# V1 Intersection Slope Face Surface Ready Loop Plan

Date: 2026-06-28  
Status: Active  
Scope: restore dedicated `Intersection Slope Face Surface` generation by producing source-traceable, closed, ready slope-face loops

## Purpose

This document defines the implementation plan for the currently missing `Intersection Slope Face Surface` preview.

The immediate symptom is:

- `V1CorridorIntersectionSlopeFaceSurfacePreview` is not created.
- Build Parametric shows `Intersection Slope Face Surface` as missing or disabled.
- Visible yellow or blue linework is diagnostic or contract review geometry, not the dedicated surface.

The root cause is:

- `IntersectionSlopeFaceLoopResult` does not produce any `ready` closed loop rows.
- The surface builder intentionally triangulates `ready` loop rows only.
- Warning or error loop rows remain diagnostic and must not create hidden repair triangles.

## Core Rule

The fix must make the loop contract correct.

Do not solve this by appending visual patch triangles after the fact.

`Intersection Slope Face Surface` must be generated from accepted intersection source/result contracts:

- `IntersectionModel`
- topology result
- edge network result
- surface zone result
- Applied Section side-slope/daylight result context where needed
- shared breakline and boundary contracts

Generated mesh, preview objects, or ordinary `Slope Face Surface` triangles must not become source truth.

## Current Behavior

Build Parametric currently follows this path:

1. Evaluate topology.
2. Evaluate edge network.
3. Evaluate surface zones.
4. Evaluate slope-face loops with `evaluate_slope_face_loops()`.
5. Build `V1CorridorIntersectionSlopeFaceSurfacePreview` from ready loops only.

The dedicated surface is skipped when:

- no slope-face zones exist
- slope-face zones have missing `inner_edge_refs`
- slope-face zones have missing `outer_edge_refs`
- slope-face zones have missing `tie_edge_refs`
- boundary edge refs cannot be resolved
- loop points are too few
- loop points are open in XY
- loop points self-cross
- source lineage is not accepted

This is correct as a safety gate, but the upstream loop construction is not yet complete enough for the T intersection preset case.

## Design Direction

The next implementation must convert intersection slope ownership into closed loop contracts before triangulation.

The loop evaluator should not merely concatenate edge start/end points in the existing ref order.

It should build a small edge graph from boundary candidates, order the edges into closed rings, validate the ring, and then pass only accepted rings to the surface builder.

## Phase 1 - Instrument Current Failure

Status: Planned

Goal:

- make the current failure explainable in Build Parametric without requiring code inspection.

Tasks:

| Task id | Status | Work item | Primary files | Acceptance criteria |
| --- | --- | --- | --- | --- |
| ISFS-001 | Done | Add loop readiness summary to Intersection and Results notes. | `cmd_build_corridor.py`, `intersection_evaluation_service.py` | Results row explains `ready=0`, warning/error counts, and top loop blocking reasons. |
| ISFS-002 | Done | Expose per-loop blocking diagnostics in the Intersections tab. | `cmd_build_corridor.py` | Double-click or row notes show missing inner/outer/tie refs, open loop, unresolved refs, and self-crossing state. |
| ISFS-003 | Done | Add focused tests for missing preview when ready loops are zero. | `tests/contracts/v1/` | Test proves the missing surface is a deliberate contract gate, not a UI visibility bug. |

Phase 1 progress note:

- `ConsumedIntersectionContractSummary` now includes Slope Face loop readiness counts.
- The summary includes compact blocking reason tokens such as `slope_face_loop_open_xy`, `slope_face_loop_tie_edge_refs_missing`, `source_warning`, and `surface_zone_warning`.
- Slope Face loop row diagnostics are now also carried into consumed contract diagnostics so the Results row can explain why a dedicated preview was not generated.
- Intersections tab Slope Face loop rows now include `closed_xy`, `self_crossing`, and `blocking=` notes, and their source diagnostics include loop diagnostics as well as source diagnostics.
- Focused tests now cover the zero-ready-loop gate: no `V1CorridorIntersectionSlopeFaceSurfacePreview` is created, and stale preview objects are removed.

## Phase 2 - Build Ordered Boundary Rings

Status: Planned

Goal:

- replace raw edge-ref concatenation with deterministic closed-ring assembly.

Tasks:

| Task id | Status | Work item | Primary files | Acceptance criteria |
| --- | --- | --- | --- | --- |
| ISFS-004 | Done | Add an edge endpoint graph helper for slope-face loop candidates. | `intersection_evaluation_service.py` | Boundary edge refs are converted into nodes and directed/undirected candidate segments with source refs. |
| ISFS-005 | Done | Order boundary segments into one or more rings. | `intersection_evaluation_service.py` | Connected boundary edges form a closed `loop_points_xyz` sequence even when refs are not already in traversal order. |
| ISFS-006 | Done | Detect and report dangling endpoints. | `intersection_evaluation_service.py` | Missing closure reports the exact endpoint and source edge refs that prevent a ready loop. |
| ISFS-007 | Done | Keep deterministic tie-breaking. | `intersection_evaluation_service.py` | Same source inputs always produce the same loop order and diagnostics. |

Phase 2 progress note:

- Added `_slope_face_loop_endpoint_graph()` as the graph foundation for ordered Slope Face loop assembly.
- The helper converts boundary edge refs into endpoint nodes, undirected adjacency, segment rows, unresolved edge refs, degenerate edge refs, dangling endpoint nodes, and branch nodes.
- Added focused contract coverage for closed-loop edges plus a dangling diagnostic tail and unresolved edge ref.
- Added `_slope_face_loop_ordered_rings_from_graph()` to convert unordered connected boundary segments into deterministic closed ring point sequences.
- Added focused coverage that unordered rectangle edges produce one closed ring with the first point repeated as the last point.
- Endpoint graph rows now expose dangling endpoint coordinates and incident edge refs.
- `evaluate_slope_face_loops()` now emits `warning:slope_face_loop_dangling_endpoint:<edge_refs>:xyz=<x,y,z>` diagnostics so open loop failures point back to the source edge side that blocks closure.
- Added evaluator coverage that a missing tie side reports dangling endpoint diagnostics and keeps ready loop count at zero.
- Added canonical ring point ordering so closed loop sequences start at the smallest endpoint key and choose the deterministic direction.
- Added coverage that reversed edge directions and different input order still produce the same closed ring point sequence.

## Phase 3 - Complete Slope-Face Zone Boundary Inputs

Status: Planned

Goal:

- ensure each intersection slope-face zone has enough meaningful edge refs to form a ring.

Tasks:

| Task id | Status | Work item | Primary files | Acceptance criteria |
| --- | --- | --- | --- | --- |
| ISFS-008 | Done | Audit how daylight, pavement, curb-return, and side-slope edge refs are assigned to slope zones. | `intersection_evaluation_service.py` | T preset slope zones list all required inner, outer, and tie edges or report precise source gaps. |
| ISFS-009 | Done | Derive missing tie edges from accepted curb-return or control-area boundary contracts only when source lineage is explicit. | `intersection_evaluation_service.py`, result models if needed | Tie edges are source-traceable and are not guessed from preview mesh geometry. |
| ISFS-010 | Done | Add Applied Section side-slope boundary refs where the intersection needs to tie into ordinary side-slope output. | Applied Section/result bridge, `intersection_evaluation_service.py` | Loop rows can consume Applied Section side-slope boundary refs as result context while preserving source ownership. |
| ISFS-011 | Done | Separate warning-only diagnostic zones from accepted surface-generation zones. | `intersection_surface_zone.py`, `intersection_slope_face_loop.py` | Contract review clearly distinguishes review-only candidates from surface-generating loops. |

Phase 3 progress note:

- Slope surface-zone notes now include `slope_zone_boundary_audit=inner:<n> outer:<n> tie:<n> boundary:<n>`.
- The audit note also records `inner_refs`, `outer_refs`, and `tie_refs`, or marks them as missing.
- Missing pavement or curb-return tie context remains warning-only source/result diagnostics; no generated mesh or preview geometry is used as source.
- Curb-return edge-network rows now preserve source corner `control_area_ref`.
- When direct leg-ref matching cannot find curb-return tie edges, surface-zone evaluation can use accepted curb-return edges from the same control area as a source-traceable fallback.
- Added focused coverage proving the control-area fallback fills tie refs without relying on preview or mesh geometry.
- Slope Face loop evaluation can now consume Applied Section side-slope result context and records matching `source_applied_section_refs` on loop rows.
- Build Parametric passes the document Applied Section Set into slope-face loop evaluation for contract review, preview metadata, and daylight suppression.
- Intersections tab source refs include the Applied Section side-slope refs, so the loop row can show which evaluated section context participated in the tie-in.
- Open loop candidates no longer run self-crossing validation on raw fallback point concatenation; they remain warning diagnostics until a closed ring exists.
- Surface-zone and Slope Face loop rows now carry `surface_generation_role` and `surface_generation_status`.
- Warning-only zones and loops are marked `diagnostic_only:blocked`; only `surface_candidate:ready` loop rows may generate the dedicated `Intersection Slope Face Surface`.
- Build Parametric Intersections row notes now show `generation=<role>:<status>`, and the surface preview stores `SurfaceGenerationReadyLoopCount`.
- The surface builder now triangulates from the explicit surface-generation gate instead of relying only on row `status=ready`.

## Phase 4 - Surface Triangulation From Ready Loops

Status: Planned

Goal:

- make the dedicated surface useful after ready loops exist.

Tasks:

| Task id | Status | Work item | Primary files | Acceptance criteria |
| --- | --- | --- | --- | --- |
| ISFS-012 | Done | Keep first implementation as loop fan triangulation only for valid simple rings. | `cmd_build_corridor.py` | Ready loops generate visible triangles with source loop refs and no hidden repair geometry. |
| ISFS-013 | Done | Reject skinny or degenerate ring fan output with diagnostics. | `cmd_build_corridor.py`, TIN quality helpers | Surface quality rows explain degenerate rings instead of producing misleading geometry. |
| ISFS-014 | Done | Confirm ordinary `Slope Face Surface` clipping/suppression uses the dedicated ready-loop footprint only when available. | `cmd_build_corridor.py` | No ordinary side-slope triangles are removed by warning-only intersection loops. |

Phase 4 progress note:

- The dedicated `Intersection Slope Face Surface` builder now consumes only loops that pass both the surface-generation gate and simple-ring checks.
- A loop must be `surface_candidate:ready`, `status=ready`, `closed_xy=True`, `self_crossing=False`, and have at least three unique fan boundary points before triangulation.
- Preview metadata now distinguishes contract `ReadyLoopCount` from `SurfaceGenerationReadyLoopCount`.
- Generated preview triangles keep the source loop id in triangle notes and `SourceLoopRefs`.
- Invalid surface candidates are skipped and reported through readiness blocking tokens such as `surface_generation_open_xy`.
- Fan triangulation now evaluates triangle area and quality before writing triangles.
- Degenerate or skinny loop fans are rejected as whole loops, so partial misleading fan surfaces are not emitted.
- Surface quality rows now record `generated_loop_count`, `rejected_degenerate_loop_count`, `rejected_skinny_loop_count`, `fan_min_quality`, and `rejected_loop_refs`.
- Ordinary `Slope Face Surface` suppression now has focused coverage proving it only removes daylight triangles when a generated dedicated ready-loop reference surface has triangles.
- Quality-rejected or warning-only reference surfaces with no triangles leave ordinary side-slope triangles untouched and record `intersection_slope_loop_suppress_status=skipped`.

## Phase 5 - Review UX

Status: Planned

Goal:

- let users understand whether the missing surface is source data, topology, edge, or ring-order related.

Tasks:

| Task id | Status | Work item | Primary files | Acceptance criteria |
| --- | --- | --- | --- | --- |
| ISFS-015 | Done | Add a concise recommended action for missing `Intersection Slope Face Surface`. | `cmd_build_corridor.py` | User sees whether to rebuild sources, review edge families, review curb-return policy, or inspect side-slope tie-in. |
| ISFS-016 | Done | Add optional visual debug for closed-loop candidates. | `cmd_build_corridor.py` | Ready loops, open loops, and dangling endpoints can be distinguished visually. |
| ISFS-017 | Done | Keep the Visibility checkbox disabled only when the preview object is truly absent. | `cmd_build_corridor.py` | Disabled state matches object existence and notes explain why it is absent. |

Phase 5 progress note:

- Slope Face loop readiness summaries now include a concise `action=...` recommendation when the dedicated surface is blocked.
- Build Parametric stores `IntersectionSlopeFaceSurfaceRecommendedAction` on the intersection preview.
- Intersection review summary includes `intersection_slope_face_action=...` so Results and Guided Review notes can expose the next user action.
- Recommendations are derived from blocking tokens such as missing tie refs, open/dangling loops, self-crossing loops, low point count, blocked surface generation, and source lineage warnings.
- Intersections tab double-click highlights now color Slope Face loop rows by debug state.
- Ready closed loops use green, open loops use orange, dangling endpoints use red, self-crossing loops use magenta, and source-warning closed loops use yellow.
- Highlight objects record `HighlightDebugStatus`, `HighlightDebugHint`, and `HighlightColor` for review/debug visibility.
- `Intersection Slope Face Surface` now records a dedicated missing/error preview diagnostic when no generated triangles exist.
- Visibility checkboxes stay disabled only when the target preview object is absent, and their tooltip explains the missing status plus recommended action.
- Results rows for absent `Intersection Slope Face Surface` reuse the same diagnostic/action text instead of showing only a generic missing state.

## Phase 6 - Tests And Manual QA

Status: Planned

Goal:

- prevent regressions in both intersection-owned slope loops and ordinary road slope face output.

Tasks:

| Task id | Status | Work item | Primary files | Acceptance criteria |
| --- | --- | --- | --- | --- |
| ISFS-018 | Done | Add unit tests for ordered ring assembly. | `tests/contracts/v1/` | Unordered boundary edges produce a closed ring. |
| ISFS-019 | Done | Add unit tests for dangling/open loop diagnostics. | `tests/contracts/v1/` | Missing tie edge blocks ready status with clear diagnostics. |
| ISFS-020 | Done | Add FreeCADCmd smoke validation for T intersection preset. | `tests/regression/` | Build creates `V1CorridorIntersectionSlopeFaceSurfacePreview` when source prerequisites are complete. |
| ISFS-021 | Done | Update manual QA. | `docsV1/V1_INTERSECTION_MANUAL_QA.md` | QA includes ready-loop count, preview object existence, and visual checks around curb returns and side-slope tie-ins. |

## Acceptance Criteria

Phase 6 progress note:

- Ordered ring helper tests cover unordered edge refs and deterministic tie breaking.
- `evaluate_slope_face_loops()` now has a contract test proving unordered/reversed boundary edges still produce a ready, closed, non-self-crossing surface candidate loop.
- Dangling/open loop diagnostics now have contract coverage for partial tie-edge loops and explicit missing tie-edge refs.
- Missing/open tie conditions block ready status, keep the loop `diagnostic_only:blocked`, and preserve `slope_face_loop_dangling_endpoint`, `slope_face_loop_open_xy`, or `slope_face_loop_tie_edge_refs_missing` diagnostics.
- `tests/regression/smoke_intersection_t_slope_face_surface.py` validates the T intersection preset context under FreeCADCmd.
- The smoke marks preset source prerequisites as reviewed, then verifies that a complete accepted Slope Face ready-loop contract creates `V1CorridorIntersectionSlopeFaceSurfacePreview` with triangles, ready-loop refs, Results-row readiness, and enabled Visibility notes.
- The current default T preset edge network still needs a future source-coordinate enhancement before it can directly emit ready slope-face loops without the smoke's explicit complete ready-loop contract.
- Manual QA now asks reviewers to check ready-loop count, `generation=surface_candidate:ready`, Results-row status/action, Visibility checkbox enabled state, preview tree location, source loop refs, and curb-return/side-slope tie-in visual behavior.

The work is complete when:

- Build Parametric creates `V1CorridorIntersectionSlopeFaceSurfacePreview` for a valid T intersection preset.
- The Results row for `Intersection Slope Face Surface` is `ready` when ready loops produce triangles.
- When it is missing, the Results or Intersections tab explains the exact blocking reason.
- Ordinary `Slope Face Surface` remains generated from Applied Section side-slope/daylight context.
- No hidden repair triangles are appended from mesh or preview geometry.
- `FreeCADCmd.exe` validation passes under FreeCAD 1.1.1.

## Non-goals

- Do not make generated preview geometry editable source.
- Do not infer missing intersection intent from old mesh fragments.
- Do not reintroduce the removed visible boundary strip patches.
- Do not merge ordinary `Slope Face Surface` and dedicated `Intersection Slope Face Surface` into one untraceable output.
- Do not treat warning-only loop candidates as accepted surface geometry.

## Implementation Order

Recommended order:

1. Phase 1: expose the current ready-loop blocking reason.
2. Phase 2: implement ordered boundary ring assembly.
3. Phase 3: complete missing slope-zone boundary refs from accepted source/result contracts.
4. Phase 4: triangulate only validated ready loops.
5. Phase 5: improve review UX and visual diagnostics.
6. Phase 6: add tests and manual QA.

## Current Risk

The highest risk is accidentally fixing the symptom by using ordinary surface triangles or preview meshes as source.

The safer path is slower but cleaner:

- make source/result contracts complete
- make loops closed and accepted
- then generate the dedicated preview surface
