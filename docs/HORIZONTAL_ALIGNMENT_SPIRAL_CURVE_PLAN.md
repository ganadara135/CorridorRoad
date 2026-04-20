<!-- SPDX-License-Identifier: LGPL-2.1-or-later -->
<!-- SPDX-FileNotice: Part of the Corridor Road addon. -->

# Horizontal Alignment Spiral Curve Plan

Date: 2026-04-15

## Purpose

This document defines a corrective plan for the visible zig-zag behavior seen in
`3D Centerline`.

The current issue should not be treated as a display sampling problem only.
The horizontal source geometry itself mixes true curve edges and polyline-based
transition edges, so the rendered centerline can still look jagged even when the
display sampling is dense.

Implementation note as of `PR-3`:

1. transition spirals now prefer fitted BSpline edges
2. diagnostics expose `BSplineSpiral` vs `PolylineSpiral`
3. polyline fallback is still allowed when spline creation fails

## Current Diagnosis

### What is true-curve today

`HorizontalAlignment` currently uses:

1. tangent segments as line edges
2. circular curve segments as true arc edges

This part is not the main problem.

### What used to be polyline before PR-3

Transition spirals were originally built as:

1. sampled spiral points
2. converted to `_polyline_edges(...)`
3. stored as many short line edges in the final alignment shape

That was the main reason the alignment was not a fully curve-native source when transitions were enabled.

Current state:

1. transition spirals now prefer fitted BSpline edges
2. polyline fallback remains available for robustness

### Why 3D Centerline still looks jagged

`Centerline3DDisplay` currently builds its visible wire with:

1. station sampling
2. `point_at_station(...)`
3. `Part.makePolygon(points)`

So the visible result inherits two separate straight-segment effects:

1. source transition geometry is already polyline-like
2. display output is also rendered as a polygon wire

Because of that, increasing sampling density alone may reduce the effect, but it
does not remove the structural cause.

## Scope Split

This problem should be split into two layers.

### Layer A: source geometry quality

`HorizontalAlignment` should expose smoother transition geometry so the station-to-point
evaluation follows a curve-like path instead of a broken chain.

### Layer B: display geometry quality

`Centerline3DDisplay` should render the visible wire in a smoother viewer-facing form,
instead of always showing a polygonal chain.

## Candidate Approaches

### Option 1. Display-only spline overlay

Keep the engineering source unchanged and only change the displayed `3D Centerline`
wire to a spline-like curve.

How it works:

1. keep station-based evaluation exactly as it is
2. build a viewer-facing spline edge or spline wire from sampled 3D points
3. use that spline only for visual display

Pros:

1. lowest engineering risk
2. fastest improvement for user trust
3. does not change downstream station-based calculations

Cons:

1. source `HorizontalAlignment` still contains polyline spiral segments
2. display can become visually smoother than its source geometry
3. may hide, rather than solve, source-shape limitations

### Option 2. Curve-native spiral source

Replace polyline transition edges in `HorizontalAlignment` with curve-native edges.

Possible implementations:

1. BSpline approximation for each transition spiral
2. higher-order curve fit with tangent continuity at TS/SC/CS/ST

Pros:

1. solves the geometric cause closer to the source
2. improves every downstream station-based query
3. reduces jaggedness for both alignment and centerline displays

Cons:

1. higher implementation complexity
2. station-to-edge mapping must stay stable
3. criteria, key-station reporting, and inverse station lookup need regression coverage

### Option 3. Hybrid recommended path

Use a two-stage correction:

1. first improve `Centerline3DDisplay` visual output
2. then upgrade transition spirals in `HorizontalAlignment`

This gives users faster relief without forcing a risky geometry-core rewrite first.

## Recommended Direction

Recommended plan:

1. keep station-based engineering as the source of truth
2. introduce a viewer-facing smooth display mode for `Centerline3DDisplay`
3. in parallel, plan a source-geometry upgrade for transition spirals in `HorizontalAlignment`
4. do not treat dense sampling alone as the final fix

In practical terms:

1. near-term fix = display smoothing
2. structural fix = curve-native spiral source

## Detailed Design Direction

### A. Centerline display smoothing

Add a display mode for `Centerline3DDisplay`:

1. `Polyline`
2. `SmoothSpline`

`Polyline` remains useful for debugging and exact sampled-point inspection.
`SmoothSpline` becomes the default user-facing mode.

Rules:

1. the display spline must be built from station-evaluated 3D points
2. the display spline must not become the engineering source of truth
3. sections, structures, and corridor logic must continue using `frame_at_station(...)`

### B. Horizontal spiral upgrade

Upgrade transition spirals in `HorizontalAlignment` from:

1. sampled points + line edges

to:

1. sampled points + fitted BSpline edge

Required constraints:

1. preserve entry and exit station positions
2. preserve tangent direction at TS and SC or CS and ST
3. keep circular arc section unchanged
4. keep station traversal stable enough for `point_at_station(...)`

### C. Station mapping stability

If source geometry changes from line-chain spirals to spline spirals, these methods
must be revalidated:

1. `HorizontalAlignment.point_at_station(...)`
2. `HorizontalAlignment.tangent_at_station(...)`
3. `HorizontalAlignment.station_at_xy(...)`
4. section frame creation
5. structure placement and region-boundary diagnostics

## UI / UX Direction

No new workflow order should be required.

Users should still be able to:

1. create/edit alignment
2. generate `3D Centerline`
3. continue to sections and corridor work

Suggested `3D Centerline` task-panel additions:

1. `Wire Display Mode`
2. `Polyline`
3. `Smooth Spline`
4. optional debug-only diagnostics, not normal sampling controls

Suggested wording:

1. `Smooth Spline` improves viewer readability only
2. station-based calculations still use the underlying alignment/profile model
3. user-facing task panel should not expose chord-error / min-step / max-step tuning in the normal workflow

## Risks

### Risk 1. visual vs engineering mismatch

If the display spline becomes much smoother than the source geometry, users may think
that downstream calculations are using the same smoothed curve.

Mitigation:

1. keep wording explicit
2. keep `Polyline` debug mode available
3. report active display mode in status text

### Risk 2. station mapping drift

If `HorizontalAlignment` spirals are upgraded, station-to-edge mapping could shift.

Mitigation:

1. preserve key stations
2. add regression checks for TS/SC/CS/ST station values
3. compare old/new point and tangent deviation over sample stations

### Risk 3. regression in sections/structures

Sections and structures rely on station frames.

Mitigation:

1. keep `Centerline3D.frame_at_station(...)` authoritative
2. add smoke/regression coverage for structure placement and section generation

## Implementation Plan

## Current Status

1. `PR-1` completed
2. `PR-2` completed
3. `PR-3` completed
4. `PR-4` completed

### `PR-1` Diagnostics and proof

1. document that transition spirals are currently polyline edges
2. add developer-visible diagnostics for active display mode and source edge makeup
3. add a focused regression sample that reproduces visible zig-zag on transition geometry

### `PR-2` Display smoothing mode

1. add `Polyline` vs `SmoothSpline` display mode to `Centerline3DDisplay`
2. keep `Polyline` available for debugging
3. make `SmoothSpline` the default user-facing mode
4. verify that sections and corridor features still read station-based frames only

### `PR-3` Horizontal spiral source upgrade

1. replace transition polyline edges with fitted spline edges
2. preserve TS/SC/CS/ST key-station behavior
3. revalidate station and tangent queries on updated geometry

### `PR-4` Regression hardening and docs

1. add regression coverage for:
   - transition display smoothness
   - station mapping stability
   - structure/section downstream behavior
2. update wiki and developer docs with the display-vs-source distinction
3. completed artifacts:
   - `tests/regression/smoke_alignment_transition_downstream.py`
   - `tests/regression/README.md`
   - `docs/wiki/Developer-Guide.md`
   - `.tmp_wiki_repo/Developer-Guide.md`

## Acceptance Criteria

1. `3D Centerline` no longer shows obvious zig-zag artifacts in normal user view
2. `Polyline` mode remains available for debugging sampled geometry
3. downstream station-based design behavior remains unchanged
4. transition-enabled `HorizontalAlignment` no longer relies on visibly broken line chains as the final long-term source geometry
