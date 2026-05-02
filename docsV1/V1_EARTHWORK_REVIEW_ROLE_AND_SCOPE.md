# CorridorRoad V1 Earthwork Review Role and Scope

Date: 2026-04-28
Status: Draft detail plan
Depends on:

- `docsV1/V1_REVIEW_VIEWER_ROLE_DECISION.md`
- `docsV1/V1_EARTHWORK_REVIEW_EXECUTION_PLAN.md`
- `docsV1/V1_EARTHWORK_BALANCE_PLAN.md`
- `docsV1/V1_EARTHWORK_OUTPUT_SCHEMA.md`

## 1. Purpose

This document defines the user-facing role of `Earthwork Review`.

## 2. Scope

`Earthwork Review` is the multi-station and station-range review screen for cut/fill and mass-haul results.

It answers project and corridor-range earthwork questions after corridor and surface results exist.

## 3. Core Rule

`Earthwork Review` verifies earthwork balance across many stations and ranges.

It does not replace station-level 2D section review.

It does not replace profile, alignment, assembly, region, or corridor source editors.

## 4. Main User Questions

The viewer should answer:

- What is the total cut and fill state?
- Which station ranges are surplus zones?
- Which station ranges are deficit zones?
- Where are the balance points?
- How does cumulative mass-haul change along the corridor?
- Which local station or range should be inspected in `Cross Section Viewer`?
- Which profile or alignment range should be inspected in `Plan/Profile Viewer`?

## 5. Required Inputs

Minimum inputs:

- `EarthworkBalanceOutput`
- `MassHaulOutput`
- station range rows
- cut/fill summary rows
- balance ratio rows
- diagnostic rows

High-value inputs:

- corridor surface references
- design-vs-existing ground comparison rows
- section-level cut/fill area rows
- haul-zone rows
- borrow/waste hints
- selected station or selected earthwork window context

## 6. UI Layout

Recommended layout:

1. Project-level cut/fill summary
2. Station range / balance window table
3. Mass-haul summary or graph
4. Focused station/range context
5. Handoff buttons to `Cross Section Viewer` and `Plan/Profile Viewer`
6. Diagnostics and missing-input guidance

## 7. What It Should Show

It should show:

- total cut
- total fill
- net balance
- balance ratio
- surplus ranges
- deficit ranges
- mass-haul cumulative values
- nearest section review station
- handoff context for station/range inspection

## 8. What It Should Not Try To Do

It should not become:

- the main 2D station section viewer
- the profile editor
- the corridor builder
- a direct surface geometry editor
- a final drawing-sheet generator

## 9. User Actions

Required first actions:

- select an earthwork window
- focus a station or station range
- inspect cut/fill and mass-haul summary
- open `Cross Section Viewer` for local section explanation
- open `Plan/Profile Viewer` for profile/alignment context

Deferred actions:

- optimization recommendations
- borrow/waste site management
- construction staging scenarios
- AI earthwork advice

## 10. Diagnostics

Diagnostics should explain:

- corridor build missing
- existing ground surface missing
- design surface missing
- section area rows missing
- no station range rows
- mass-haul unavailable
- stale result state after source edits

## 11. Relationship to Other Review Screens

`Earthwork Review` owns multi-station and range-based cut/fill review.

`Cross Section Viewer` owns local station 2D section explanation.

`Plan/Profile Viewer` owns alignment, stationing, profile, EG/FG continuity review.

Normal handoff:

- from `Earthwork Review` to `Cross Section Viewer` when the user asks why a range has cut/fill
- from `Earthwork Review` to `Plan/Profile Viewer` when the user asks whether profile or stationing explains the trend

## 12. Implementation Milestones

1. Make the title and summary explicitly say cut/fill and mass-haul review.
2. Keep project-level totals visible at the top.
3. Add station-range focus as the primary table interaction.
4. Preserve selected range when opening `Cross Section Viewer`.
5. Preserve selected range when opening `Plan/Profile Viewer`.
6. Add empty states for missing corridor, EG, FG, or section area data.
7. Validate with corridor surface and section-area results from a real document.
