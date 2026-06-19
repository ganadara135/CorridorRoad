# V1 Supplemental Frame Sampling Plan

Status: Superseded

Scope: define how Build Corridor creates output-only supplemental frames between accepted Applied Section stations so corridor surfaces and solids follow the reviewed `Centerline3DResult` curve.

Superseded by:

- [V1_APPLIED_SECTION_SUPPLEMENTAL_SAMPLING_REDESIGN_PLAN.md](./V1_APPLIED_SECTION_SUPPLEMENTAL_SAMPLING_REDESIGN_PLAN.md)

Reason:

Surface generation needs complete evaluated `AppliedSection` rows at supplemental stations, not Build Corridor-only frame samples.

Keep this document as historical implementation context only.

## Purpose

Build Corridor must follow the 3D Centerline curve, not only the sparse user station list.

User stations remain the design and review anchors.

Supplemental frames add derived drawing/build samples between those anchors.

## Scope

This plan covers:

- supplemental frame terminology
- station placement rules
- 3D Centerline frame lookup
- Build Corridor surface and solid sampling
- user-facing density controls
- diagnostics and guided review feedback
- validation criteria

This plan does not make supplemental frames editable source rows.

## Core Rule

`Centerline3DResult` owns the baseline station, offset, elevation, and tangent frame.

`AppliedSection.frame` is a derived station placement snapshot.

Supplemental frames are output-only derived placement snapshots.

They may improve geometry density, but they must not change Assembly, Subassembly, Region, Profile, Alignment, or Applied Section source intent.

## Terminology

| Term | Meaning |
| --- | --- |
| User station | A station explicitly created by stationing, region boundaries, intersections, or Applied Sections. |
| Applied Section frame | The local placement frame persisted with an accepted Applied Section result. |
| Supplemental station | A generated station value inserted between user stations for output geometry only. |
| Supplemental frame | The `Centerline3DResult`-derived placement frame at a supplemental station. |
| Build frame series | The ordered list of user frames plus supplemental frames used by Build Corridor to create surfaces and solids. |

## Design Goals

- Make curved 3D Centerline output visibly follow the reviewed curve.
- Keep user station rows stable and readable.
- Avoid turning display/build samples into editable source.
- Use one shared frame lookup behavior for horizontal curves, profile changes, and combined 3D curvature.
- Let ordinary users control density with a simple slider.
- Give advanced diagnostics when fallback or sparse sampling occurs.
- Keep performance predictable.

## Sampling Inputs

Build Corridor should build the frame series from:

- accepted Applied Section stations
- required Region start and end stations
- Assembly/Subassembly transition stations
- Intersection supplemental stations
- Structure and Drainage hard break stations when they affect corridor output
- user-selected supplemental density
- 3D Centerline chord deviation
- 3D Centerline tangent angle change
- profile elevation and grade change
- superelevation change when available

## Placement Rules

Start with the accepted Applied Section station list.

Add required hard break stations before optional densification.

Hard break stations include:

- Region boundaries
- Assembly template changes
- explicit override boundaries
- intersection control-area handoff stations
- structure tie-in stations when they alter corridor shape
- drainage policy or ditch handoff stations when they alter corridor shape

Then add optional supplemental stations between consecutive hard/user stations.

Optional supplemental stations are inserted when any rule below is exceeded:

| Rule | Default |
| --- | --- |
| Maximum spacing | controlled by the Build Corridor density slider |
| Maximum tangent change | 3 degrees |
| Maximum chord deviation from 3D Centerline | 0.25 m |
| Maximum profile elevation delta per span | TBD after validation |
| Maximum superelevation delta per span | TBD after superelevation output stabilization |

The implementation may recursively split a span until all active rules pass or a configured maximum sample count is reached.

## Frame Resolution

Each supplemental station must resolve its frame from `Centerline3DResult`.

The frame must not be made by linear interpolation of Applied Section XY coordinates when the shared 3D Centerline is available.

Required frame fields:

- station
- x
- y
- z
- tangent direction
- normal direction or enough tangent data to derive it
- source mode

Use `source=centerline3d_result` when the shared baseline resolves the frame.

Use `source=applied_section_frame` only as an explicit fallback during transition.

Fallback must create a diagnostic row.

## Geometry Application

Build Corridor should create surfaces and solids from the full Build frame series.

That series includes:

- original Applied Section frames
- supplemental frames

For supplemental frames, section point rows may be derived by interpolation of lateral offsets, vertical offsets, subassembly refs, point codes, link codes, and surface roles between neighboring accepted Applied Sections.

Frame origin and tangent must come from the resolved supplemental frame.

This keeps section shape interpolation separate from baseline path ownership.

## UX Plan

Expose a simple control in Build Corridor:

```text
Supplemental Sampling
[ Low ---- Medium ---- High ---- Very High ]
```

Recommended mapping:

| UX level | Max spacing |
| --- | --- |
| Low | 10 m |
| Medium | 5 m |
| High | 2 m |
| Very High | 1 m |

Keep the existing fine-grained slider if already implemented, but label it as density rather than source station count.

Advanced settings may be added later:

- max spacing
- max tangent change
- max chord deviation
- max samples per span
- show supplemental frames in 3D View

## Diagnostics

Build Corridor Guided Review should report:

- requested density level
- resolved max spacing
- input user station count
- supplemental frame count
- total build frame count
- count by trigger type
- frame source mode
- fallback count
- maximum observed chord deviation after sampling
- maximum observed tangent delta after sampling

Recommended diagnostic messages:

| Kind | Severity | Meaning |
| --- | --- | --- |
| `supplemental_frame_source_centerline3d` | info | Supplemental frames used `Centerline3DResult`. |
| `supplemental_frame_fallback_applied_section_frame` | warning | Shared 3D Centerline was unavailable for one or more frames. |
| `supplemental_frame_density_limited` | warning | Requested density was capped by max sample count. |
| `supplemental_frame_chord_deviation_exceeded` | warning | Final frame spacing may still be too sparse for the curve. |
| `supplemental_frame_tangent_delta_exceeded` | warning | Final tangent change per span is still high. |

## Implementation Order

| Step | Status | Work |
| --- | --- | --- |
| 1 | Done | Add a dedicated Build frame series helper that accepts Applied Sections plus `Centerline3DResult`. |
| 2 | Done | Move max spacing, tangent delta, and chord deviation checks into the helper. |
| 3 | Done | Make the helper recursively split spans until all active sampling rules pass. |
| 4 | Done | Ensure every supplemental frame resolves origin and tangent from `Centerline3DResult`. |
| 5 | Done | Feed the full Build frame series into corridor surface generation, not only accepted Applied Section frames. |
| 6 | Done | Preserve Subassembly point/link/surface provenance during supplemental section interpolation. |
| 7 | Done | Add Guided Review rows for source mode, trigger counts, fallback counts, and final max deviation. |
| 8 | Done | Add a 3D optional review display for supplemental frames. |
| 9 | Done | Add focused FreeCADCmd validation for curved centerline densification. |
| 10 | Done | Update user docs after the behavior is stable. |

## Implementation Notes

- Done: Build Corridor surface geometry now inserts supplemental sections through recursive span splitting instead of one-pass uniform insertion.
- Done: Supplemental frame resolution prefers the supplied `Centerline3DResult` frame resolver and preserves `source=centerline3d_result` notes.
- Done: Design surface generation consumes the expanded section series.
- Done: Supplemental section interpolation now preserves compatible Subassembly point, link, and shape rows so surface ownership and highlights can continue across generated samples.
- Done: Build Corridor Guided Review now includes a `2a. Supplemental Frames` row with source station count, supplemental frame count, total build frame count, source mode counts, fallback count, tangent delta, and chord deviation.
- Done: Build Corridor can create `V1CorridorSupplementalFrameMarkers` to show supplemental frame positions and tangent markers in the 3D View.
- Done: Added `tests/contracts/v1/test_supplemental_frame_sampling.py` as the focused FreeCADCmd validation for supplemental frame sampling.
- Done: Updated `docsV1/wiki/Applied-Sections-Build-Corridor.md` with user-facing Supplemental Sampling guidance.
- Validated: FreeCADCmd service-level curved-centerline test passed with Low density producing 5 sections and High density producing 17 sections.
- Validated: FreeCADCmd supplemental Subassembly provenance interpolation test passed.
- Validated: FreeCADCmd supplemental sampling Guided Review diagnostics test passed.
- Validated: FreeCADCmd supplemental frame marker preview test passed.
- Validated: `FreeCADCmd.exe -c "exec(open(r'tests\\contracts\\v1\\test_supplemental_frame_sampling.py', 'r', encoding='utf-8').read())"` passed.

## Acceptance Criteria

- A curved `Centerline3DResult` produces more Build frames than the accepted Applied Section station count when density or curvature requires it.
- Increasing the supplemental density visibly changes the generated corridor surface on a curved 3D Centerline.
- Supplemental frame origins lie on the reviewed 3D Centerline curve.
- Supplemental frame tangents follow the reviewed 3D Centerline tangent.
- Build Corridor Guided Review reports `source=centerline3d_result` for supplemental frames when available.
- Fallback to `applied_section_frame` is visible as a warning.
- User station rows do not change when supplemental density changes.
- Applied Sections remain the accepted review result; Build Corridor owns only the output densification.

## Manual QA Checklist

- Build a corridor with a sparse station list and a visibly curved 3D Centerline.
- Build with Low density and capture the Design Surface edge.
- Build with Very High density and confirm the Design Surface follows the curve more closely.
- Confirm Guided Review reports a larger total build frame count.
- Confirm supplemental frame source is `centerline3d_result`.
- Hide the 3D Centerline result or force fallback and confirm a warning appears.
- Confirm changing density does not add rows to the Applied Sections table.
- Confirm Lane, Shoulder, Ditch, and Side Slope provenance remains visible in guided review and surface highlights.

## Risks

| Risk | Mitigation |
| --- | --- |
| Too many supplemental frames can slow Build Corridor. | Cap samples per span and report `supplemental_frame_density_limited`. |
| Supplemental frames may be mistaken for source stations. | Label them as output-only in UI and diagnostics. |
| Shape interpolation can break when neighboring sections have different point topology. | Preserve existing fallback diagnostics and only interpolate compatible profiles. |
| Fallback to Applied Section frames can hide centerline drift. | Require explicit fallback diagnostics and guided review counts. |

## Non-goals

- Do not edit Alignment, Profile, Region, or Assembly source from supplemental frames.
- Do not add supplemental rows to the Applied Sections source table.
- Do not make supplemental frame markers mandatory display objects.
- Do not replace `Centerline3DResult` with Build Corridor-owned centerline logic.
