# CorridorRoad V1 Plan/Profile Connection Review Role and Scope

Date: 2026-04-28
Status: Draft detail plan
Depends on:

- `docsV1/V1_REVIEW_VIEWER_ROLE_DECISION.md`
- `docsV1/V1_PLAN_PROFILE_REVIEW_EXECUTION_PLAN.md`
- `docsV1/V1_PLAN_PROFILE_CONNECTION_REVIEW_UX.md`
- `docsV1/V1_PLAN_OUTPUT_SCHEMA.md`
- `docsV1/V1_PROFILE_OUTPUT_SCHEMA.md`

## 1. Purpose

This document defines what `Plan/Profile Connection Review` is for after the review viewer role split.

## 2. Scope

`Plan/Profile Connection Review` is a continuity and readiness review screen.

It sits between profile authoring and detailed section/corridor review.

## 3. Core Rule

`Plan/Profile Connection Review` verifies that Alignment, Stations, Profile, and EG/FG references are connected correctly.

It does not replace the detailed 2D `Cross Section Viewer`.

`Key stations` are navigation aids only.

They are not sufficient as the main review dataset.

The main UX should be a full station-grid connection review.

## 4. Main User Questions

The viewer should answer:

- Does the selected Alignment have stationing?
- Do station rows map to valid XY positions?
- Does the Profile cover the station range?
- Are EG samples available from the selected TIN?
- Are FG profile values evaluated at review stations?
- Are FG and EG values evaluated across the full station grid, not only key stations?
- Where are station rows with alignment/profile/EG issues?
- Is the active document using real v1 objects or fallback/demo context?

## 5. Required Inputs

Minimum inputs:

- `PlanOutput`
- `ProfileOutput`
- focused station context
- alignment/profile source references
- bridge or source diagnostics

High-value inputs:

- `V1Stationing`
- full station connection rows
- EG TIN sampling rows
- profile vertical curve evaluation rows
- Review Readiness rows
- alignment frame rows

## 6. UI Layout

Recommended layout:

1. Review Readiness summary
2. Source Link Summary `[implemented]`
3. Full Station Connection Table
4. Connection Diagnostics
5. Focused station and navigation controls
6. Evaluation tabs
7. Source handoff buttons

Evaluation tabs:

- Alignment / Stationing
- Profile / FG
- EG Reference
- Issues
- Diagnostics

## 7. What It Should Show

It should show:

- station count and station interval
- alignment range and active station frame
- full station-grid connection status
- grouped connection diagnostics with next actions
- profile control coverage
- FG evaluated elevation and grade
- EG sampled elevation and no-hit status
- profile station-range fit
- source-link diagnostics

## 8. What It Should Not Try To Do

It should not become:

- the main 2D cross-section viewer
- a full profile sheet generator
- a corridor surface viewer
- an editor for generated geometry

## 9. User Actions

Required first actions:

- change station interval
- show all station rows
- show issue station rows only
- use `Quick Navigation Stations` only as shortcuts, not as the full station list
- double-click diagnostic rows to open the likely source panel
- focus another review station
- inspect alignment/profile/EG status
- open `Alignment`
- open `Stations`
- open `Profile`

Deferred actions:

- profile sheet layout
- advanced plan/profile plotting
- mass-haul integration

## 10. Diagnostics

Diagnostics should explain:

- no Alignment source
- no Stations
- no Profile source
- Profile station range mismatch
- station rows without alignment XY
- station rows without FG evaluation
- EG TIN not selected
- EG no-hit rows
- fallback/demo preview source

## 11. Implementation Milestones

1. [x] Make the title and help text explicitly say continuity/readiness review.
2. Add a full station connection table as the main review dataset.
3. Keep key stations as navigation only.
4. [x] Add Source Link Summary for Alignment, Stations, Profile, and TIN.
5. [x] Add grouped Connection Diagnostics for source links, stationing, Alignment, Profile/FG, TIN/EG, and FG-EG.
6. [x] Add diagnostic-row handoff to Alignment, Stations, Profile, and TIN source panels.
7. [x] Add `Open Stations` handoff if missing from the current UI.
8. Validate the flow before entering Cross Section Viewer.
