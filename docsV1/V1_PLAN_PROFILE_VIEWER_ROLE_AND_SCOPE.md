# CorridorRoad V1 Plan/Profile Viewer Role and Scope

Date: 2026-04-28
Status: Draft detail plan
Depends on:

- `docsV1/V1_REVIEW_VIEWER_ROLE_DECISION.md`
- `docsV1/V1_PLAN_PROFILE_REVIEW_EXECUTION_PLAN.md`
- `docsV1/V1_PLAN_OUTPUT_SCHEMA.md`
- `docsV1/V1_PROFILE_OUTPUT_SCHEMA.md`

## 1. Purpose

This document defines what `Plan/Profile Viewer` is for after the review viewer role split.

## 2. Scope

`Plan/Profile Viewer` is a continuity and readiness review screen.

It sits between profile authoring and detailed section/corridor review.

## 3. Core Rule

`Plan/Profile Viewer` verifies that Alignment, Stations, Profile, and EG/FG references are connected correctly.

It does not replace the detailed 2D `Cross Section Viewer`.

## 4. Main User Questions

The viewer should answer:

- Does the selected Alignment have stationing?
- Do station rows map to valid XY positions?
- Does the Profile cover the station range?
- Are EG samples available from the selected TIN?
- Are FG profile values evaluated at review stations?
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
- EG TIN sampling rows
- profile vertical curve evaluation rows
- Review Readiness rows
- alignment frame rows

## 6. UI Layout

Recommended layout:

1. Review Readiness summary
2. Focused station context
3. Station interval and navigation controls
4. Evaluation tabs
5. Source handoff buttons

Evaluation tabs:

- Alignment / Stationing
- Profile / FG
- EG Reference
- Diagnostics

## 7. What It Should Show

It should show:

- station count and station interval
- alignment range and active station frame
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
- EG TIN not selected
- EG no-hit rows
- fallback/demo preview source

## 11. Implementation Milestones

1. Make the title and help text explicitly say continuity/readiness review.
2. Group tables by Alignment, Profile, EG Reference, and Diagnostics.
3. Keep Review Readiness at the top.
4. Clarify when the viewer is using fallback/demo data.
5. Add `Open Stations` handoff if missing from the current UI.
6. Validate the flow before entering Cross Section Viewer.
