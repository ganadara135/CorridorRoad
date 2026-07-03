# V1 Intersection Completion Quality Plan

Date: 2026-06-25  
Status: Active planning document  
Scope: improving the current Intersection visual/result completeness after the first production-quality T-intersection output

## Purpose

This plan defines the remaining work needed to raise Intersection output quality from a working visual result to a traceable, watertight-ready, Digital Twin-ready result.

The key goal is to make the current Intersection output less dependent on late visual repair and more dependent on shared result contracts.

The highest-priority item is a shared boundary breakline contract.

Intersection is the first target domain, but the contract should also serve other boundary-sharing output families such as:

- `Intersection Surface`
- `Design Surface`
- `Slope Face Surface`
- curb-return / pavement tie-in strips
- Region-to-Region surface transitions
- corridor-to-structure contact edges
- drainage / ditch / gutter handoff edges
- future Watertight Solid target boundaries

## Current Baseline

The current Intersection build can create a usable T-intersection preview with:

- main-road and side-road Design/Slope Face surfaces
- transitional `Intersection Surface` patch
- curb-return surface area
- side-slope strip restoration from pre-clip Side Slope TIN
- suppressed legacy boundary strip preview/output objects
- source/result review rows and transitional handoff diagnostics

Known remaining weakness:

- surfaces may visually touch without sharing the same explicit boundary row
- some boundaries are copied as coordinates instead of consumed from one shared contract
- curb-return patch triangulation is still a transitional fan-like output
- Guided Review does not yet explain all gap/restore/skip decisions clearly enough
- downstream solids still see the intersection patch as transitional

## Status Legend

| Status | Meaning |
| --- | --- |
| Planned | Not implemented. |
| Started | First slice exists but the accepted contract is incomplete. |
| Done | Implemented and covered by focused tests or manual QA. |
| Blocked | Requires a prior task. |

## Phase 1 - Shared Breakline Contract

Status:

- Done for the first common-contract implementation.
- The implementation adds the common `SharedBreaklineResult` model, Intersection shared breakline builder, TIN metadata attachment, preview metadata, audit helper, geometric endpoint matching, and focused contract tests.
- Region transitions, Drainage, and Watertight Solid boundary trace/handoff blocker paths now consume the common model. Structure-specific shared breakline adoption remains future scope.

Goal:

- make contact edges between boundary-sharing result/output objects one shared result contract.
- use Intersection as the first implementation domain.

Current issue:

- each surface can generate or restore its own edge geometry
- even if the output looks connected, downstream consumers cannot prove that both sides share the same boundary identity
- this is not unique to Intersection; any adjacent surface, structure, drainage, or solid output can hit the same problem

Core rule:

- one evaluated breakline row owns each accepted contact edge
- surfaces consume that row by reference
- no result/output object should invent its own contact edge when a shared breakline row exists
- domain-specific builders may add specialized metadata, but the shared boundary identity should stay common

### 1.1 Result Model

Add a common result contract:

- file: `freecad/Corridor_Road/v1/models/result/shared_breakline.py`
- result model: `SharedBreaklineResult`
- row model: `SharedBreaklineRow`
- point row model: `SharedBreaklinePointRow`

Intersection-specific helpers may live near the Intersection evaluation service, but should return or consume the common `SharedBreaklineResult`.

Recommended row fields:

| Field | Purpose |
| --- | --- |
| `breakline_id` | stable row id |
| `domain_kind` | `intersection`, `region_transition`, `structure`, `drainage`, `corridor`, `watertight_solid` |
| `domain_ref` | owning source/result ref such as Intersection id, Region transition id, Structure id, or Drainage id |
| `breakline_role` | domain role such as `patch_to_design`, `patch_to_slope_face`, `curb_return`, `pavement_tie_in`, `daylight_tie_in`, `region_transition`, `structure_contact`, `ditch_handoff`, `solid_boundary` |
| `source_contract_refs` | edge-network, surface-zone, patch-boundary, AppliedSection, Structure, Drainage, or Region source refs |
| `consumer_refs` | result/output object refs expected to consume the breakline |
| `from_output_role` | first consumer role |
| `to_output_role` | second consumer role |
| `point_rows` | ordered xyz points, or refs to point rows |
| `station_start` / `station_end` | station span when available |
| `alignment_ref` | participating Alignment |
| `side` | left/right/center/unknown |
| `material_role` | pavement, shoulder, side_slope, curb_return, structure, ditch, gutter, etc. |
| `source_status` | accepted/warning/error/defaulted |
| `diagnostic_rows` | row-level diagnostics |
| `handoff_target` | owning source stage for repair |

Recommended point row fields:

| Field | Purpose |
| --- | --- |
| `point_id` | stable point id |
| `breakline_ref` | parent breakline row |
| `sequence` | ordered index |
| `x`, `y`, `z` | accepted shared coordinate |
| `station` | station if available |
| `offset` | lateral offset if available |
| `source_point_ref` | AppliedSection, edge-network, or patch-boundary point lineage |

### 1.2 Domain Builders

Add domain builders in the evaluation/output layer, not in preview mappers.

Common helper:

- `shared_breakline_result(...)`

Intersection first-slice helper:

- `corridor_intersection_shared_breakline_result(...)`

Inputs:

- `IntersectionModel`
- `AppliedSectionSet`
- `IntersectionEdgeNetworkResult`
- `IntersectionSurfaceZoneResult`
- `IntersectionPatchBoundaryResult`
- `IntersectionSlopeFaceBoundaryResult`
- pre-clip Side Slope TIN where needed for side-slope contact rows

Output:

- one `SharedBreaklineResult`

Rules:

- Use edge-network and surface-zone rows first.
- Use patch boundary rows only as transitional fallback.
- Use AppliedSection side-slope rows for `patch_to_slope_face` breaklines.
- Never derive breaklines from final preview mesh edges if a result/source row exists.
- If two candidate edges are nearly coincident, snap only by creating a diagnostic and choosing the accepted owner; do not silently move source points.
- Keep the common breakline contract independent of Intersection-specific object names.

Future domain builders:

| Domain | Shared breakline use |
| --- | --- |
| Region transition | shared boundary between adjacent corridor surface regions |
| Structure | contact edges between road surface/solid and bridge, culvert, retaining wall, or custom structure output |
| Drainage | ditch/gutter/inlet handoff edges that must remain traceable to Drainage source rows |
| Watertight solids | shell adjacency edges used for fuse/trim/gap validation |

### 1.3 Surface Consumption

Refactor Build Parametric output creation so each consumer can consume shared breakline rows:

| Surface | Required behavior |
| --- | --- |
| `Intersection Surface` | outer boundary uses `patch_to_design`, `curb_return`, and `patch_to_slope_face` breakline rows |
| `Design Surface` | clipped edge references matching `patch_to_design` rows |
| `Slope Face Surface` | restored/strip edge references matching `patch_to_slope_face` rows |
| `Curb Return` | arc/chord boundary references `curb_return` rows |
| Watertight solids | shell boundaries consume the same breakline refs |
| Future structure/drainage outputs | consume `structure_contact`, `ditch_handoff`, or `gutter_handoff` rows |

Implementation detail:

- add `boundary_refs` entries on each TIN surface that include breakline ids
- add triangle `notes` or future row metadata with `breakline_ref`
- attach preview properties:
  - `SharedBreaklineResultId`
  - `SharedBreaklineCount`
  - `SharedBreaklineConsumedCount`
  - `SharedBreaklineMismatchCount`
  - `IntersectionSharedBreaklineCount` may remain as an Intersection-specific convenience alias

### 1.4 Boundary Audit

Add a validation helper:

- common: `shared_breakline_audit(...)`
- first Intersection wrapper: `corridor_intersection_shared_breakline_audit(...)`

Checks:

- every shared breakline has at least two intended consumers when required
- consumed surface edges have matching endpoints within tolerance
- endpoint z-values match the shared breakline z-values
- no consumer edge is reversed without being recorded
- no gap exceeds tolerance
- no duplicated local-only boundary exists where a shared breakline is available

Recommended tolerances:

- XY endpoint tolerance: `1.0e-4 m`
- Z endpoint tolerance: `1.0e-4 m`
- max gap warning threshold: configurable, default `0.005 m`

Acceptance criteria:

- Build Parametric review shows `shared_breakline=ready`
- `Intersection Surface` and `Slope Face Surface` expose the same `patch_to_slope_face` breakline refs
- `Intersection Surface` and `Design Surface` expose the same `patch_to_design` breakline refs
- tests verify reversed edge order, missing consumer, z mismatch, and accepted match
- the common result model does not depend on Intersection-only fields
- future Region/Structure/Drainage builders can reuse the same row model without schema changes

## Phase 2 - Curb Return Triangulation Quality

Goal:

- replace transitional fan-like curb-return triangulation with a better conditioned surface output.

Tasks:

| Task id | Status | Work item | Acceptance criteria |
| --- | --- | --- | --- |
| INT-CQ-CURB-001 | Done | Normalize curb-return boundary as ordered breakline rings. | Curb-return boundary and shared breakline rows are consumed without re-sampling from preview geometry. |
| INT-CQ-CURB-002 | Done | Replace fan fallback with constrained ear clipping or structured strip triangulation. | Structured strip/core triangulation is used for valid curb-return arcs and does not emit `ordered_fan_fallback` in focused tests. |
| INT-CQ-CURB-003 | Done | Add quality rows for skinny triangles, long edges, boundary crossings, and fan fallback usage. | Guided Review reports patch triangulation mode, bbox ratio, min quality, and skinny triangle warnings. |
| INT-CQ-CURB-004 | Done | Add tests for T, skewed, and wide-radius curb returns. | Focused regression tests cover T, skewed T, and wide-radius curb-return structured-strip triangulation without fan fallback. |

Implementation notes:

- Intersection Surface uses `structured_strip_curb_return_blend` for the T preset and preserves curb-return arc/segment counts.
- Curb-return shared breakline roles include outer, inner, pavement contact, shoulder contact, and slope-face contact rows.
- Focused tests verify `curb_return_blend` and `curb_return_core` quality refs and absence of `ordered_fan_fallback` for valid arcs.
- Skewed and wide-radius curb-return tests use source/result contract inputs and verify structured-strip triangulation before preview object generation.
- Follow-up candidate: practical exclusion polygon union can be strengthened for highly skewed tie-in strips; this is separate from curb-return strip triangulation.

## Phase 3 - Intersection Surface Role And Replacement Gate

Goal:

- make it clear whether the black `Intersection Surface` is final accepted pavement replacement or transitional review geometry.

Tasks:

| Task id | Status | Work item | Acceptance criteria |
| --- | --- | --- | --- |
| INT-CQ-GATE-001 | Done | Split `review_patch`, `accepted_surface_zone`, and `replacement_candidate` status fields. | Review rows distinguish transitional patch output, accepted surface-zone candidate output, and replacement readiness. |
| INT-CQ-GATE-002 | Done | Add replacement gate explanation to Guided Review. | Guided Review and Build Review rows show gate status, blocker kind, recommendation, and next source/result stage. |
| INT-CQ-GATE-003 | Done | Color/style accepted vs transitional Intersection Surface differently. | Transitional patch and accepted candidate visual styles are separated and replacement preview objects preserve visual-role metadata. |
| INT-CQ-GATE-004 | Done | Add tests for replacement gate status propagation to Watertight/Exchange. | Transitional patch and shared breakline blockers propagate to Watertight, Simulation Package, and Exchange context tests. |

Implementation notes:

- `IntersectionSurfaceReplacementGateStatus`, readiness, handoff preference, selected downstream role, and blocker kind are persisted on the Intersection Surface preview.
- Watertight and Simulation Package handoff paths block transitional-only patch output and preserve replacement blocker context for Exchange.
- Transitional Intersection patch previews use `intersection_transitional_patch` styling and preserve `IntersectionSurfaceReplacementVisualRole=transitional_review_patch`.
- Accepted replacement candidates use `intersection_accepted_candidate` styling through the same replacement visual-style helper.

## Phase 4 - Main/Side Road Tie-In Cleanup

Goal:

- remove small gaps, overlaps, and duplicated edge fragments around the main-road and side-road contact zone.

Tasks:

| Task id | Status | Work item | Acceptance criteria |
| --- | --- | --- | --- |
| INT-CQ-TIE-001 | Done | Add tie-in edge continuity audit. | Build Review now includes an Intersection Tie-In Continuity row reporting tie-in/curb/overlap edge counts plus shared-breakline mismatch, reversed, and missing-consumer counts. |
| INT-CQ-TIE-002 | Done | Snap only generated result edges to accepted shared breakline points. | TIN result vertices within tolerance snap to accepted shared breakline points; source rows remain unchanged and snap diagnostics are preserved on result quality rows. |
| INT-CQ-TIE-003 | Done | Add station-span diagnostics around intersection entry/exit stations. | Tie-In Continuity review notes include the active Intersection Applied Section station span. |
| INT-CQ-TIE-004 | Done | Add manual QA capture fields for before/after screenshots. | Intersection preview metadata records reproducible before/after screenshot names, visibility context, checklist rows, and Tie-In review notes expose the QA capture summary. |

Implementation notes:

- `intersection_tie_in_continuity` review rows summarize pavement/stem tie-in edges, curb-return edges, overlap-cut edges, boundary diagnostics, and shared breakline audit counts.
- The row status becomes error for geometry mismatch, missing consumer, or boundary diagnostics; warning for mesh mismatch or reversed edges.
- Station span is derived from source Applied Sections with the same active Intersection id.
- Shared breakline constraint edge generation can snap nearby generated TIN result vertices to accepted shared breakline endpoint coordinates without mutating `SharedBreaklinePointRow` source/result contract rows.
- Snap count, max distance, and per-vertex diagnostics are stored as `shared_breakline_constraint_snap_*` quality rows.
- `IntersectionManualQA*` preview properties preserve before/after screenshot names, grouped visibility context, and checklist rows for reproducible tie-in visual QA.

## Phase 5 - Superelevation And Grading Context

Goal:

- ensure intersection grading, road crown, and approach superelevation do not conflict silently.

Tasks:

| Task id | Status | Work item | Acceptance criteria |
| --- | --- | --- | --- |
| INT-CQ-GRADE-001 | Done | Add grading ownership row per control area. | Build Review now includes an Intersection Grading Ownership row showing Intersection policy vs normal superelevation ownership. |
| INT-CQ-GRADE-002 | Done | Add crossfall transition diagnostics at entry/exit breaklines. | Grading Ownership review notes expose superelevation source count, transition count, left/right crossfall ranges, max crossfall delta, and station span. |
| INT-CQ-GRADE-003 | Done | Preserve controlling Profile refs on shared breakline rows. | Shared breakline source contract refs now include AppliedSection profile ids for ordinary corridors and Intersection leg/grading profile lineage for intersection rows. |

Implementation notes:

- `intersection_grading_ownership` review rows summarize grading policy, mode, target crossfall, superelevation source/transition counts, left/right crossfall ranges, max crossfall delta, grading context result ref, profile refs, and station span.
- The row status is warning when crossfall changes across the active Intersection station span or transition rows are present.
- Ordinary corridor shared breaklines preserve AppliedSection `profile_id` lineage in `source_contract_refs`.
- Intersection shared breaklines preserve participating leg profile refs and grading policy refs in `source_contract_refs`.

## Phase 6 - Drainage Review Handoff

Goal:

- keep intersection drainage intent visible without reintroducing false Drainage Flow highlights.

Tasks:

| Task id | Status | Work item | Acceptance criteria |
| --- | --- | --- | --- |
| INT-CQ-DRN-001 | Done | Add separate `Intersection Drainage Hint` review marker. | Low-point/outlet hints are consumed as `IntersectionDrainageHintResult` metadata without recreating false Drainage Flow highlight objects. |
| INT-CQ-DRN-002 | Done | Attach drainage hint refs to curb/gutter breaklines. | Intersection drainage hint rows map to gutter, ditch, and flow-split shared breakline rows with hint source refs. |
| INT-CQ-DRN-003 | Done | Add accepted drainage handoff gate. | Build Review separates hint-only drainage visibility from accepted DrainageModel element/flow-route handoff readiness. |

Implementation notes:

- Intersection drainage handoff rows preserve hint source refs and consumers.
- Drainage handoff breaklines are visible through Breakline Audit and role-aware Recommended Action.
- `intersection_drainage_handoff_gate` reports `hint_only`, `accepted_drainage`, or missing-reference states with recommended action text.
- The gate checks Intersection drainage policy refs against accepted DrainageModel element and flow-route rows before reporting downstream readiness.

## Phase 7 - Guided Review And Object Visibility

Goal:

- make the user-facing review surface explain what happened.

Tasks:

| Task id | Status | Work item | Acceptance criteria |
| --- | --- | --- | --- |
| INT-CQ-REV-001 | Done | Add Shared Breakline review row. | Review shows ready/warning/error counts and focus object. |
| INT-CQ-REV-002 | Done | Add Side Slope restore/strip explanation. | Side Slope strip and preclip restore paths expose restored, skipped-existing, and skipped-intersection counts on preview metadata and review notes. |
| INT-CQ-REV-003 | Done | Add grouped visibility toggles for Design, Intersection, Slope Face, Breaklines, Diagnostics. | Build Parametric Visibility tab exposes grouped toggles backed by shared visibility helpers and focused tests. |
| INT-CQ-REV-004 | Done | Add focus helpers for mismatched breaklines. | Double-clicking a row highlights the exact boundary segment. |

Implementation notes:

- The Visibility tab includes grouped toggles for Design, Intersection, Slope Face, Breaklines, and Diagnostics while preserving individual preview toggles.
- Grouped toggles use shared helper functions so panel UI, tests, and future automation call the same visibility contract.

## Phase 8 - Watertight Solid Readiness

Goal:

- make intersection surfaces ready for closed shell generation.

Tasks:

| Task id | Status | Work item | Acceptance criteria |
| --- | --- | --- | --- |
| INT-CQ-WT-001 | Done | Add shell boundary gap audit using shared breaklines. | Solid target discovery reads shared breakline solid-readiness status/counts and blocks Intersection solid targets when open, duplicate, or non-manifold boundary issues remain. |
| INT-CQ-WT-002 | Done | Map shared breaklines to solid face adjacency rows. | Watertight Solid output rows derive deterministic `boundary_adjacency_rows` from shared breakline boundary trace rows so production builders can fuse by shared identity instead of coordinate guessing. |
| INT-CQ-WT-003 | Done | Block final handoff when shared breakline audit fails. | Watertight handoff summary blocks final quality when the Intersection shared breakline audit reports warning/error or mismatch counts; Simulation Package and Exchange context preserve the blocker. |

Implementation notes:

- Solid target discovery consumes `SharedBreaklineSolidReadinessStatus`, open-end, duplicate-edge, reversed-edge, and non-manifold-node counts from Build Parametric preview objects.
- Intersection Watertight targets receive `SharedBreaklineSolidReadiness` notes, source refs, and target diagnostics before Part solid generation.
- Shared breakline boundary trace rows are carried as source context for Intersection targets and Watertight output rows.
- `WatertightSolidOutputRow.boundary_adjacency_rows` derives deterministic candidate adjacency rows from shared breakline boundary trace rows.
- FreeCAD `V1WatertightSolidOutput` objects persist and round-trip `SolidBoundaryAdjacencyRows`.
- Future production Part/solid fusion should consume these adjacency identities instead of mesh coordinate guessing.
- `IntersectionWatertightHandoffSummary` reads `SharedBreaklineAuditStatus`, geometry mismatch, mesh mismatch, missing consumer, and reversed edge counts from `V1CorridorIntersectionSurfacePreview`.
- Shared breakline audit issues force `final_quality_status=blocked` and `digital_twin_handoff=review_required` even when accepted-zone solid targets exist.
- `SimulationPackageOutput` preserves shared breakline audit status/counts and adds `intersection_shared_breakline_audit_blocked` to diagnostic kinds when the audit blocks handoff.
- Exchange source-context rows expose the same shared breakline audit status/counts so downstream packages can explain why the Intersection handoff is blocked.

## Recommended Execution Order

1. Add `SharedBreaklineResult` and point rows.
2. Build the first Intersection shared breakline result from existing edge/surface-zone/patch/slope-face contracts.
3. Attach shared breakline refs to `Intersection Surface` and `Slope Face Surface`.
4. Add shared breakline audit and Guided Review row.
5. Replace current side-slope restore diagnostics with shared-breakline-aware diagnostics.
6. Improve curb-return triangulation quality.
7. Add drainage hint marker and grading ownership review.
8. Add Watertight Solid gap/readiness gate.

## First Implementation Slice

Recommended first slice:

- create `SharedBreaklineResult`
- generate `patch_to_slope_face` rows from the current Intersection patch boundary plus Applied Section side-slope edges
- attach those refs to `Intersection Surface` and `Slope Face Surface`
- add an audit test that proves both surfaces consume the same breakline id

Initial status:

- Done for shared consumption and first geometric endpoint audit.
- `SharedBreaklineResult`, `SharedBreaklineRow`, and `SharedBreaklinePointRow` exist as common result models.
- `corridor_intersection_shared_breakline_result(...)` generates first Intersection `patch_to_design` and `patch_to_slope_face` rows.
- `Slope Face Surface` TIN `boundary_refs` can consume shared breakline ids.
- Build Parametric preview objects expose `SharedBreakline*` properties.
- `shared_breakline_audit(...)` verifies consumer refs and boundary-edge endpoint matches.
- Build Parametric review notes expose audit summary as `audit=<status> geometry=<matched>/<tested> missing=<count> mismatch=<count> reversed=<count>`.
- Preview objects expose `SharedBreaklineAuditStatus`, `SharedBreaklineGeometryMatchCount`, `SharedBreaklineGeometryMismatchCount`, `SharedBreaklineMissingConsumerCount`, `SharedBreaklineMismatchCount`, `SharedBreaklineReversedEdgeCount`, `SharedBreaklineAuditSummary`, and `SharedBreaklineAuditNotes`.
- Build Parametric exposes a `Breakline Audit` tab with a top-level issue/no-issue summary followed by per-surface audit rows and a `Recommended Action` column.
- Breakline Audit rows can create a cyan `Shared Breakline Highlight` review object from stored `SharedBreaklineSegmentRows`, so the accepted shared boundary can be checked directly in the 3D view.
- The audit accepts boundary chains split across multiple TIN boundary edges, so T-intersection triangulation subdivision does not produce a false `geometry_mismatch` when the chain still follows the shared breakline.
- Surfaces now carry `shared_breakline_constraint_segment_rows` quality metadata when they consume shared breaklines. Breakline Audit treats this normalized constraint contract as the primary consumption proof, with mesh edge matching as a secondary fallback.

Do not start by changing triangulation.

The first slice should prove shared boundary ownership before changing visible mesh shape.

Next implementation phase:

- Phase 2 - Curb Return Triangulation Quality.
- Replace transitional fan-like curb-return triangulation with ordered breakline rings and better conditioned triangles.

## Manual QA Checklist

After each phase, test with:

- T Intersection - Basic
- Cross Intersection - Basic
- Skewed Intersection - Basic
- Urban Curb/Gutter - Basic
- Drainage-Sensitive Sag - Basic

For each case capture:

- `IntersectionManualQABeforeScreenshotName`
- `IntersectionManualQAAfterScreenshotName`
- `IntersectionManualQAVisibilityContext`
- `Intersection Surface` visible state
- `Slope Face Surface` visible state
- Shared Breakline review row
- Side Slope restore counts
- Curb-return triangle quality row
- Watertight readiness blocker status
