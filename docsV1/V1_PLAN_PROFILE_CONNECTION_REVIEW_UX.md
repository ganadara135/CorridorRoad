# CorridorRoad V1 Plan/Profile Connection Review UX

Date: 2026-04-28
Status: Draft detail plan
Depends on:

- `docsV1/V1_REVIEW_VIEWER_ROLE_DECISION.md`
- `docsV1/V1_PLAN_PROFILE_VIEWER_ROLE_AND_SCOPE.md`
- `docsV1/V1_PLAN_PROFILE_REVIEW_EXECUTION_PLAN.md`
- `docsV1/V1_PLAN_OUTPUT_SCHEMA.md`
- `docsV1/V1_PROFILE_OUTPUT_SCHEMA.md`

## 1. Purpose

This document refines the UX direction for `Plan/Profile Connection Review`.

The current viewer is too focused on `key stations`.

That is not enough to prove that Alignment, Stations, Profile, EG, and FG are correctly connected across the design range.

## 2. Core Decision

`Plan/Profile Connection Review` should be a connection review screen.

It should show whether:

- Alignment produces valid station frames
- Stations cover the intended range
- Profile covers the same station domain
- FG values evaluate at the station grid
- EG values sample correctly from TIN
- source links are real v1 document objects, not fallback/demo context

`Key stations` are navigation aids only.

They are not the main review dataset.

## 3. Main UX Problem

A compact key-station list is useful for movement, but it hides important problems:

- missing station rows between key stations
- profile range gaps
- EG no-hit zones
- sudden FG grade changes
- alignment frame errors away from selected key stations
- station interval mismatch
- source object mismatch between Alignment, Stations, and Profile

The viewer must expose the full station-grid connection state.

## 4. Primary User Questions

The viewer should answer:

- Is every station row connected to Alignment XY?
- Is every station row covered by Profile?
- Is FG evaluated at every station row?
- Is EG sampled at every station row when TIN exists?
- Where are no-hit, gap, warning, or mismatch rows?
- Are Alignment, Stations, and Profile source IDs consistent?
- Which source editor should be opened to fix the problem?

## 5. Recommended Layout

Recommended top-to-bottom layout:

1. Connection Readiness banner
2. Source Link Summary
3. Full Station Connection Table
4. Connection Diagnostics
5. Focus / Navigation controls
6. Supporting tabs
7. Source handoff buttons

## 6. Connection Readiness Banner

The top banner should summarize:

- Alignment: ready / missing / mismatch
- Stations: ready / missing / stale
- Profile: ready / missing / range mismatch
- FG Evaluation: ready / partial / failed
- EG Sampling: ready / partial / no TIN / no-hit

This is the first thing the user should see.

## 7. Source Link Summary

The viewer should show source identity clearly:

- Alignment object
- Alignment ID
- Stations object
- Station count
- Station range
- Profile object
- Profile alignment reference
- Profile station range
- EG TIN object
- preview source kind

This section should make fallback/demo mode impossible to miss.

Current implementation:

- [x] `Source Link Summary` table shows Alignment, Stations, Profile, and TIN source rows.
- [x] Each row reports object label/name when available, source ID/reference, range/count, and link status.

## 8. Full Station Connection Table

The main table should be based on the full station grid, not only key stations.

Recommended columns:

- Station
- X
- Y
- Alignment status
- FG Elevation
- FG grade
- Profile status
- EG Elevation
- EG status
- Delta FG-EG
- Notes

The table should support:

- filter all / issues only
- focus selected station
- double-click to highlight station in 3D View
- row color by status
- dark-mode readable text on colored status rows
- EG sampling aligned to the full `PlanOutput.station_rows` grid
- FG-EG delta calculation for rows where both elevations are available

## 9. Quick Navigation Stations Role

`Quick Navigation Stations` should remain, but only as a navigation shortcut.

It is not a full station list.

The full station grid belongs in the `Station Connection` table.

They should include:

- start station
- end station
- current station
- nearby stations
- issue stations

They should not be the only visible station review rows.

## 10. Connection Diagnostics

Diagnostics should be grouped by connection type:

- source link diagnostics
- station coverage diagnostics
- alignment evaluation diagnostics
- profile coverage diagnostics
- FG evaluation diagnostics
- EG sampling diagnostics

Each diagnostic row should say:

- what failed
- station or range affected
- likely source owner
- recommended next action

Current implementation:

- [x] `Connection Diagnostics` table shows separate rows for `Source Links`, `Alignment`, `Stations`, `Profile / FG`, `TIN / EG`, and `FG-EG`.
- [x] Each row reports status, finding, and next action.
- [x] TIN-missing and FG-EG-unavailable states are explicit instead of hidden inside raw bridge diagnostics.
- [x] Diagnostic rows can be double-clicked to open the most relevant source panel.

## 11. Supporting Tabs

Supporting tabs should not hide the main connection table.

Recommended tabs:

- Alignment / Stations
- Profile / FG
- EG Reference
- Issues
- Handoff

## 12. User Actions

Required actions:

- refresh/rebuild review
- change station interval
- show all rows
- show issue rows only
- focus selected station
- open `Alignment`
- open `Stations`
- open `Profile`

Deferred actions:

- full profile graph editing
- final profile sheet plotting
- earthwork optimization
- corridor surface editing

## 13. Empty States

The viewer should explain missing prerequisites:

- No Alignment: create or select Alignment.
- No Stations: open Stations and apply stationing.
- No Profile: open Profile and apply profile rows.
- No EG TIN: select or build TIN if EG review is required.
- Demo/fallback mode: active document v1 objects were not resolved.

## 14. Implementation Milestones

1. [x] Add `Open Stations` handoff.
2. [x] Add a full station connection table.
3. [x] Add issue-only filtering.
4. [x] Add row status coloring.
5. [x] Add full-station EG/FG sampling rows.
6. [x] Add source link summary for Alignment, Stations, Profile, and TIN.
7. [x] Add grouped connection diagnostics by source/evaluation area.
8. [x] Add diagnostic-row handoff to source panels.
9. [x] Rename key-station navigation UI to `Quick Navigation Stations`.
10. [x] Rename UX text to emphasize connection review.
11. Validate with a real TIN + Alignment, Stations, Profile, and TIN document.

## 15. Non-Goals

This viewer does not replace `Cross Section Viewer`.

This viewer does not edit Alignment, Stations, or Profile source rows directly.

This viewer does not generate profile sheets.

This viewer does not build corridor surfaces.
