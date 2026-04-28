# CorridorRoad V1 Review Viewer Role Decision

Date: 2026-04-28
Status: Active direction
Depends on:

- `docsV1/V1_MASTER_PLAN.md`
- `docsV1/V1_VIEWER_PLAN.md`
- `docsV1/V1_REVIEW_STAGE_SPLIT_PLAN.md`
- `docsV1/V1_PLAN_PROFILE_REVIEW_EXECUTION_PLAN.md`
- `docsV1/V1_CROSS_SECTION_VIEWER_EXECUTION_PLAN.md`

## 1. Purpose

This document fixes the product role split between `Plan/Profile Viewer`, `Cross Section Viewer`, and `Earthwork Review`.

It exists because the early v1 review work added useful review tables, diagnostics, and handoff behavior, but the user-facing purpose of each viewer must remain clear.

## 2. Core Decision

`Cross Section Viewer` is the primary station-by-station 2D section review screen.

`Plan/Profile Viewer` is the upstream alignment, stationing, and profile continuity review screen.

`Earthwork Review` is the multi-station and station-range cut/fill review screen.

The review screens should not compete for the same user job.

## 3. Cross Section Viewer Role

`Cross Section Viewer` answers:

- What does the road section look like at this station?
- Are FG, EG, pavement layers, subgrade, ditch, side slope, drainage, and structure context correct here?
- Does the section match the active Assembly and Region policy?
- What cut/fill or earthwork hint applies at this station?
- Which source editor should be opened to change this section result?

The center of the UI should be a large 2D section drawing.

Tables and diagnostics are supporting information, not the main experience.

## 4. Cross Section Viewer UI Direction

Recommended layout:

1. Top navigation bar
2. Large central 2D section canvas
3. Compact station context summary
4. Supporting tabs or collapsible panels

The 2D section canvas should show, when available:

- existing ground line
- finished grade line
- pavement and subgrade layers
- side slopes / slope faces
- ditches and drainage shapes
- structures or structure influence zones
- offset and elevation axes
- station label and scale hints

Supporting tabs may include:

- Components
- Terrain
- Corridor Results
- Quantities / Earthwork
- Diagnostics
- Source / Handoff

## 5. Plan/Profile Viewer Role

`Plan/Profile Viewer` answers:

- Does Alignment connect correctly to Stations?
- Does Profile connect correctly to the same station domain?
- Are EG and FG profile references available and sampled correctly?
- Are station intervals, key stations, and focused station context understandable?
- Are alignment/profile source links valid before section and corridor review?

It is not the main detailed section review screen.

It should be treated as a continuity and readiness review between `Profile` and `Cross Section Viewer`.

## 6. Plan/Profile Viewer UI Direction

Recommended layout:

1. Readiness and source-link summary
2. Focused station and station interval controls
3. Alignment/profile continuity tables
4. Profile line and EG/FG sampling diagnostics
5. Handoff to `Alignment`, `Stations`, and `Profile`

It may show profile graphics, but it should not try to replace:

- detailed 2D cross-section review
- profile sheet output
- corridor surface review

## 7. Earthwork Review Role

`Earthwork Review` answers:

- What are total cut and fill quantities?
- Which station ranges are surplus or deficit zones?
- Where are the balance points?
- How does cumulative mass-haul change along the corridor?
- Which station or range should be opened in `Cross Section Viewer` for local explanation?
- Which station or range should be opened in `Plan/Profile Viewer` for alignment/profile context?

It is not the main detailed section review screen.

It should be treated as the multi-station and station-range earthwork result review screen after corridor and surface results exist.

## 8. Earthwork Review UI Direction

Recommended layout:

1. Project-level cut/fill summary
2. Station range / balance window table
3. Mass-haul summary or graph
4. Focused station/range context
5. Handoff to `Cross Section Viewer` and `Plan/Profile Viewer`

It may show local station context, but it should not try to replace:

- station-by-station 2D cross-section review
- profile continuity review
- corridor source editing

## 9. Workflow Placement

Recommended user flow:

1. `TIN`
2. `Alignment`
3. `Stations`
4. `Profile`
5. `Plan/Profile Viewer`
6. `Assembly`
7. `Regions`
8. `Applied Sections`
9. `Build Corridor`
10. `Cross Section Viewer`
11. `Earthwork Review`
12. `Outputs & Exchange`

The practical rule is:

- use `Plan/Profile Viewer` before detailed section review
- use `Cross Section Viewer` after applied sections or corridor build results exist
- use `Earthwork Review` after corridor surfaces and section earthwork quantities exist

## 10. Current Implementation Gap

Current `Cross Section Viewer` has many useful data tables.

The next redesign must make the 2D section drawing the dominant screen element.

Current `Plan/Profile Viewer` has useful station, profile, and diagnostic tables.

The next refinement must make its role clearer as a readiness and continuity review screen.

Current `Earthwork Review` has useful cut/fill, mass-haul, and handoff behavior.

The next refinement must keep it focused on multi-station/range earthwork review rather than local section drawing.

## 11. Detailed Documentation Plan

Create or update detailed documents in this order:

1. `V1_CROSS_SECTION_2D_VIEWER_DESIGN.md`
2. `V1_PLAN_PROFILE_VIEWER_ROLE_AND_SCOPE.md`
3. `V1_EARTHWORK_REVIEW_ROLE_AND_SCOPE.md`
4. `V1_REVIEW_WORKFLOW_STAGE_MAP.md`

Each detailed document should include:

- Purpose
- Scope
- Main user questions
- Required inputs
- UI layout
- User actions
- Diagnostics
- Non-goals
- Implementation milestones

## 12. Non-Goals

This decision does not define final drawing sheets.

This decision does not reintroduce v0 mixed ownership.

This decision does not make review viewers edit generated geometry.

This decision does not move durable design intent out of source models.

## 13. Acceptance Criteria

The role split is accepted when:

- users can explain why they open `Plan/Profile Viewer`
- users can explain why they open `Cross Section Viewer`
- users can explain why they open `Earthwork Review`
- `Cross Section Viewer` feels like a station 2D section review screen
- `Plan/Profile Viewer` feels like a continuity/readiness review screen
- `Earthwork Review` feels like a multi-station/range cut/fill review screen
- neither viewer hides engineering logic inside presentation code
