# Parametric Road V1 3D Centerline Toolbar Plan

Date: 2026-05-14
Status: Draft implementation plan
Scope: promote 3D Centerline review into an independent toolbar stage after `Review Plan/Profile`

Depends on:

- `docsV1/V1_MASTER_PLAN.md`
- `docsV1/V1_ALIGNMENT_MODEL.md`
- `docsV1/V1_PROFILE_MODEL.md`
- `docsV1/V1_PLAN_PROFILE_CONNECTION_REVIEW_UX.md`
- `docsV1/V1_3D_REVIEW_DISPLAY_PLAN.md`
- `docsV1/V1_STRUCTURE_GEOMETRY_CONTRACT.md`
- `docsV1/V1_DRAINAGE_FLOW_ROUTE_IMPLEMENTATION_PLAN.md`
- `docsV1/V1_CENTERLINE_OWNERSHIP_CONSOLIDATION_PLAN.md`

## 1. Purpose

`3D Centerline` should become a separate toolbar stage after `Review Plan/Profile`.

The goal is to make the evaluated 3D baseline visible before downstream source stages consume it.

Structures, Drainage, Applied Sections, Build Corridor, and Watertight Solids all need a common station/offset/elevation frame.

This stage makes that frame reviewable instead of hiding it inside Build Corridor.

## 2. Scope

This plan covers:

- toolbar placement
- command and output-object responsibilities
- source/result boundaries
- UI behavior
- implementation order
- acceptance criteria

This plan does not implement:

- direct editing of alignment or profile geometry
- manual editing of generated 3D centerline vertices
- replacement of `Review Plan/Profile`
- replacement of Build Corridor guided review

## 3. Core Rule

`3D Centerline` is a read-only review and handoff stage.

It is derived from accepted source contracts:

- `AlignmentModel`
- `ProfileModel`
- `V1Stationing`
- optional terrain/profile context where already available

It must not become a hidden source model.

## 4. Toolbar Position

Recommended toolbar order:

```text
Project
-> TIN
-> Alignment
-> Stations
-> Profile
-> Review Plan/Profile
-> 3D Centerline
-> Assembly
-> Regions
-> Structures
-> Drainage
-> Applied Sections
-> Build Corridor
-> Review
-> Outputs & Exchange
-> AI Assist
-> Watertight Solids
```

## 5. Why It Belongs Before Structures And Drainage

Structures need to place source rows, native bodies, and connection points against a stable station/offset/elevation frame.

Drainage needs the same frame for:

- ditch element station ranges
- inlet and outlet structure context
- pipeline endpoint resolution
- Flow Route 3D review

If the 3D Centerline is only visible inside Build Corridor, users discover baseline problems too late.

## 6. Object Boundary

### 6.1 Source

Source ownership remains in:

- Alignment
- Profile
- Stationing

### 6.2 Result

The 3D Centerline result should be a generated review/result contract.

Recommended result contract name:

- `Centerline3DResult`

Recommended row family:

- `Centerline3DPointRow`

Expected row fields:

| Field | Meaning |
|---|---|
| `station` | evaluated station |
| `x` | model-space X |
| `y` | model-space Y |
| `z` | profile elevation |
| `grade` | optional local grade |
| `source_alignment_ref` | alignment source ref |
| `source_profile_ref` | profile source ref |
| `source_station_ref` | stationing row/source ref |
| `diagnostic_refs` | validation and sampling diagnostics |

### 6.3 Output / Presentation

Recommended persisted review object:

- `V1Centerline3DReview`

Recommended 3D preview object:

- `V1Centerline3DPreview`

The preview object may contain a Part wire/polyline or a smooth display curve and station markers.

The display curve is presentation-only. Station/frame calculations continue to use `Centerline3DResult` point rows and the shared frame lookup service.

It is an output/presentation object, not editable source.

## 7. UI Plan

The `3D Centerline` panel should show:

- prerequisite status for Alignment, Profile, and Stationing
- sampled point count
- station range
- elevation range
- display mode: `Smooth Curve` or `Polyline`
- geometry status
- diagnostics
- buttons: `Show`, `Hide`, `Focus`, `Apply`, `Close`

Optional later controls:

- station marker interval
- key-station-only marker mode
- show tangent/normal/binormal frame glyphs
- show structure/drainage consumer readiness

## 8. Build Corridor Relationship

Build Corridor may keep a guided review row named `3D Centerline`, but it should consume or reference the same generated review/output contract where practical.

The long-term target is:

- `3D Centerline` toolbar builds/reviews the baseline result
- `Build Corridor` verifies that the baseline result exists or can be regenerated
- downstream review rows do not duplicate centerline generation logic

## 9. Structures Relationship

Structures should use the 3D Centerline frame for:

- preview placement
- native body placement
- connection point 3D review
- station/offset pick feedback

Structures should still store source rows as station/offset/elevation intent.

They should not store generated centerline vertices as source.

## 10. Drainage Relationship

Drainage should use the 3D Centerline frame for:

- pipeline candidate geometry
- element station-range review
- Flow Route preview
- inlet/outlet connection context

Drainage source rows still own drainage intent.

Pipeline geometry remains result/output.

## 11. Implementation Plan

| Step | Status | Work |
|---|---|---|
| 1 | Done | Record this implementation plan and add it to `docsV1/README.md`. |
| 2 | Done | Update master workflow wording so `3D Centerline` is a first-class review stage after `Review Plan/Profile`. |
| 3 | Done | Add `Centerline3DResult` dataclasses under `models/result`. |
| 4 | Done | Add a centerline evaluation service that samples Alignment + Profile over `V1Stationing`. |
| 5 | Done | Add `V1Centerline3DReview` or equivalent persisted output object. |
| 6 | Done | Add a `3D Centerline` command and task panel. |
| 7 | Done | Add toolbar/menu registration immediately after `Review Plan/Profile`. |
| 8 | Done | Route preview/review objects under the v1 project tree review/output group. |
| 9 | Done | Reuse the result in Structures preview and connection point preview where practical. |
| 10 | Done | Reuse the result in Drainage pipeline/Flow Route preview where practical. |
| 11 | Done | Update Build Corridor guided review so its centerline row references the shared result instead of owning duplicate logic. |
| 12 | Done | Add contract tests for result sampling, command registration, and preview object creation. |
| 13 | Done | Add contract tests for Structures, Drainage, and Build Corridor consumer reuse. |
| 14 | Pending | Add manual QA steps for checking station/elevation continuity in the FreeCAD 3D View. |

## 12. Acceptance Criteria

- `3D Centerline` appears as a toolbar/menu stage after `Review Plan/Profile`.
- Opening the panel does not create source data.
- The panel reports missing Alignment, Profile, or Stationing prerequisites clearly.
- `Show` creates or updates one review preview object.
- The preview has a visible 3D line and optional station markers.
- The display mode can switch between smooth presentation and exact polyline presentation without changing source/result station frames.
- The generated result preserves source refs to Alignment, Profile, and Stationing.
- Structures and Drainage can continue to store source intent while using the evaluated 3D frame for preview/review.
- Build Corridor can still run if the user skips the explicit `3D Centerline` stage, but should prefer the shared result when available.

## 13. Risks

| Risk | Mitigation |
|---|---|
| Duplicate centerline logic between Build Corridor and the new command | Move sampling into a shared service before wiring consumers. |
| Users may think the 3D line is editable | Label the stage as review, keep source edits in Alignment/Profile/Stations. |
| Stationing gaps or profile gaps create misleading previews | Add diagnostics and block `ok` status when required elevation samples are missing. |
| Structures/Drainage may drift if they compute their own frames | Introduce shared frame lookup helpers after the initial result contract exists. |

## 14. Current Decision

Proceed with the independent `3D Centerline` toolbar stage.

Keep it read-only.

Use it as the common baseline review surface before Structures, Drainage, Applied Sections, and Build Corridor.

Applied Sections should consume this result for per-section placement frames.

They should not be treated as a second 3D centerline owner.
