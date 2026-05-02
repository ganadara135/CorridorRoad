# CorridorRoad V1 Review Workflow Stage Map

Date: 2026-04-28
Status: Draft detail plan
Depends on:

- `docsV1/V1_REVIEW_VIEWER_ROLE_DECISION.md`
- `docsV1/V1_UX_RESET_PLAN.md`
- `docsV1/V1_IMPLEMENTATION_PHASE_PLAN.md`

## 1. Purpose

This document maps each v1 review surface to its stage in the road design workflow.

## 2. Core Rule

Each review surface should answer a distinct user question.

No review screen should become a generic dumping ground for every table.

## 3. Stage Map

| Stage | Primary Command | Review Surface | User Question |
| --- | --- | --- | --- |
| Terrain | `TIN` | TIN review inside `TIN` | Is the existing ground TIN valid? |
| Alignment | `Alignment` | `Review Alignment` | Is horizontal geometry valid? |
| Stationing | `Stations` | Stations panel / Plan/Profile readiness | Are stations generated and mapped to XY? |
| Profile | `Profile` | `Plan/Profile Viewer` | Do Alignment, Stations, Profile, EG, and FG connect? |
| Assembly / Region | `Assembly`, `Regions` | Section readiness / source diagnostics | Which section rules apply by station? |
| Applied Sections | `Applied Sections` | Cross Section Viewer | What does this station's section look like? |
| Corridor Build | `Build Corridor` | Cross Section Viewer + 3D review | Did corridor surfaces build correctly? |
| Earthwork | `Earthwork Review` | Earthwork Viewer | What are cut/fill, balance, and mass-haul implications across stations and ranges? |
| Output | `Outputs & Exchange` | Output review / sheets | What can be exported or delivered? |

## 4. Viewer Ownership

`Plan/Profile Viewer` owns continuity review.

`Cross Section Viewer` owns station 2D section review.

`Earthwork Viewer` owns multi-station and station-range cut/fill, balance, and mass-haul review.

`TIN` owns terrain validity and edit operation review.

## 5. Recommended Handoff Direction

Normal flow:

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

Backward handoff:

- `Plan/Profile Viewer` may open `Alignment`, `Stations`, or `Profile`.
- `Cross Section Viewer` may open `Assembly`, `Regions`, or structure/drainage editors.
- `Earthwork Viewer` may open `Cross Section Viewer` or `Plan/Profile Viewer`.

Earthwork handoff rule:

- open `Cross Section Viewer` when the user needs local 2D station explanation
- open `Plan/Profile Viewer` when the user needs alignment, stationing, profile, or EG/FG continuity context

## 6. Empty State Rule

When a review screen opens too early, it should say which prior stage is missing.

Examples:

- `Plan/Profile Viewer`: Stations missing.
- `Cross Section Viewer`: Applied Sections missing.
- `Earthwork Viewer`: Corridor or earthwork result missing.

## 7. Non-Goals

This map does not define final drawing sheets.

This map does not define every toolbar label.

This map does not authorize review screens to edit generated output geometry.

## 8. Implementation Use

Use this map when deciding:

- where a new table belongs
- which command should expose a user action
- whether a review feature is stage-appropriate
- whether a screen is becoming too broad
