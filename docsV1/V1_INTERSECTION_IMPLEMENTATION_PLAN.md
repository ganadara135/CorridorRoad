# Parametric Road V1 Intersection Implementation Plan

Date: 2026-06-03
Branch: `v1-0503`
Status: Draft implementation plan
Depends on:

- `docsV1/V1_MASTER_PLAN.md`
- `docsV1/V1_ARCHITECTURE.md`
- `docsV1/V1_ALIGNMENT_MODEL.md`
- `docsV1/V1_PROFILE_MODEL.md`
- `docsV1/V1_3D_CENTERLINE_TOOLBAR_PLAN.md`
- `docsV1/V1_SUPERELEVATION_MODEL.md`
- `docsV1/V1_ASSEMBLY_MODEL.md`
- `docsV1/V1_REGION_MODEL.md`
- `docsV1/V1_STRUCTURE_MODEL.md`
- `docsV1/V1_DRAINAGE_MODEL.md`
- `docsV1/V1_SECTION_MODEL.md`
- `docsV1/V1_INTERSECTION_MODEL.md`

## 1. Purpose

This document defines the first implementation plan for the v1 `Intersections` source stage.

The goal is to add at-grade intersection intent without breaking the current source -> evaluation -> result -> output flow.

Intersections should let users select an intersection type, connect multiple road alignments, define control Regions, review the junction context in 3D, and pass intersection context into `Build Sections`.

## 2. Core Rule

An intersection is not just a wider Region.

The Region owns station-range Assembly application.

The Intersection owns multi-Alignment junction relationship, leg identity, control area policy, and downstream context.

Generated intersection display geometry is review output only. It must not become the editable source of truth.

## 3. Workflow Position

The v1 workflow should become:

```text
Project Setup
-> TIN / Terrain
-> Alignment
-> Stations
-> Profile
-> Review Plan/Profile
-> 3D Centerline
-> Superelevation
-> Assembly
-> Regions
-> Intersections
-> Structures
-> Drainage
-> Build Sections
-> Build Parametric
-> Review
-> Watertight Solids
-> Outputs / Exchange
```

`Intersections` belongs after `Regions` because intersection control areas should reference accepted intersection Regions.

It belongs before `Structures` and `Drainage` because intersection Structures and Drainage rows may reference intersection Regions and intersection context.

## 4. Multi-Alignment Strategy

### 4.1 Rule

Each road axis remains its own `AlignmentModel`.

`side-road-alignment` means a separate side-road centerline. It does not mean the main road's left or right width line.

Road edge lines, lane edges, shoulder edges, ditch edges, and curb edges are Assembly or intersection output geometry, not side-road alignments.

### 4.2 Required Source Families

A practical intersection may involve:

- primary road alignment
- secondary road alignment
- optional additional approach alignments
- profile per participating alignment
- stationing per participating alignment
- 3D Centerline per participating alignment
- Region rows per participating alignment

### 4.3 Intersection Point Mapping

The intersection source should store the point relationship as both geometry and station references:

```text
intersection:t-01
  point: x, y, z
  primary_alignment_ref: alignment:main-road
  primary_station: 520.000
  secondary_alignment_ref: alignment:side-road-01
  secondary_station: 85.000
```

The first implementation can calculate the XY intersection from two sampled alignment paths and resolve each path's station.

Profile elevation and 3D point refinement can be added after the station mapping is stable.

## 5. Region Strategy

Intersection influence areas should be represented as separate Regions on each participating road.

Example:

```text
Main Road Regions
  region:main-normal-01        STA 0.000-480.000
  region:main-intersection-01  STA 480.000-560.000
  region:main-normal-02        STA 560.000-end

Side Road Regions
  region:side-intersection-01  STA 0.000-120.000
  region:side-normal-01        STA 120.000-end
```

The `Intersections` panel should link these Regions through `control_region_refs`.

The Region table should not gain intersection-specific policy fields.

## 6. Intersection Type Selection

The `Intersections` panel must provide user-facing type selection.

Initial supported types:

| UI label | Internal value | First implementation scope |
|---|---|---|
| T Intersection | `t_intersection` | primary + one side road |
| Cross Intersection | `cross_intersection` | two crossing road axes |
| Y Intersection | `y_intersection` | two diverging/merging road axes |

Deferred types:

| UI label | Internal value | Reason deferred |
|---|---|---|
| Staggered Intersection | `staggered_intersection` | needs paired offset junction logic |
| Roundabout | `roundabout` | needs specialized circulatory roadway logic |
| Channelized Turn | `channelized_turn` | needs turn-channel geometry and lane policy |

## 7. Intersections Panel UX

### 7.1 Panel Placement

Toolbar order should become:

```text
Assembly -> Regions -> Intersections -> Structures -> Drainage
```

### 7.2 Panel Sections

Recommended first panel layout:

```text
Preset / Type
  Intersection Type
  Preset Data

Source Mode
  Use Existing Alignments
  Create Starter Sources

Alignments
  Primary Alignment
  Secondary Alignment
  Additional Alignment rows, future

Intersection Point
  Auto Detect
  Primary STA
  Secondary STA
  XY / Z summary

Control Regions
  Primary Region
  Secondary Region
  Influence length controls

Legs
  Leg ID
  Role
  Alignment
  Region
  Approach STA Start
  Approach STA End

Policies
  Curb Return
  Turn Lane
  Grading
  Drainage

Review
  Show Intersection
  Validate
  Apply
  Close
```

### 7.3 Type Presets

Preset data should fill source intent only.

Recommended first presets:

- `Basic T Intersection`
- `Basic Cross Intersection`
- `Basic Y Intersection`

Preset loading may fill:

- `intersection_kind`
- default leg roles
- default control influence lengths
- default policy refs
- starter Region naming suggestions

Preset loading must not generate final corridor surfaces or solids.

## 8. Source Modes

### 8.1 Use Existing Alignments

This is the default professional workflow.

The user chooses existing primary and secondary Alignment rows.

The panel then:

- detects XY crossing or nearest approach
- resolves station on each alignment
- suggests control Region ranges
- validates that selected Regions exist
- creates or updates `IntersectionModel`

### 8.2 Create Starter Sources

This mode supports early design and tutorials.

The panel may create starter source objects:

- primary Alignment
- secondary Alignment
- basic Profile rows
- Stationing rows
- basic Regions
- intersection Regions

The created objects must remain normal source objects that users can edit from their own panels.

This mode must not hide generated intent inside the intersection panel.

## 9. Source Model Updates

`IntersectionModel` should be extended in small steps.

Recommended additions:

- `intersection_index`
- `primary_alignment_ref`
- `secondary_alignment_refs`
- `intersection_point_x`
- `intersection_point_y`
- `intersection_point_z`
- `primary_station`
- `control_region_refs`
- `policy_refs`
- `source_mode`
- `diagnostic_rows`

`IntersectionLegRow` should preserve:

- `intersection_id`
- `leg_role`
- `alignment_ref`
- `profile_ref`
- `centerline3d_ref`
- `region_ref`
- `approach_station_start`
- `approach_station_end`
- `priority`
- `notes`

`IntersectionControlArea` should preserve:

- per-alignment station ranges
- control Region refs
- influence Region refs, if any
- curb-return policy ref
- turn-lane policy ref
- grading policy ref
- drainage policy ref

## 10. Evaluation Service

`IntersectionEvaluationService` should evolve from station-only lookup into alignment-aware lookup.

First target:

```text
resolve_station(intersection_model, alignment_ref, station)
```

Result should include:

- active intersection id
- active control area id
- active leg id
- leg role
- control Region ref
- curb-return policy ref
- turn-lane policy ref
- grading policy ref
- drainage policy ref
- diagnostics

## 11. Build Sections Integration

`Build Sections` is the first downstream result stage that should consume intersection context.

Each affected Applied Section should store:

- `intersection_ref`
- `intersection_kind`
- `intersection_leg_role`
- `intersection_control_area_ref`
- `intersection_region_ref`
- `curb_return_policy_ref`
- `turn_lane_policy_ref`
- `intersection_grading_policy_ref`
- `intersection_drainage_policy_ref`

The first implementation does not need to fully alter section geometry.

It should make the context visible and testable first.

## 12. 3D Review

The first review output should show:

- intersection point marker
- primary and secondary leg highlight
- control Region station spans
- influence area spans
- labels for leg role and intersection type

Review objects should be routed under the appropriate review or intersection tree group.

They are generated outputs, not source geometry.

## 13. Structures And Drainage Handoff

Structures and Drainage should continue to own their own source rows.

Intersection context should help them by exposing:

- available intersection Regions
- active leg roles
- control area ids
- recommended low-point or inlet review locations, future

The first implementation should avoid automatic drainage solving.

Drainage can later use intersection context for curb/gutter flow, inlet placement hints, and Flow Route diagnostics.

## 14. Build Parametric And Surface Strategy

Initial Build Parametric integration should be conservative.

First target:

- build ordinary Region surfaces for intersection Regions
- label and review them as intersection-controlled Regions
- diagnose gap/overlap between main and side-road intersection surfaces

Deferred:

- automatic curb-return surface patch
- automatic intersection grading surface blend
- automatic turn-lane taper geometry
- automatic multi-leg surface stitching

## 15. Watertight Solid Strategy

Intersections should eventually become separate solid targets.

Potential targets:

- `intersection_body`
- `intersection_surface_patch`
- `intersection_curb_gutter_body`
- `intersection_drainage_body`

The first implementation should only preserve enough context for later target discovery.

## 16. Diagnostics

Recommended first diagnostics:

- `intersection_missing_primary_alignment`
- `intersection_missing_secondary_alignment`
- `intersection_alignment_pair_does_not_cross`
- `intersection_station_mapping_failed`
- `intersection_control_region_missing`
- `intersection_control_region_wrong_alignment`
- `intersection_leg_region_missing`
- `intersection_overlapping_control_area`
- `intersection_type_not_supported`
- `intersection_context_not_reflected_in_applied_sections`

## 17. Implementation Phases

| Phase | Status | Scope | Acceptance Criteria |
|---|---|---|---|
| IX-1 | Done | Update docs and workflow references | README/workflow docs mention `Intersections` between Regions and Structures |
| IX-2 | Done | Extend source dataclasses and tests | `IntersectionModel` round-trips type, alignment refs, control Regions, and legs |
| IX-3 | Done | Alignment-aware evaluation service | service resolves active context by `alignment_ref + station` |
| IX-4 | Done | Add Intersections command and panel shell | panel opens without document mutation and exposes Type/Preset selection |
| IX-5 | Done | Existing Alignments mode | panel can select primary/secondary Alignment and validate required refs |
| IX-6 | Done | Auto Detect intersection point | service computes or reports crossing/nearest station mapping |
| IX-7 | Done | Create Starter Sources mode | panel can create editable starter Alignment/Profile/Station/Region sources |
| IX-8 | Done | Control Region linking | panel links selected intersection Regions to intersection rows |
| IX-9 | Done | 3D review overlay | double-click/show action highlights point, legs, and control spans |
| IX-10 | Done | Build Sections handoff | Applied Sections show active intersection context |
| IX-11 | Done | Build Parametric diagnostics | intersection Regions appear in build review with gap/overlap diagnostics |

## 18. First Coding Slice

Recommended first coding slice:

1. [x] Update `IntersectionModel` fields for type, alignment refs, control Regions, and leg rows.
2. [x] Add contract tests for `t_intersection`, `cross_intersection`, and `y_intersection` presets.
3. [x] Extend `IntersectionEvaluationService.resolve_station()` to accept `alignment_ref`.
4. [x] Add a minimal `Intersections` command/panel with no document mutation on open.
5. [x] Add `Intersection Type` combo and `Preset Data` loading.

This creates a safe source and UX foundation before 3D geometry or Build Sections behavior changes.

## 19. Non-goals

The first implementation should not attempt:

- full automatic intersection grading
- full curb-return surface generation
- roundabout modeling
- traffic signal modeling
- hidden automatic overwrite of existing Alignment/Profile/Region objects
- direct conversion of generated review geometry into source state
- watertight intersection solids before source and section context are stable
