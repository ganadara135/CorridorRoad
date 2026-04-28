# CorridorRoad V1 Earthwork Review Execution Plan

Date: 2026-04-23
Branch: `v1-dev`
Status: Draft baseline, mass-haul practical review and review handoff slices complete
Depends on:

- `docsV1/V1_MASTER_PLAN.md`
- `docsV1/V1_UX_RESET_PLAN.md`
- `docsV1/V1_REVIEW_STAGE_SPLIT_PLAN.md`
- `docsV1/V1_EARTHWORK_BALANCE_PLAN.md`
- `docsV1/V1_EARTHWORK_OUTPUT_SCHEMA.md`
- `docsV1/V1_IMPLEMENTATION_PHASE_PLAN.md`
- `docsV1/V1_REVIEW_VIEWER_ROLE_DECISION.md`
- `docsV1/V1_EARTHWORK_REVIEW_ROLE_AND_SCOPE.md`

## 1. Purpose

This document defines how `Earthwork Review` should become a v1-native review surface rather than remain only an analytical backend or temporary preview.

It exists to define:

- what the review screen is responsible for
- how it should consume `EarthworkBalanceOutput` and `MassHaulOutput`
- how it should connect to section and profile review workflows
- what implementation milestones are needed before it becomes the preferred earthwork review path

## 2. Product Goal

The goal is to create one coherent earthwork review surface that helps users inspect:

- total cut/fill state
- cut/fill aggregation across many stations and station ranges
- surplus and deficit zones
- balance ratio
- cumulative mass-haul behavior
- borrow and waste needs
- station-focused local context

This review screen should become the preferred place to inspect earthwork results after corridor rebuild.

## 3. Definition of Promotion

`Earthwork Review` is considered promoted when:

- users can open a dedicated v1 earthwork review panel directly
- the panel consumes normalized `EarthworkBalanceOutput` and `MassHaulOutput`
- users can move between project-level summary and station-level context
- ordinary earthwork review no longer depends on ad-hoc old dialogs or one-off summaries

## 4. Relationship to Other UI

`Earthwork Review` is:

- a review surface
- a comparison surface
- a diagnostic surface

It is not:

- the source editor for profile or section geometry
- the optimization engine itself
- a replacement for drawing sheets

Practical relationship:

- source edits still happen in alignment, profile, region, template, or structure editors
- `Earthwork Review` becomes the preferred place to inspect their earthwork consequences

## 5. Scope of the First Promoted Review UI

The first promoted v1 earthwork review screen should include:

- overview summary block
- balance summary rows
- zone list
- mass-haul curve summary
- balance-point list
- haul-zone list
- focused station or focused window context
- handoff links to `Plan/Profile Review` and `Cross Section Viewer`
- visible stale/current state

It does not yet need:

- full optimization UI
- full candidate-comparison dashboard
- full AI recommendation workflow
- final drawing-sheet integration

## 6. Minimum Functional Milestones

### 6.1 Milestone A: Stable review shell

Required outcomes:

- earthwork review command opens reliably
- `EarthworkBalanceOutput` summary renders clearly
- `MassHaulOutput` summary renders clearly

Completion signal:

- users can inspect earthwork results without reading raw result objects

### 6.2 Milestone B: Station and zone focus

Required outcomes:

- focused station can be shown
- focused balance window can be shown
- focused haul zone can be shown
- local cut/fill state is readable

Completion signal:

- a user can connect project-level balance numbers to a local corridor location

### 6.3 Milestone C: Linked review workflow

Required outcomes:

- jump from earthwork review to `Cross Section Viewer`
- jump from earthwork review to `Plan/Profile Review`
- preserve station or window context where practical

Completion signal:

- users can move from "what is imbalanced" to "where and why" without manual re-navigation

### 6.4 Milestone D: Review-quality improvements

Required outcomes:

- surplus/deficit zones are distinguishable
- balance points are visible
- borrow/waste summaries are clear
- diagnostics are visible when outputs are partial or degraded

Completion signal:

- the review screen supports real engineering interpretation, not just total-volume reporting

### 6.5 Milestone E: Preferred review path switch

Required outcomes:

- documentation and workflow favor the v1 earthwork review screen first
- earthwork preview bridges remain only as temporary support

Completion signal:

- ordinary earthwork review can be done in the v1 screen without relying on old review behavior

## 7. Data Contract Requirements

The promoted review screen must rely on:

- `EarthworkBalanceOutput`
- `MassHaulOutput`
- `summary_rows`
- `balance_rows`
- `zone_rows`
- `curve_rows`
- `balance_point_rows`
- `haul_zone_rows`
- optional `comparison_rows`
- optional `diagnostic_rows`

It must not rely on:

- recomputing cut/fill inside the UI
- hidden profile parsing inside the review panel
- raw display geometry as the primary earthwork source

## 8. UI Requirements

Recommended first layout:

- top overview block
- balance table
- zone table
- mass-haul summary area
- balance-point / haul-zone table
- focused context block
- handoff button row

The UI should visibly present:

- total cut
- total fill
- usable cut where available
- borrow / waste
- balance ratio
- final cumulative mass
- max surplus and max deficit cumulative mass
- mass-curve station/value rows
- focused station or focused window
- stale/current status

## 9. Command Strategy

During transition:

- keep the v1 earthwork review command as a standalone entry
- keep bridge entry from section or profile review where useful
- use the v1 review screen as the preferred post-build earthwork inspection target
- route the main `Cut-Fill Calc` review command to the v1 earthwork viewer first
- keep the existing v0 cut/fill panel as a fallback-only continuity path

Longer term:

- the main earthwork review command should resolve directly to the v1 review screen

## 10. Relationship to Cross Section and Profile Review

`Earthwork Review` should not stay isolated.

It should connect to:

- `Cross Section Viewer` for local section explanation
- `Plan/Profile Review` for linear cause review

Expected interaction pattern:

1. identify imbalance in earthwork review
2. jump to affected station/window
3. inspect geometry and source context in section or plan/profile review
4. hand off to a source editor if a change is needed

## 11. Testing and Validation

The promoted review screen should be validated through:

- contract tests for earthwork preview payloads
- focused station/window tests
- mass-haul summary tests
- handoff tests to section and profile review
- manual testing with a real document

Current implementation status:

- [x] Earthwork Review summary reports total cut/fill and mass-haul curve count
- [x] mass-haul output summary includes final cumulative mass and max surplus/deficit cumulative mass
- [x] Earthwork Review shows a mass-curve station/cumulative-mass table
- [x] `MassHaulService` interpolates balance point station values where cumulative mass crosses zero inside a window
- [x] Earthwork Review can hand off selected station/window context to Cross Section Viewer
- [x] Cross Section Viewer can display earthwork window, cut/fill, and haul-zone context from the handoff payload
- [x] Earthwork Review can hand off selected station/window context to Plan/Profile Review for linear-cause review
- [x] Plan/Profile Review can display earthwork window, cut/fill, and haul-zone context from the handoff payload

Minimum manual scenarios:

1. open earthwork review after corridor rebuild
2. inspect total cut/fill and balance ratio
3. select or focus a deficit zone
4. jump to cross section review
5. return and jump to plan/profile review
6. confirm station/window context stays understandable

## 12. Acceptance Criteria for Promotion

The v1 earthwork review screen is ready to become the preferred review path when:

- it opens reliably on real documents
- project-level and local earthwork context are both visible
- mass-haul interpretation is readable
- handoff to section and profile review works
- the screen remains output-driven and read-only
- ordinary earthwork review no longer depends on old summary paths

## 13. Non-Goals

Do not block promotion on:

- full optimization workflow
- full AI recommendation flow
- full drawing-sheet integration
- final 3D mass-haul visualization
- full multi-scenario dashboard

## 14. Final Rule

`Earthwork Review` should become the normal place to inspect cut/fill balance and mass-haul behavior after rebuild.

If the team must choose between preserving old ad-hoc summaries and strengthening normalized v1 earthwork review, the v1 review path should win.
