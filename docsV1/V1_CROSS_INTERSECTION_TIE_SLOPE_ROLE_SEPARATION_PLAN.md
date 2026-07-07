# V1 Cross Intersection Tie Slope Role Separation Plan

Last updated: 2026-07-07

## Purpose

Define the source-driven plan for completing `Intersection Tie Slope Surface` in Cross intersections without reintroducing fan-shaped patches, mesh-derived repairs, or mixed surface ownership.

This plan supersedes the failed direction of expanding Cross Tie Slope by directly connecting curb-return arcs, generated surface triangles, or broad internal cap geometry.

## Problem

The current Cross intersection result can create some `Intersection Tie Slope Surface` panels, but the output still does not match the intended ownership model.

Observed issues:

- Tie Slope panels are still too small near some approach-to-intersection corners.
- Some earlier attempts created panels inside the curb-return or central intersection area instead of the road-to-intersection transition band.
- Fan or wedge panels can appear when non-adjacent edges are connected.
- Rectangular supplemental Applied Section corners are the intended reach target, but the code has not yet separated that target from curb-return geometry ownership.

## Core Rule

For Cross intersections, `Intersection Tie Slope Surface` owns only the side-slope transition band between road Applied Sections and intersection supplemental Applied Sections.

It may extend into the curb-return influence area when, and only when, the target edge comes from the same intersection supplemental Applied Section sequence.

The source of truth is:

- intersection source/evaluation context
- station-ordered Applied Section rows
- same alignment or leg ownership
- same side
- adjacent Applied Section pairs
- accepted side-slope boundary edges

The source of truth is not:

- generated TIN triangles
- preview or highlight objects
- tree objects
- curb-return mesh boundaries
- ordinary `Slope Face Surface` output
- `Intersection Slope Face Surface` output

## Surface Ownership

`Intersection Tie Slope Surface` owns:

- transition strips from ordinary road side-slope sections to intersection supplemental side-slope sections
- Cross approach windows between the first active intersection Applied Section and the innermost valid supplemental Applied Section edge
- primary and secondary road transition bands, handled with the same rules

`Intersection Tie Slope Surface` does not own:

- central pavement/intersection surface
- curb-return interior fill
- broad circular fan fills
- ordinary corridor side-slope strips outside the intersection transition window
- residual gaps whose source role is unknown

`Intersection Slope Face Surface` owns:

- curb-return-adjacent slope-face cells that are not road approach transition strips
- slope-face cells whose source is an intersection slope-face loop or slope-face surface-zone contract

Ordinary `Slope Face Surface` owns:

- non-intersection corridor side-slope strips outside the intersection transition window

## Implementation Phases

### Phase 1 - Remove Ambiguous Fill Logic

Keep the already accepted cleanup:

- remove broad internal cap generation
- remove Cross `intersection_adjacent_pair` generation when it creates non-adjacent patches
- keep only traceable Applied Section window candidates

Acceptance criteria:

- no synthetic fan/cap panels are created for Cross Tie Slope
- diagnostics identify rejected candidates instead of silently filling them

### Phase 2 - Add Tie Slope Gap Ownership Audit

Before generating new panels, classify every remaining Cross transition gap.

Required classes:

- `tie_slope_candidate`
- `intersection_slope_face_candidate`
- `ordinary_slope_face_candidate`
- `intersection_surface_candidate`
- `unowned_gap`

Acceptance criteria:

- the audit reports which gap class is responsible
- Cross gaps near the rectangular supplemental Applied Section corners are classified as `tie_slope_candidate`
- curb-return interior cells are not classified as Tie Slope

Progress:

- 2026-07-06: Added `ownership_class` and `ownership_notes` to Applied Section Tie Slope window rows.
- 2026-07-06: Exposed `ownership=` counts in the `intersection_tie_slope_window` Intersections row notes.
- 2026-07-06: Exposed `IntersectionTieSlopeWindowOwnershipSummary` on the preview object for smoke/manual QA.

### Phase 3 - Build Cross Tie Slope From Adjacent Applied Section Pairs

Generate Cross Tie Slope only from adjacent Applied Section pairs.

For each participating road and side:

- find the first/last ordinary Applied Section adjacent to the intersection window
- find ordered intersection supplemental Applied Sections for the same alignment or leg
- connect only adjacent side-slope boundary edges
- stop at the innermost valid supplemental edge that reaches the rectangular corner target
- reject non-adjacent spans

Acceptance criteria:

- primary and secondary roads both receive Tie Slope transition panels
- generated panels follow Applied Section ordering
- no panel bridges across the central intersection surface

Progress:

- 2026-07-06: Gated visible Tie Slope surface generation by `ownership_class=tie_slope_candidate`.
- 2026-07-06: Gated Tie Slope shared breakline emission by the same ownership class.
- 2026-07-06: Added Cross smoke coverage that accepted `curb_return_approach_pair` rows are owned by `Intersection Tie Slope`.
- 2026-07-06: Exposed accepted supplemental endpoint window counts by road role so primary/secondary coverage can be verified before further geometry expansion.
- 2026-07-06: Restored the Cross Tie Slope geometry path to adjacent Applied Section pairs only; rejected full-edge expansion as an ineffective geometry experiment.
- 2026-07-07: Reverted the explicit Applied Section side-slope edge experiment. T and Cross Tie Slope windows both use the restored legacy window edge path while the next Cross strategy is reconsidered.

### Phase 4 - Shared Breakline Registration

Register the generated Tie Slope panel edges as shared breaklines.

Required consumers:

- `intersection_tie_slope_surface`
- adjacent ordinary `slope_face_surface`, where applicable
- adjacent `intersection_slope_face_surface`, where applicable
- adjacent design/intersection surface boundary, only when the source role proves the shared boundary

Acceptance criteria:

- Breakline Audit reports no geometry mismatch or missing consumer for accepted Tie Slope windows
- warning notes are limited to known ownership warnings, not geometric drift

### Phase 5 - Presentation And QA

Expose the result without using preview geometry as source truth.

Required presentation:

- Results row for `Intersection Tie Slope Surface`
- Visibility toggle for `Intersection Tie Slope Surface`
- diagnostics for rejected Cross Tie Slope candidates
- optional highlight for candidate windows, clearly marked as presentation only

Manual QA:

- T intersection remains unchanged
- Cross intersection has Tie Slope on primary and secondary roads
- Tie Slope reaches the intended rectangular supplemental Applied Section corner targets
- no broad triangular fan panels appear away from the intersection
- no generated object appears at unrelated Alignment coordinates

## Rejected Approaches

Do not restore these approaches:

- direct curb-return arc to road-edge fan fill
- broad internal rectangular cap consumption
- mesh-based gap patching
- preview/highlight object reuse as geometry source
- non-adjacent Applied Section connection
- mixing ordinary `Slope Face Surface` and dedicated intersection surfaces

## Diagnostics

The build should emit explicit notes for:

- missing side-slope edge rows
- mismatched alignment or leg ownership
- side mismatch
- non-adjacent Applied Section pair rejection
- candidate skipped because it belongs to `Intersection Slope Face Surface`
- candidate skipped because it would enter central pavement/intersection surface ownership
- candidate skipped because no shared breakline consumer can be assigned

## Completion Criteria

The work is complete when:

- Cross Tie Slope is generated from Applied Section context, not from generated meshes
- primary and secondary road approach bands are handled with the same rule
- rectangular supplemental Applied Section corner targets are reached where valid
- curb-return interior and central intersection surface are not filled by Tie Slope
- Breakline Audit remains ready or emits actionable source diagnostics
- FreeCADCmd smoke tests pass for T and Cross intersections
