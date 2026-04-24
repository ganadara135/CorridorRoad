# CorridorRoad V1 Review Stage Split Plan

Date: 2026-04-23
Branch: `v1-dev`
Status: Draft baseline
Depends on:

- `docsV1/V1_MASTER_PLAN.md`
- `docsV1/V1_UX_RESET_PLAN.md`
- `docsV1/V1_ACTION_LABEL_RESET_PLAN.md`

## 1. Purpose

This document defines the stage split between:

- `Review Alignment`
- `Review Plan/Profile`
- `Review Cross Sections`
- `Review Earthwork`

It exists to prevent users from being pushed into later-stage review surfaces before the necessary design data exists.

## 2. Problem Statement

Without an explicit stage split, the UX becomes confusing:

- saving alignment can appear to open plan/profile review unexpectedly
- plan/profile review can appear before stationing exists
- cross-section review can appear before corridor results exist
- earthwork review can appear before cut/fill analysis exists

This makes the workflow feel internally routed rather than intentionally staged.

## 3. Stage Rule

Each review surface must belong to one primary design stage.

### 3.1 Review Alignment

Stage:

- `Alignment`

Prerequisites:

- active project
- one alignment object or one alignment draft context

Not required:

- stationing
- profile
- corridor
- earthwork

Purpose:

- verify horizontal geometry only
- inspect geometry element count and diagnostics
- confirm alignment source status
- direct user toward `Generate Stations`

### 3.2 Review Plan/Profile

Stage:

- `Stations & Profile`

Prerequisites:

- stationing exists
- plan station context exists
- optional existing-ground and finished-grade profile context

Purpose:

- inspect station-focused plan/profile outputs
- inspect profile control rows
- inspect grade or curve changes
- direct user toward assemblies/regions once profile work is ready

### 3.3 Review Cross Sections

Stage:

- `Corridor Review`

Prerequisites:

- section set or corridor-derived section context exists
- corridor build or section result context exists

Purpose:

- inspect section ownership
- inspect terrain and structure interaction
- inspect station-by-station section results

### 3.4 Review Earthwork

Stage:

- `Analytical Review`

Prerequisites:

- cut/fill or earthwork result context exists

Purpose:

- inspect cut/fill balance
- inspect earthwork windows and haul context
- inspect borrow/waste signals

## 4. Do Not Auto-Jump Rule

One stage must not silently jump the user into another stage’s main review surface.

Examples:

- `Alignment` apply must not silently behave like `Plan/Profile Review`
- `Stations` generation must not silently behave like `Cross Section Review`
- `Corridor` build must not silently behave like `Earthwork Review`

If a later-stage review surface is unavailable, the UI should:

- explain the missing prerequisite
- offer the next valid action

## 5. Alignment Review Definition

`Review Alignment` is not a reduced `Plan/Profile Viewer`.

It is its own review concept.

Minimum content:

- alignment identity
- alignment geometry summary
- geometry element rows
- design criteria or diagnostic rows where available
- coordinate/source context
- next-step guidance: `Generate Stations`

Minimum prohibited assumptions:

- do not assume stationing exists
- do not assume profile exists
- do not assume cut/fill exists

## 6. Plan/Profile Review Definition

`Review Plan/Profile` starts only when stationing/profile context exists.

If stationing does not exist yet, the UI should not fake a full plan/profile review.

Instead it should:

- block the command with a clear message
- or show an explicit empty-state panel with:
  - `Stations not generated yet`
  - `Next: Generate Stations`

## 7. Empty-State Rule

Each review surface should have a proper empty state.

### 7.1 Review Alignment empty state

Show:

- `No alignment defined yet`
- `Next: Create or import an alignment`

### 7.2 Review Plan/Profile empty state

Show:

- `Stations not generated yet`
- `No profile controls yet`
- `Next: Generate Stations`

### 7.3 Review Cross Sections empty state

Show:

- `No section results yet`
- `Corridor build required`
- `Next: Build Corridor`

### 7.4 Review Earthwork empty state

Show:

- `No earthwork results yet`
- `Next: Run Earthwork Analysis`

## 8. Command Mapping Rule

Recommended top-level mapping:

- `Review Alignment` -> alignment-stage review
- `Review Plan/Profile` -> stationing/profile-stage review
- `Review Cross Sections` -> section/corridor-stage review
- `Review Earthwork` -> analytical-stage review

No command should attempt to “guess a better later viewer” if its own stage prerequisites are missing.

## 9. Current Implementation Implication

Short term:

- existing plan/profile viewer code may still be reused as implementation support
- but the user-facing command behavior must follow the stage split

Meaning:

- `Edit Alignment` should not expose a direct action that behaves like later-stage plan/profile review
- if reused internally, the reused viewer must be wrapped as `Review Alignment` with alignment-only semantics

## 10. UX Consequences

This stage split changes the button model.

Examples:

- `Alignment` screen:
  - `Apply`
  - `Review Alignment`
  - `Next: Generate Stations`
- `Stations & Profile` screen:
  - `Generate Stations`
  - `Apply`
  - `Review Plan/Profile`
- `Corridor` screen:
  - `Build Corridor`
  - `Review Cross Sections`
  - `Review Earthwork` only when applicable

## 11. Implementation Order

1. define `Review Alignment` as a separate user concept
2. stop routing alignment-stage buttons into full plan/profile review wording
3. add prerequisite checks and empty states to main review commands
4. update command labels and tooltips
5. update workflow docs and toolbar grouping

## 12. Acceptance Criteria

This stage split is successful when:

- users can tell which stage they are in
- alignment review no longer feels like hidden plan/profile review
- missing prerequisites are explicit
- no review command silently skips to a later-stage mental model

## 13. Final Rule

Review surfaces should follow design readiness, not implementation convenience.

If a user has not created the prerequisite data yet, the UX must explain that clearly rather than rerouting them into a different stage.
