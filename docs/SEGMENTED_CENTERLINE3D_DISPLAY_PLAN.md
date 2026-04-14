<!-- SPDX-License-Identifier: LGPL-2.1-or-later -->
<!-- SPDX-FileNotice: Part of the Corridor Road addon. -->

# Segmented 3D Centerline Display Plan

Date: 2026-04-14

## Purpose

This document defines a structural improvement plan for `3D Centerline` display.

The target is not to change the station-based design model.
The target is to improve user trust and visual stability by replacing the current single sampled wire mental model with a segmented, meaning-aware display system.

The plan assumes:

1. station-based design remains the engineering source of truth
2. visible zig-zag / wiggly centerline behavior is primarily a display-side sampling/rendering issue
3. the best fix is to improve display segmentation and sampling policy, not to move design logic away from station-based evaluation

## Problem Statement

The current `Centerline3DDisplay` builds one sampled polyline wire across the full alignment.

That causes three kinds of confusion:

1. visual confusion
   - a long sampled wire can look angular, segmented, or wiggly during zoom/pan
2. semantic confusion
   - the visible wire does not show where meaningful design changes happen
   - transition zones, vertical curve ranges, region boundaries, and structure-influenced spans are not obvious from the display structure
3. trust confusion
   - users may think the station-based design itself is inaccurate even when section/corridor calculations are correct

## Current State

Today:

1. `Centerline3D` is an engine/data object
   - resolves `point3d_at_station(...)`
   - resolves `tangent3d_at_station(...)`
   - resolves `frame_at_station(...)`
2. `Centerline3DDisplay` is a viewer object
   - adaptively samples stations
   - builds a single `Part.makePolygon(points)` wire
3. sections and corridor logic already depend on station-based frame evaluation, not on the displayed wire as the design contract

This split is already directionally correct.
The weak point is that the display object is still too monolithic and too generic.

## Target Outcome

The target system should satisfy all of the following.

### Geometry contract

1. `Centerline3D` remains the station-based geometric engine
2. `Centerline3DDisplay` remains display-only
3. sections, structures, and corridor generation continue to evaluate the engine at stations rather than inheriting truth from a rendered polyline

### Display contract

1. the visible centerline should be divided into meaningful segments
2. each segment should be sampled according to its geometric/design context
3. display segmentation should make boundaries easier to understand visually and easier to debug

### Workflow contract

1. command order should remain fundamentally upstream-to-downstream
2. `3D Centerline` should still be generated from alignment + profile inputs
3. later objects such as `RegionPlan` and `StructureSet` may influence display segmentation metadata, but should not become the geometric source of the centerline itself

## Non-Goals

1. this plan does not replace station-based design with polyline-driven design
2. this plan does not make `Typical Section` or `Edit Structures` prerequisites for centerline geometry computation
3. this plan does not force a full internal rename away from `Centerline3DDisplay`
4. this plan does not promise infinite visual smoothness under every OpenGL precision scenario

## Design Principles

### 1. Keep engine and display separate

Do not let display-driven concerns leak into section/corridor engineering logic.

### 2. Segment by design meaning

The display object should expose design-relevant boundaries instead of one undifferentiated wire.

### 3. Preserve current command order

The recommended user-facing dependency chain remains:

1. Alignment
2. Profiles / Vertical Alignment
3. 3D Centerline
4. Typical Section
5. Regions
6. Structures
7. Sections
8. Corridor

`Regions` and `Structures` may later refine how the display is split or annotated, but they do not define the baseline centerline geometry.

### 4. Improve confidence without changing engineering truth

When the display looks coarse, improve the display.
Do not rewrite the core station-based model to match a rendering artifact.

## Proposed Object Responsibility Split

### `Centerline3D`

Keep responsibility limited to:

1. resolve 3D point at station
2. resolve tangent/frame at station
3. expose total length and source diagnostics
4. remain independent from regions, structures, and corridor packaging

### `Centerline3DDisplay`

Evolve into:

1. segmented display assembly object
2. owner of display sampling policy
3. owner of segment-level diagnostics
4. optional consumer of segmentation hints from:
   - `Stationing`
   - horizontal key stations
   - vertical curve keys
   - `RegionPlan`
   - `StructureSet`

### Optional child/segment objects

Recommended new display hierarchy:

1. `Centerline3DDisplay`
2. child `Centerline3DSegment` objects or internal segment row records

Each segment should represent one meaningful display range.

### Recommended visibility policy

Recommended user-facing behavior:

1. `Centerline3D` remains an internal engine/data object
2. `Centerline3D` should stay hidden from normal 3D view usage
3. `Centerline3DDisplay` is the object users should normally see in the tree and in 3D view
4. if segment-level debug objects are introduced later, they should remain optional and not become the default tree experience

This keeps the engine/display split clean without forcing users to manage two centerline objects in normal workflows.

## Segmentation Strategy

### Base split sources

Always split at:

1. start station
2. end station
3. stationing values when enabled
4. horizontal alignment edge boundaries
5. horizontal key stations if available
6. vertical curve boundaries such as BVC/EVC

### Optional semantic split sources

Split additionally when available:

1. region boundaries
2. region transition boundaries
3. structure influence ranges
4. structure notch boundaries
5. explicitly requested debug stations

### Segment categories

Each segment should carry a kind label such as:

1. `base`
2. `horizontal_transition`
3. `vertical_curve`
4. `region_boundary`
5. `region_transition`
6. `structure_zone`
7. `structure_notch`
8. `mixed`

Kinds are for diagnostics and display policy only.
They do not replace the underlying centerline math.

## Sampling Strategy

### Why segment-local sampling

A single global `MaxChordError / MinStep / MaxStep` policy is too blunt.
Straight spans, transition spans, and structure-sensitive spans do not need the same density.

### Proposed per-segment sampling policy

Each segment should derive its own sampling parameters from:

1. geometric curvature / vertical change
2. segment kind
3. user display quality preset

Example policy direction:

1. straight/base segments
   - relaxed spacing
2. curve / transition / vertical-curve segments
   - tighter spacing
3. region boundary or structure-sensitive segments
   - force boundary inclusion and tighter near-boundary spacing

### Quality presets

Recommended display presets:

1. `Fast`
2. `Normal`
3. `Fine`
4. `Ultra`

Suggested mapping policy:

1. `Fast`
   - coarser `MaxChordError`
   - larger `MinStep` / `MaxStep`
2. `Normal`
   - current default-quality replacement
3. `Fine`
   - recommended for engineering review
4. `Ultra`
   - recommended for screenshots / visual QA only

## Display Construction Options

Two implementation paths are acceptable.

### Option A: single parent shape assembled from segmented polylines

1. each segment builds its own sampled wire
2. parent display builds a compound of all segment wires

Pros:

1. easy migration path
2. keeps current `Part`-based wire display style
3. simpler compatibility with current tree and command flow

Cons:

1. segment objects remain mostly invisible unless surfaced in diagnostics

### Option B: real child display segment objects

1. create child `Part::FeaturePython` display objects per segment
2. parent acts as organizer + summary owner

Pros:

1. easier visual debugging
2. segment-level tree inspection becomes explicit
3. easier to color-code segment kinds

Cons:

1. more tree clutter
2. more recompute and object-lifecycle complexity

Recommended first delivery:

1. implement Option A first
2. keep Option B as a later debugging/advanced-mode feature

## Display Diagnostics

`Centerline3DDisplay` should report:

1. segment count
2. segment kind summary
3. total sampled point count
4. densest segment summary
5. highest-deviation segment summary
6. split sources used

Optional advanced diagnostics:

1. station ranges per segment
2. actual per-segment sampling policy
3. precision warning if display is far from local origin

## Local/World Precision Policy

Segmentation is not a substitute for coordinate hygiene.
The display runtime should continue to follow the local/world transform policy.

Required rules:

1. display geometry should be built in project-local coordinates
2. world-coordinate references should be converted at the boundary
3. diagnostics may mention world/local setup, but display geometry should not depend on large raw world coordinates where avoidable

## Command and Workflow Policy

### Recommended command order

Do not move `3D Centerline` after `Typical Section` or `Edit Structures` as a baseline workflow rule.

Reason:

1. centerline geometry is still driven by alignment + profile
2. typical section, regions, and structures are downstream consumers
3. later objects may contribute segmentation hints, but they are not the baseline geometric source

### Recompute policy

`Centerline3DDisplay` should recompute when:

1. alignment changes
2. stationing changes
3. vertical alignment or profile bundle changes
4. display quality settings change

Optional semantic recompute when enabled:

1. region plan boundaries change
2. structure corridor ranges change

Recommended setting:

1. semantic split sources should be opt-in or lightweight by default
2. base centerline display must still work without regions or structures

## UI Policy

Recommended task-panel or property additions:

1. `Display Quality`
2. `Segment By Regions`
3. `Segment By Structures`
4. `Segment By Vertical Keys`
5. `Show Segment Diagnostics`

### Implemented first-pass task-panel UX

The current preferred user flow is now task-panel based instead of immediate one-click generation.

Recommended panel composition:

1. `Sources`
   - `Alignment`
   - `Stationing`
   - `Vertical Alignment`
   - `ProfileBundle`
   - `Use Stationing`
   - `Elevation Source`
2. `Display`
   - target display object selector
   - `Show Wire`
   - `Use Key Stations`
   - `Display Quality`
3. `Sampling`
   - `Max Chord Error`
   - `Min Step`
   - `Max Step`
4. `Run`
   - status/summary text
   - explicit `Generate 3D Centerline Now`

UX rules:

1. keep `Centerline3DDisplay` as the visible user object
2. keep the panel explicit that the 3D wire is a sampled display object
3. remind users that station-based frames remain the engineering source of truth
4. keep advanced numeric sampling values visible, but make `Display Quality` the main normal-path control

Recommended completion/status wording:

1. make it explicit that this is a display wire
2. clarify that station-based frames remain the engineering source of truth

Example wording:

- `3D centerline display updated.`
- `Segments: 18 | Sampled points: 412 | Design frames remain station-based.`

## Compatibility Policy

Keep backward compatibility for current objects where possible.

Recommended migration behavior:

1. existing `Centerline3DDisplay` objects should load with segmentation disabled or base-only
2. new properties should default safely
3. no change should be required for existing section/corridor files to continue working

## Regression Coverage

Add or extend tests for:

1. segmented display still covers full centerline range
2. boundary stations are preserved
3. segment count changes when region/structure split sources are enabled
4. section generation results remain unchanged when only display segmentation changes
5. large-coordinate/local-origin projects still generate display geometry in local coordinates

## Implementation Plan

## Current Status

1. `PR-1` completed
2. `PR-2` completed
3. `PR-3` completed
4. `PR-4` completed
5. `PR-5` completed

### `PR-1` Segment model + diagnostics foundation

1. add segment-row planning helper
2. define split-source merge rules
3. define segment kind classification
4. add diagnostic summary properties to `Centerline3DDisplay`

### `PR-2` Segmented display assembly

1. replace single global sampled wire build with per-segment assembly
2. keep output as one parent display shape/compound
3. preserve current visual behavior when no extra split sources are enabled

### `PR-3` Quality presets + per-segment sampling policy

1. add display quality presets
2. derive per-segment sampling policy from kind + preset
3. tune defaults toward smoother visual output

### `PR-4` Region / structure semantic segmentation

1. add optional region-boundary split consumption
2. add optional structure-range split consumption
3. expose segment source summaries in diagnostics
4. add task panel source pickers and toggles for semantic split control

### `PR-5` UI wording + wiki/docs + regression hardening

1. update command/panel wording so users understand the display-vs-design split
2. update architecture/wiki/troubleshooting docs
3. add regression coverage for segment planning and unchanged station-based section behavior
4. verify with `smoke_centerline3d_display_segmentation.py` and existing station-based section merge smoke

## Success Criteria

The plan is successful when all of the following are true:

1. users can still run `3D Centerline` before `Typical Section`, `Regions`, and `Structures`
2. the visible centerline is smoother and more understandable
3. region/structure boundaries can optionally appear in segmentation diagnostics
4. station-based sections and corridor results remain numerically unchanged when only display segmentation changes
5. users are less likely to mistake display artifacts for design-model errors
