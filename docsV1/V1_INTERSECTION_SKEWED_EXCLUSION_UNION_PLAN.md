# V1 Intersection Skewed Exclusion Union Plan

Date: 2026-06-26  
Status: Implemented through focused contract tests; manual QA pending real FreeCAD document  
Scope: practical exclusion footprint robustness for skewed Intersection tie-in geometry

## Purpose

This plan separates skewed intersection exclusion-footprint work from curb-return surface triangulation work.

The curb-return surface can already be generated with `structured_strip_curb_return_blend` for normal T, skewed T, and wide-radius curb-return cases.

The remaining issue is different:

- the Intersection patch can be triangulated correctly
- but the practical exclusion polygon used to clip or protect adjacent `Design Surface` and `Slope Face Surface` TIN fragments can fail for highly skewed tie-in strips

This plan defines how to make that exclusion footprint source-driven, inspectable, and robust enough for skewed intersections.

## Scope

In scope:

- practical exclusion polygon generation from evaluated result contracts
- skewed T-intersection tie-in strip union
- curb-return arc surface parts as part of the exclusion footprint
- diagnostics when the footprint cannot be built
- focused FreeCADCmd contract tests
- Build Parametric review metadata where useful

Out of scope:

- changing curb-return structured-strip triangulation itself
- replacing the transitional Intersection Surface patch with an accepted zone surface
- full computational geometry library adoption unless a later phase proves it necessary
- writing generated preview geometry back as source intent

## Core Rule

The practical exclusion footprint must be derived from evaluated source/result contracts:

- `IntersectionModel`
- `IntersectionTieInEdgeResult`
- `IntersectionBoundarySegmentResult`
- curb-return boundary segment rows
- future accepted surface-zone boundary rows

It must not infer engineering meaning from already-generated mesh fragments.

If a stable footprint cannot be built, the result should return diagnostics and keep adjacent surface clipping conservative rather than silently producing a misleading exclusion area.

## Current Baseline

The current implementation can:

- generate curb-return boundary arcs for T intersections
- triangulate curb-return blend/core parts without `ordered_fan_fallback`
- build practical exclusion polygons for normal T-intersection tie-in strips
- clip daylight/design fragments using a practical intersection boundary when available

Known weakness:

- when the side-road tie-in strip enters at a high skew angle, the current tie-in strip union can return `None`
- this does not mean the curb-return surface failed
- it means the footprint union used by exclusion/clipping does not yet robustly merge skewed strip polygons

## Status Legend

| Status | Meaning |
| --- | --- |
| Planned | Not implemented. |
| Started | First slice exists but accepted behavior is incomplete. |
| Done | Implemented and covered by focused tests or manual QA. |
| Blocked | Requires a prior task. |

## Phase 1 - Reproduce And Classify

Goal:

- make the skewed failure reproducible with focused result-contract tests.

Tasks:

| Task id | Status | Work item | Acceptance criteria |
| --- | --- | --- | --- |
| INT-SKEW-EXCL-001 | Done | Add a skewed tie-in fixture that produces a valid `IntersectionBoundarySegmentResult` but no practical exclusion polygon. | Focused test proves curb-return triangulation succeeds while practical exclusion footprint is missing. |
| INT-SKEW-EXCL-002 | Done | Classify failure mode in diagnostics. | The footprint candidate reports invalid primary strip, invalid secondary strip, invalid union, zero-area output, and curb-return-ready context. |
| INT-SKEW-EXCL-003 | Done | Add review-facing diagnostic notes. | Build/review notes can explain that clipping used fallback boundary while the practical footprint is missing. |

Implementation notes:

- Added a practical footprint candidate helper that preserves diagnostics instead of returning only `None`.
- Existing `_intersection_practical_exclusion_polygon_from_boundary_segments` remains compatibility-safe and still returns `None` unless the candidate is `ready`.
- Fallback ordered patch-boundary exclusion now carries `practical_footprint_status` and diagnostic quality rows.
- Guided Review exclusion notes now include `footprint=missing` and the first practical footprint diagnostic.

## Phase 2 - Normalize Tie-In Strip Inputs

Goal:

- make skewed strip polygons valid before union.

Tasks:

| Task id | Status | Work item | Acceptance criteria |
| --- | --- | --- | --- |
| INT-SKEW-EXCL-004 | Done | Normalize tie-in strip point order by centerline side and signed area. | Tie-in strip candidates are normalized to positive signed area before union consumption. |
| INT-SKEW-EXCL-005 | Done | Remove duplicate and near-duplicate XY points before union. | Tie-in strip polygons remove repeated and near-duplicate XY points before validity checks. |
| INT-SKEW-EXCL-006 | Done | Add tolerance-aware point equality for strip endpoints. | Degenerate near-duplicate strip edges are rejected before union construction. |

Implementation notes:

- Added `_normalize_intersection_tie_in_strip_polygon` for strip-level point cleanup.
- `_intersection_tie_in_strip_polygon` now consumes normalized candidates and still rejects zero-area or self-crossing strips.
- Focused tests cover winding normalization, duplicate removal, and degenerate near-duplicate rejection.
- This phase prepares stable strip inputs; the skewed outer-loop union itself remains Phase 3 scope.

## Phase 3 - Robust Practical Union

Goal:

- build a usable exclusion footprint from overlapping or touching strip polygons and curb-return parts.

Implementation direction:

- first attempt deterministic strip boundary tracing from result rows
- then include curb-return surface parts as expansion polygons
- prefer a simple local polygon-union routine only if it stays deterministic and testable
- if the union cannot be made watertight, return a degraded but explicit footprint status rather than silent success

Tasks:

| Task id | Status | Work item | Acceptance criteria |
| --- | --- | --- | --- |
| INT-SKEW-EXCL-007 | Done | Build a graph of candidate boundary edges from tie-in strip polygons and curb-return parts. | Existing union graph remains the first pass and consumes normalized tie-in and curb-return polygons. |
| INT-SKEW-EXCL-008 | Done | Trace the outer footprint loop from exterior candidate edges. | Normal T and skewed T fixtures return one non-self-crossing outer loop. |
| INT-SKEW-EXCL-009 | Done | Preserve curb-return expansion in the traced footprint. | Focused hull fallback test proves curb-return arc/blend polygons can expand the footprint beyond strip-only hulls. |
| INT-SKEW-EXCL-010 | Done | Add fallback status for partial footprints. | If graph tracing cannot close a loop, exterior-hull recovery is used with diagnostics; missing remains explicit if recovery also fails. |

Implementation notes:

- Added `_xy_polygon_exterior_hull_boundary` as a deterministic source/result fallback when the segment graph cannot close an outer loop.
- Practical footprint candidates now preserve the graph failure diagnostic and add `intersection_exclusion_footprint_outer_loop_recovered:exterior_hull` when fallback recovery succeeds.
- Skewed T practical exclusion now returns `ready` with `practical_boundary_aligned=True` instead of silently falling back to `None`.
- The fallback still uses evaluated tie-in strip and curb-return part polygons, not generated preview meshes.

## Phase 4 - Surface Clipping Integration

Goal:

- consume the improved footprint without changing source ownership.

Tasks:

| Task id | Status | Work item | Acceptance criteria |
| --- | --- | --- | --- |
| INT-SKEW-EXCL-011 | Done | Attach footprint quality metadata to clipped Design/Slope surfaces. | TIN quality rows include footprint source, strategy, status, area, and diagnostics. |
| INT-SKEW-EXCL-012 | Done | Ensure missing footprint does not remove valid adjacent surface triangles. | Explicit missing/degraded practical footprints use conservative skip and preserve adjacent triangles. |
| INT-SKEW-EXCL-013 | Done | Verify skewed T clipping with focused TIN fixtures. | Focused fixture removes triangles inside the recovered skewed footprint and keeps outside triangles. |

Implementation notes:

- Recovered skewed practical footprints are now consumed by `_clip_tin_surface_by_intersection_exclusion`.
- Clipped TINs preserve `intersection_exclusion_practical_footprint_status` and diagnostics as quality rows.
- Explicit `missing` or `degraded` practical footprints use `conservative_skip_*_practical_footprint` and do not remove triangles.
- Focused tests cover both ready skewed clipping and conservative missing-footprint behavior.

## Phase 5 - Review UX And Manual QA

Goal:

- make the issue visible to users before they inspect the model visually.

Tasks:

| Task id | Status | Work item | Acceptance criteria |
| --- | --- | --- | --- |
| INT-SKEW-EXCL-014 | Done | Add Review row or notes for practical exclusion footprint status. | Guided Review distinguishes `ready`, `degraded`, and `missing` footprint states. |
| INT-SKEW-EXCL-015 | Done | Add recommended actions. | Missing/degraded states tell the user whether to adjust intersection source, rebuild Applied Sections, or review skew/tie-in geometry. |
| INT-SKEW-EXCL-016 | Done | Add manual QA checklist for skewed intersections. | QA procedure verifies curb-return surface, exclusion footprint, adjacent surface clipping, and shared breakline audit together. |

Implementation notes:

- Guided Review exclusion notes now include practical footprint status and the first footprint diagnostic.
- Missing/degraded practical footprint states include recommended actions.
- `V1_INTERSECTION_MANUAL_QA.md` includes a dedicated skewed practical exclusion footprint checklist.

## Acceptance Criteria

The plan is complete when:

- normal T, skewed T, and wide-radius curb-return triangulation still pass without fan fallback
- skewed T practical exclusion footprint returns a non-self-crossing outer loop
- clipping tests prove inside/outside triangles are handled correctly
- missing/degraded footprint states are visible in review output
- no implementation reads generated preview geometry as source truth
- FreeCADCmd focused tests cover the result-contract path

## Relationship To Other Plans

- `V1_INTERSECTION_COMPLETION_QUALITY_PLAN.md` covers overall intersection completion quality.
- `INT-CQ-CURB-004` covers curb-return triangulation variants.
- This document covers the separate skewed practical exclusion footprint union problem.
- Shared breakline audit work remains the proof path for adjacent surface contact identity.

## Open Questions

- Should skewed footprint union remain a local deterministic edge-tracing routine, or should a small proven polygon clipping dependency be adopted later?
- What default tolerance should be used for near-touching skewed strip corners: project tolerance, breakline audit tolerance, or a dedicated footprint tolerance?
- Should degraded footprints still be visualized as diagnostic outlines in the Breakline Audit tab?
