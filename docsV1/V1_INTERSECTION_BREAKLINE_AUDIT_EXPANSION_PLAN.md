# V1 Corridor-Wide Breakline Audit Expansion Plan

Date: 2026-06-25
Status: Implemented with follow-up scope
Scope: Shared Breakline Audit coverage for normal roads and Intersection output quality

## Purpose

This plan records the breakline audit expansion work for v1 corridor and Intersection results.

The goal is to move normal road and Intersection quality checks from visual touch-up toward explicit shared boundary contracts.

Breakline Audit should prove that adjacent result/output objects consume the same accepted `SharedBreaklineResult` rows before those objects are used by review, quantities, exchange, or Watertight Solids.

Intersection remains the first high-risk implementation target because it exposes the most visible boundary failures. However, the same audit contract must also cover ordinary corridor surfaces such as lane, shoulder, side slope, daylight, ditch, subgrade, and Region transitions.

## Core Rule

Corridor and Intersection contact edges must be owned by shared result contracts, not by copied mesh coordinates.

Generated TIN edges may visualize the result, but they are not the source of boundary ownership.

Every audited contact should answer:

- which source/result owns the breakline
- which surfaces or outputs consume it
- whether each consumer records the normalized constraint segment
- whether the mesh display follows the consumed constraint closely enough
- what action the user should take if it does not

## Current Baseline

Initial baseline:

- `SharedBreaklineResult`, `SharedBreaklineRow`, and `SharedBreaklinePointRow`
- first Intersection shared breakline rows:
  - `patch_to_design`
  - `patch_to_slope_face`
- surface-level `shared_breakline_constraint_segment_rows` metadata
- Build Parametric `Breakline Audit` tab
- Recommended Action column
- 3D `Shared Breakline Highlight`
- mesh fallback checks for edge, edge-chain, internal TIN edge, and polyline coverage
- corridor-wide ordinary-road shared breakline rows from Applied Section subassembly link endpoints
- Region start/end shared breakline rows from Applied Section Region boundaries
- normal-road Design and Slope Face surfaces consuming corridor-wide and Region breakline constraint metadata

Implemented expansion:

- ordinary corridor lane/shoulder/side-slope/daylight contacts are audited as shared breaklines where Applied Section source links exist
- Region start/end, Region transition, and assembly-change boundaries are audited
- normal-road gutter/ditch drainage handoffs are audited against `drainage_surface` constraints
- Intersection patch, curb-return, shoulder, slope-face, drainage, and control-area contacts use first-class shared breakline roles
- Breakline Audit exposes role/material grouping, Recommended Action, 3D highlighting, mesh adherence, and solid-readiness graph metadata
- Watertight Solid boundary trace rows consume shared breakline source lineage

Remaining follow-up scope:

- a future dedicated Shoulder Surface can consume existing shoulder shared breaklines without changing the source contract
- subgrade and material-layer boundary audit remains a later Digital Twin/material body phase
- full production Watertight Solid builders should continue consuming shared breakline closure instead of preview mesh inference

## Scope Decision

The original Intersection-first plan was not enough by itself to guarantee that ordinary road breakline issues were solved.

The shared model and audit machinery are reusable, but normal roads need their own source roles, consumers, and acceptance tests.

This document therefore treats Intersection as one implementation slice of a corridor-wide breakline audit system.

General-road audit has been implemented explicitly for:

- lane-to-lane boundaries
- lane-to-shoulder boundaries
- shoulder-to-side-slope boundaries
- side-slope-to-daylight or terrain handoff
- ditch/gutter handoff
- Region start/end and Region transition boundaries
- subgrade and material-layer boundaries in a later material-body phase
- future Watertight Solid profile loops using the shared breakline graph and boundary trace rows

Scope conclusion:

- Running only Intersection-only phases would not guarantee normal-road breakline audit completeness.
- The shared result model is common, but normal roads still need their own `CR-BLA-*` tasks and acceptance tests.
- Phase 2 and Phase 3 are the ordinary-road foundation phases.
- Intersection phases reuse the same common audit model instead of introducing a separate Intersection-only mechanism.

## Status Legend

| Status | Meaning |
| --- | --- |
| Planned | Not implemented. |
| Started | First slice exists but full acceptance is incomplete. |
| Done | Implemented and covered by focused tests or manual QA. |
| Blocked | Requires a prior task. |

## Phase 1 - Existing Patch Contact Hardening

Status: Done

Goal:

- make the current `patch_to_design` and `patch_to_slope_face` checks reliable and actionable.

Tasks:

| Task id | Status | Work item | Acceptance criteria |
| --- | --- | --- | --- |
| INT-BLA-001 | Done | Add normalized constraint segment metadata to consuming surfaces. | Audit can prove consumption through `shared_breakline_constraint_segment_rows`. |
| INT-BLA-002 | Done | Keep mesh edge checks as fallback diagnostics. | Audit still reports geometry mismatch when a consumer claims only boundary refs without constraint rows. |
| INT-BLA-003 | Done | Split `patch_to_design` into per-contact roles. | Primary alignment contacts become `patch_to_design_pavement_tie_in`; secondary/stem contacts become `patch_to_design_stem_tie_in`; broad `patch_to_design` remains only as a fallback when boundary segment source rows are unavailable. |
| INT-BLA-004 | Done | Add per-breakline audit details in panel rows. | Breakline Audit now expands surface rows with role-level display rows and selected role filters for 3D highlight. Exact failed breakline ids remain in audit notes. |
| INT-BLA-005 | Done | Add corrective action by role. | Recommended Action maps patch, curb-return, shoulder, drainage, Region, control-area, and ordinary road role notes to source/rebuild guidance. |

Implementation notes:

- `patch_to_design` should stop representing all design contacts as one broad row.
- `patch_to_slope_face` should remain a shared contract between Intersection Surface and Slope Face Surface, but Intersection Surface generation should consume it before triangulation, not only after triangulation.
- The first role-level panel slice keeps surface rows and adds indented role rows underneath each surface row.
- T Intersection focused validation now reports `patch_to_design_pavement_tie_in=2` and `patch_to_design_stem_tie_in=2` with zero geometry and mesh mismatch.

## Phase 2 - General Road Surface Breaklines

Status: Done

Goal:

- apply Breakline Audit to ordinary corridor surfaces before and outside intersection-specific logic.

Breakline roles:

- `lane_to_lane`
- `lane_to_shoulder`
- `shoulder_to_side_slope`
- `side_slope_to_daylight`
- `ditch_handoff`
- `gutter_handoff`
- `subgrade_layer_boundary`
- `material_shape_boundary`

Tasks:

| Task id | Status | Work item | Acceptance criteria |
| --- | --- | --- | --- |
| CR-BLA-010 | Done | Generate shared breaklines from Applied Section surface-role links. | Lane/design, slope-face, and drainage-role endpoint rows are created by station span. |
| CR-BLA-011 | Done | Attach constraint segment rows to normal road Design and Slope Face surfaces. | Design, Slope Face, and Drainage preview TINs record consumed breakline refs, surface-relevant consumed counts, and `shared_breakline_constraint_segment_rows`. |
| CR-BLA-012 | Done | Add general-road Breakline Audit rows. | General-road rows appear through the existing surface-level Breakline Audit metadata; Design, Slope Face, and Drainage builds preserve consumed breaklines as TIN constraint edges before audit. |
| CR-BLA-013 | Done | Add 3D highlight for corridor breakline roles. | User can isolate lane/shoulder/side-slope/daylight and corridor drainage handoff breaklines in the model. |
| CR-BLA-014 | Done | Add contract tests for straight and curved ordinary roads. | Normal road rebuild reports zero contract mismatch where source links exist. |

Implementation notes:

- Source ownership should come from Applied Sections and Assembly/Subassembly surface-role rows.
- Do not infer ordinary road breaklines from generated meshes.
- The same `SharedBreaklineResult` model should be used; do not create an Intersection-only parallel schema.
- Design and Slope Face preview counts use the surface-relevant breakline denominator instead of the combined corridor-wide total.
- Corridor role highlight now assigns explicit colors for `lane_to_lane`, `lane_to_shoulder`, `shoulder_to_side_slope`, `side_slope_to_daylight`, and corridor gutter/ditch handoff roles using the same preview `SharedBreaklineSegmentRows` contract as Intersection highlight.
- Straight and curved ordinary-road contract tests now verify Applied Section source links produce Design and Slope Face shared breaklines with zero geometry and mesh mismatch after constraint-edge preservation.

## Phase 3 - Region Transition Breaklines

Status: Done

Goal:

- audit ordinary road Region start/end and Region-to-Region transition contacts.

Breakline roles:

- `region_start_boundary`
- `region_end_boundary`
- `region_to_region_transition`
- `assembly_change_boundary`
- `surface_transition_boundary`

Tasks:

| Task id | Status | Work item | Acceptance criteria |
| --- | --- | --- | --- |
| CR-BLA-020 | Done | Create Region boundary shared breaklines from RegionModel and Applied Sections. | Region start/end rows are created from Applied Section surface-role endpoints. |
| CR-BLA-021 | Done | Audit Region transition surfaces. | Design and Slope Face preview metadata includes Region start/end constraint rows and audits with zero mismatch in focused tests. |
| CR-BLA-022 | Done | Add Recommended Action for Region mismatch. | Breakline Audit uses `region-transition`, `region_start_boundary`, `region_end_boundary`, and `assembly_change_boundary` notes to recommend reviewing Region spans before Build Parametric. |
| CR-BLA-023 | Done | Add QA for Assembly changes across Region boundaries. | Changing Assembly at a Region boundary produces traceable `assembly_change_boundary` breaklines. |

Implementation notes:

- This phase covers normal-road Region transitions.
- Intersection control-area handoff remains in the Intersection-specific phase below.
- Region start/end breaklines are generated from Applied Section surface-role endpoints and consumed by Design and Slope Face surfaces as normalized constraint rows.
- Focused Region transition tests verify zero geometry and mesh mismatch after constraint-edge preservation.
- Assembly changes across Region boundaries now create `assembly_change_boundary` rows for each available surface role. Rows preserve previous/current Region refs, previous/current Assembly refs, boundary station, consumer surface, and source Applied Section refs.
- Breakline Audit maps `assembly_change_boundary` notes to Region-span review guidance before rebuilding Build Parametric.

## Phase 4 - Intersection Surface Constraint Generation

Status: Done

Goal:

- ensure Intersection Surface triangulation consumes shared breaklines as input constraints.

Tasks:

| Task id | Status | Work item | Acceptance criteria |
| --- | --- | --- | --- |
| INT-BLA-010 | Done | Build shared breaklines before Intersection Surface triangulation. | Intersection shared breakline result is built inside the patch TIN builder after accepted patch boundary creation. |
| INT-BLA-011 | Done | Insert shared breakline vertices into patch triangulation input. | Missing breakline endpoint vertices are inserted into the Intersection Surface TIN with source refs to the shared breakline point/source rows. |
| INT-BLA-012 | Done | Preserve shared breakline segments as constraint edges. | Support triangles make missing shared breakline segments appear as actual TIN edges and record constraint counts in quality rows. |
| INT-BLA-013 | Done | Report constraint mesh adherence. | Breakline Audit tracks contract geometry and actual mesh adherence separately with `mesh` counts and `mesh_drift` notes. |
| INT-BLA-014 | Done | Add tests for T preset side-slope contact. | Representative T-intersection preview and preset-source e2e tests assert accepted shared contracts rebuild with zero geometry and mesh mismatch on the Intersection Surface. |

Implementation notes:

- This is the main root-cause fix for recurring `patch-to-slope-face` mismatch.
- Do not solve this by increasing tolerance.
- Do not infer breaklines from generated mesh after the fact.
- First implementation slice preserves Intersection Surface shared breakline segments with support triangles and quality rows:
  - `shared_breakline_constraint_mode`
  - `shared_breakline_constraint_segment_count`
  - `shared_breakline_constraint_edge_count`
  - `shared_breakline_constraint_vertex_count`
- Focused endpoint-insertion tests verify missing shared breakline endpoint vertices preserve source point refs and shared breakline refs before support triangles are added.
- Second implementation slice separates contract readiness from actual mesh adherence:
  - audit dictionaries expose `mesh_match_count` and `mesh_mismatch_count`
  - preview objects expose `SharedBreaklineMeshMatchCount` and `SharedBreaklineMeshMismatchCount`
  - the Breakline Audit tab includes a `Mesh` column
  - contract-ready but mesh-drifted surfaces report `mesh_drift:*` notes and recommend constrained surface mesh rebuild
- Mesh edge direction is not treated as a breakline audit issue when the shared breakline contract matches; contract rows remain the authoritative direction source for downstream normal/solid checks.
- Third implementation slice applies shared breakline constraint-edge preservation to ordinary Design Surface and Slope Face Surface builds before metadata and audit are attached.
- Fourth implementation slice adds a representative T-intersection preview regression test that requires:
  - `SharedBreaklineAuditStatus = ready`
  - `SharedBreaklineGeometryMismatchCount = 0`
  - `SharedBreaklineMeshMismatchCount = 0`
  - Build Review notes include `shared_breakline=ready consumed=2/2` and `audit=ready geometry=2/2 mesh=2/2`
- Fifth implementation slice adds an end-to-end preset-source regression test for the actual `Intersection` panel Create/Build flow:
  - `create_intersection_preset_sources("T Intersection - Basic")`
  - `build_document_applied_section_set`
  - `create_corridor_intersection_surface_preview`
  - shared breakline audit ready with zero geometry, mesh, and reversed mismatch
- Patch-to-slope-face contact generation is now covered by representative T preset contract tests and the later curb-return, shoulder, drainage, and control-area rows.

## Phase 5 - Curb Return Breaklines

Status: Done

Goal:

- make curb-return boundaries first-class shared breaklines.

Breakline roles:

- `curb_return_inner`
- `curb_return_outer`
- `curb_return_to_pavement`
- `curb_return_to_shoulder`
- `curb_return_to_slope_face`

Tasks:

| Task id | Status | Work item | Acceptance criteria |
| --- | --- | --- | --- |
| INT-BLA-020 | Done | Create curb-return breakline rows from Intersection edge-network / surface-zone results. | Stable `curb_return_outer`, `curb_return_inner`, `curb_return_to_pavement`, `curb_return_to_shoulder`, and `curb_return_to_slope_face` rows are created from `IntersectionBoundarySegmentResult` curb-return chord points. |
| INT-BLA-021 | Done | Consume curb-return breaklines in curb-return surface generation. | Intersection Surface consumes curb-return breaklines as constraint edges; the shared contract remains reusable for a future dedicated Shoulder Surface. |
| INT-BLA-022 | Done | Audit curb-return contacts against pavement and shoulder. | Curb-return pavement and shoulder contacts audit against Intersection/Design Surface, and curb-return slope-face contacts audit against Intersection/Slope Face Surface. |
| INT-BLA-023 | Done | Add 3D highlight by curb-return role. | Shared Breakline Highlight can filter curb-return material and role rows with role-aware colors. |
| INT-BLA-024 | Done | Replace fan-like curb-return triangulation where needed. | Curb-return mesh follows ordered strip/core surface parts instead of center-fan-only triangles. |

Implementation notes:

- Curb-return breaklines should be derived from IntersectionModel/evaluation contracts, not from orange preview mesh cleanup.
- Arc sampling should be deterministic and stored as point rows.
- First implementation slice derives `curb_return_outer` shared breaklines from `IntersectionBoundarySegmentResult.segment_rows` where `segment_role = curb_return`.
- Second implementation slice derives `curb_return_inner` shared breaklines using the same deterministic inner offset used by curb-return blend triangulation.
- Third implementation slice derives `curb_return_to_pavement` contact rows from the start/end curb-return arc segments.
- Fourth implementation slice derives `curb_return_to_slope_face` contact rows from the same source-owned curb-return endpoint segments.
- Fifth implementation slice derives `curb_return_to_shoulder` contact rows from the same source-owned curb-return endpoint segments.
- Sixth implementation slice derives `patch_to_shoulder` and `shoulder_to_slope_face` rows from the explicit Intersection slope-face boundary result.
- Intersection Surface now consumes these curb-return and shoulder rows, so representative T intersection audit moves from `2/2` to `19/19` shared breaklines:
  - `patch_to_design`
  - `patch_to_slope_face`
  - `patch_to_shoulder`
  - two `curb_return_outer` rows
  - two `curb_return_inner` rows
  - four `curb_return_to_pavement` rows
  - four `curb_return_to_shoulder` rows
  - four `curb_return_to_slope_face` rows
- Design Surface also consumes the four `curb_return_to_pavement` rows as pavement-contact constraint edges and the four `curb_return_to_shoulder` rows as shoulder-role contact constraint edges.
- Design Surface also consumes `patch_to_shoulder` and `shoulder_to_slope_face` as explicit shoulder handoff rows.
- Slope Face Surface also consumes the four `curb_return_to_slope_face` rows and `shoulder_to_slope_face` as slope-contact constraint edges.
- A future dedicated Shoulder Surface can consume the same `curb_return_to_shoulder` role without changing the source contract.
- Focused curb-return triangulation tests verify structured strip output contains `curb_return_blend` and `curb_return_core` parts, preserves arc segment counts, and does not emit `ordered_fan_fallback` triangles for valid curb-return arcs.

## Phase 6 - Intersection Shoulder Contact Breaklines

Status: Done

Goal:

- audit contacts between Intersection Surface and Shoulder Surface independently from pavement and side slope.

Breakline roles:

- `patch_to_shoulder`
- `shoulder_to_slope_face`
- `curb_return_to_shoulder`

Tasks:

| Task id | Status | Work item | Acceptance criteria |
| --- | --- | --- | --- |
| INT-BLA-030 | Done | Identify shoulder surface-role contacts in Applied Sections. | `patch_to_shoulder` and `shoulder_to_slope_face` are derived from the explicit Intersection slope-face boundary result. |
| INT-BLA-031 | Done | Add shoulder consumer refs to surfaces. | `patch_to_shoulder` is consumed by Intersection/Design Surface; `shoulder_to_slope_face` is consumed by Design/Slope Face Surface. |
| INT-BLA-032 | Done | Add audit grouping by material/surface role. | Material/role summaries on preview objects expose shoulder rows in Breakline Audit and feed role/material highlight filters. |

Implementation notes:

- Shoulder contacts remain shared breakline rows, not a dedicated Shoulder Surface source model.
- `curb_return_to_shoulder` rows are generated from curb-return endpoint contacts and remain reusable by a future Shoulder Surface.
- Focused tests verify `patch_to_shoulder`, `shoulder_to_slope_face`, and `curb_return_to_shoulder` consumer refs, audit grouping, recommended actions, and 3D highlight filters.

## Phase 7 - Drainage, Gutter, and Ditch Handoff Breaklines

Status: Done

Goal:

- connect ordinary corridor and Intersection grading to Drainage intent through explicit handoff edges.

Breakline roles:

- `intersection_gutter_handoff`
- `intersection_ditch_handoff`
- `corridor_gutter_handoff`
- `corridor_ditch_handoff`
- `low_point_flow_split`
- `drainage_capture_edge`

Tasks:

| Task id | Status | Work item | Acceptance criteria |
| --- | --- | --- | --- |
| INT-BLA-040 | Done | Create drainage handoff breaklines from DrainageModel and Intersection grading context. | `IntersectionDrainageHintResult` rows map to `intersection_gutter_handoff`, `low_point_flow_split`, or `intersection_ditch_handoff` shared breakline rows using source-owned intersection boundary rows. |
| CR-BLA-040 | Done | Create normal-road ditch/gutter handoff breaklines from Applied Sections and DrainageModel. | Applied Section `drainage_surface` gutter/ditch links map to `corridor_gutter_handoff` and `corridor_ditch_handoff` shared breakline rows. |
| INT-BLA-041 | Done | Audit gutter/ditch contact against Intersection Surface. | Intersection drainage handoff rows have `intersection_surface` and `drainage_surface` consumers; representative T preset audit reports these rows in the shared breakline count. |
| CR-BLA-041 | Done | Audit gutter/ditch contact against ordinary corridor surfaces. | Gutter/ditch rows consume `drainage_surface` constraint metadata and audit with zero mismatch in focused tests. |
| INT-BLA-042 | Done | Add Recommended Action for missing drainage intent. | Intersection drainage handoff notes recommend reviewing Intersection Drainage source before rebuilding Intersection. |

Non-goal:

- Do not recreate old false `Drainage Flow Highlight` objects as source truth.

Implementation notes:

- Normal-road drainage handoff rows remain source-owned by Applied Section `drainage_surface` links and consume normalized `SharedBreaklineResult` constraint rows.
- Intersection drainage handoff rows preserve `IntersectionDrainageHintResult` and hint row refs before copying source-owned boundary geometry.
- Focused tests verify corridor gutter/ditch zero-mismatch audit, Intersection drainage hint lineage, role-aware Recommended Action, and T preset zero-mismatch regression.

## Phase 8 - Intersection Control-Area Boundary Breaklines

Status: Done

Goal:

- prove that Region spans and Intersection control areas hand off at the same station/span boundaries.

Breakline roles:

- `region_to_intersection_control`
- `region_transition_to_patch`
- `control_area_entry`
- `control_area_exit`

Tasks:

| Task id | Status | Work item | Acceptance criteria |
| --- | --- | --- | --- |
| INT-BLA-050 | Done | Add Region/Intersection boundary shared rows. | `control_area_entry` and `control_area_exit` rows are created from Applied Section surface-role endpoints and include alignment ref, station start/end, Region ref, and control-area ref. |
| INT-BLA-051 | Done | Audit Region surface transition contacts. | Build Parametric consumes the entry/exit rows on Intersection, Design, and Slope Face surfaces and reports geometry/mesh adherence through the existing Breakline Audit tab. |
| INT-BLA-052 | Done | Highlight Region/Intersection handoff. | The existing Shared Breakline Highlight can isolate `control_area_entry` and `control_area_exit` role rows in 3D. |

Implementation notes:

- Control-area boundary rows are generated from `AppliedSection.active_intersection_control_area_id` and Subassembly surface-role endpoints.
- Rows use `domain_kind=intersection_control_area`, `domain_ref=<control_area_id>`, and notes containing `region_to_intersection_control`.
- Recommended Action maps control-area mismatch notes to reviewing Intersection control areas and Region spans before rebuilding.
- Focused FreeCADCmd validation confirms the T Intersection preset consumes 33/33 Intersection shared rows with zero geometry and mesh mismatch after adding these rows.

## Phase 9 - Watertight Solid Boundary Loop Readiness

Status: Done

Goal:

- make shared breaklines usable as closed loop input for Watertight Solids.

Tasks:

| Task id | Status | Work item | Acceptance criteria |
| --- | --- | --- | --- |
| CR-BLA-060 | Done | Build breakline adjacency graph for ordinary corridor and Intersection contacts. | `shared_breakline_adjacency_graph` reports open ends, duplicate edges, reversed edges, and non-manifold junctions with focused contract tests. |
| CR-BLA-061 | Done | Add solid-readiness audit rows. | Breakline Audit preview metadata now exposes solid-readiness status, open ends, duplicate edges, reversed edges, non-manifold nodes, and review-note summaries without changing surface geometry audit status. |
| CR-BLA-062 | Done | Export source traceability for solid boundaries. | Build Parametric serializes `SharedBreaklineSolidBoundaryTraceRows`; Watertight Solid build collects them from preview objects and preserves them on `WatertightSolidOutputRow.boundary_trace_rows` and FreeCAD output objects. |

Implementation notes:

- The first graph slice is a pure result audit over `SharedBreaklineResult`; it does not infer topology from generated mesh.
- Closed loop rows report `shared_breakline_adjacency=closed`.
- Problem rows report `open_end_count`, `duplicate_edge`, `reversed_edge`, and `non_manifold_node_count` notes for later Watertight Solid review consumption.
- Build Parametric preview objects store `SharedBreaklineSolidReadinessStatus`, open/duplicate/reversed/non-manifold counts, and solid-readiness notes.
- Build Parametric preview objects also store `SharedBreaklineSolidBoundaryTraceRows` with breakline id, role, domain, alignment, station range, material role, source contract refs, consumer refs, and handoff target.
- Watertight Solid output rows and persisted `V1WatertightSolidOutput` objects preserve these boundary trace rows for exchange and downstream source lineage.

## Panel UX Plan

Breakline Audit now presents shared breakline status as role-level rows instead of surface-level totals only.

Current layout:

- top summary:
  - `No shared breakline issues`
  - or `Shared breakline issues found: N breakline(s)`
- role groups:
  - General Road
  - Region Transitions
  - Patch Contacts
  - Curb Return
  - Shoulder
  - Drainage Handoff
  - Region Handoff
  - Solid Readiness
- row columns:
  - `Role`
  - `Status`
  - `From`
  - `To`
  - `Contract`
  - `Mesh`
  - `Distance`
  - `Coverage`
  - `Recommended Action`
  - `Breakline Id`
  - `Notes`

Recommended actions:

| Condition | Recommended Action |
| --- | --- |
| Missing source contract | Edit owning source model. |
| Missing consumer constraint rows | Rebuild Build Parametric. |
| Contract ready but mesh drift | Rebuild constrained triangulation. |
| Intersection patch-to-slope-face mismatch | Rebuild Intersection and Slope Face constraints. |
| Intersection patch-to-design mismatch | Rebuild Intersection and Design constraints. |
| Region/control mismatch | Review Region spans, then Build Parametric. |
| Ordinary lane/shoulder/slope mismatch | Rebuild Applied Sections, then constrained surfaces. |
| Drainage handoff missing | Edit Drainage source or Intersection grading policy. |
| Solid loop open | Fix upstream breakline ownership before Watertight Solid generation. |

## Testing Plan

Focused contract tests now cover:

- ordinary road lane, shoulder, side-slope, daylight, gutter, and ditch breakline role creation
- ordinary road consumer constraint metadata for Design, Slope Face, and Drainage surfaces
- straight and curved ordinary-road zero-mismatch shared breakline audit
- Region start/end, Region transition, and Assembly-change boundary rows
- Intersection endpoint insertion and shared breakline source refs before patch triangulation
- Intersection Surface, Design Surface, and Slope Face Surface contract and mesh adherence counts
- T preset starter Intersection zero geometry, mesh, and reversed mismatch after full rebuild
- curb-return inner/outer/contact breaklines and structured strip/core triangulation without fan fallback
- shoulder handoff grouping through `patch_to_shoulder`, `shoulder_to_slope_face`, and `curb_return_to_shoulder`
- drainage handoff lineage from Applied Sections and `IntersectionDrainageHintResult`
- Region/control-area handoff station refs and role-aware Recommended Action rows
- shared breakline highlight rows by ordinary, Intersection, shoulder, drainage, and solid-readiness roles
- solid-readiness adjacency graph, boundary trace rows, and Watertight Solid output preservation

Manual QA checklist:

- Create a normal road corridor without Intersection.
- Run Applied Sections.
- Run Build Parametric.
- Open Breakline Audit.
- Confirm lane, shoulder, side-slope, daylight, gutter/ditch, Region transition, and Assembly-change contacts report contract status.
- Highlight ordinary corridor breakline roles.
- Create T preset Intersection.
- Run Applied Sections.
- Run Build Parametric.
- Open Breakline Audit.
- Confirm top summary.
- Highlight each breakline role.
- Check that cyan highlight aligns with visible surface contacts.
- Confirm drainage handoff rows appear only when source drainage/hint rows exist.
- Confirm solid-readiness rows expose open, duplicate, reversed, and non-manifold counts.
- Hide/show Intersection Surface, Design Surface, Slope Face Surface, and future Shoulder-surface consumers to confirm contact ownership.

## Implementation Order

Completed implementation record:

1. Phase 1 role-level row split and panel details.
2. Phase 2 general road surface breaklines.
3. Phase 3 normal-road Region transition and Assembly-change breaklines.
4. Phase 4 constrained Intersection Surface generation.
5. Phase 5 curb-return breaklines and structured strip triangulation.
6. Phase 6 Intersection shoulder contacts.
7. Phase 7 drainage handoff for both normal roads and Intersections.
8. Phase 8 Intersection control-area handoff.
9. Phase 9 solid-readiness graph and Watertight Solid boundary trace rows.

## Acceptance Criteria

The implemented plan is accepted when:

- Breakline Audit reports role-level rows, not only surface-level totals.
- Normal road corridor surfaces report lane, shoulder, side-slope, daylight, ditch/gutter, and Region transition shared breakline status where source data exists.
- T preset Intersection reports zero contract mismatch after rebuild.
- Curb-return, shoulder, slope-face, design, drainage, and Region handoff contacts are represented by shared breakline rows where source data exists.
- Missing source intent appears as diagnostics, not silent geometry cleanup.
- Watertight Solid readiness can consume the shared breakline graph without guessing from preview mesh.

Current status:

- Focused FreeCADCmd and contract tests satisfy the implemented acceptance criteria.
- Remaining follow-up scope is limited to future dedicated Shoulder Surface consumption, subgrade/material-layer bodies, and continued production Watertight Solid builder integration.
