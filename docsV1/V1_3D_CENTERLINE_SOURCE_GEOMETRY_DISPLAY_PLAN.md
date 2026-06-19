# V1 3D Centerline Source Geometry Display Plan

## Purpose

Define the implementation path for three 3D Centerline display modes:

- `Source Geometry`
- `B-spline`
- `Polyline`

The goal is to remove visual zigzags caused by point-only preview geometry while keeping `Centerline3DResult` as the calculation contract for downstream consumers.

## Scope

This plan covers the 3D Centerline review preview command and the follow-up handoff into Applied Sections frame placement.

The first implementation pass kept Applied Sections unchanged.

The follow-up implementation now lets Applied Sections resolve frames from Alignment/Profile Source Geometry first, then fallback to `Centerline3DResult` point-row interpolation when source geometry is unavailable.

## Core Rule

Display geometry is review geometry.

Durable station, offset, elevation, and downstream placement data remain owned by `Centerline3DResult` and source models.

## Display Modes

### Source Geometry

`Source Geometry` is the preferred review mode.

It should draw from `AlignmentModel` and `ProfileModel` source segments rather than only from evaluated point rows.

Expected behavior:

- horizontal tangent plus vertical tangent creates a 3D line
- any horizontal curve or vertical curve creates a source-sampled smooth curve
- segment boundaries come from alignment element limits, profile tangent limits, and vertical curve BVC/EVC limits
- source evaluation points are not smoothed after evaluation
- source-sampled 3D curve intervals use dense source samples rather than B-spline re-smoothing, so vertical curves do not overshoot or create local hooks
- source-sampled 3D curve interval spacing is user-adjustable from the 3D Centerline panel

Fallback behavior:

- if source geometry cannot be built, use B-spline display
- record fallback status on the preview object
- show the fallback reason in the panel message

### B-spline

`B-spline` is a visual helper mode.

It uses evaluated `Centerline3DResult.point_rows` and creates a display-only smoothed B-spline.

It is not the design-authoritative geometry.

### Polyline

`Polyline` is the raw diagnostic mode.

It connects evaluated `Centerline3DResult.point_rows` directly.

It should remain available for checking station samples and evaluation artifacts.

## User Interface

The 3D Centerline panel display combo should expose:

- `Source Geometry`
- `B-spline`
- `Polyline`

Default:

- `Source Geometry`

Tooltip:

```text
Source Geometry draws from Alignment/Profile source segments. B-spline smooths evaluated centerline points. Polyline shows raw evaluated centerline points.
```

Source Geometry controls:

- `Arc-fit tolerance Abs`
- `Arc-fit tolerance Rel`
- `Source Geometry Sample Spacing`

Default sample spacing:

- `1.0 m`

Lower spacing values draw smoother vertical/profile curves with more preview segments.

## Implementation Stages

### Stage 1: Display mode contract

Tasks:

- add the three display modes to the panel
- make `Source Geometry` the default
- normalize old `Smooth Curve` values to `B-spline`
- keep `Polyline` behavior unchanged
- add source-geometry fallback status fields

Acceptance criteria:

- the panel shows all three modes
- `Source Geometry` can be selected without breaking preview generation
- old `Smooth Curve` values remain compatible
- tests confirm mode normalization and UI default

### Stage 2: Point-based builders cleanup

Tasks:

- make `Polyline` and `B-spline` builders explicit
- keep B-spline as display-only
- make curve kind values stable

Acceptance criteria:

- `Polyline` returns `CurveKind=polyline`
- `B-spline` returns `CurveKind=bspline_smoothed` or safe fallback
- calculation point rows are unchanged

### Stage 3: Source Geometry interval builder

Tasks:

- collect source station boundaries from alignment and profile
- split centerline preview into source intervals
- classify each interval as line or curve
- evaluate XY from alignment source and Z from profile source
- build line edges for line intervals
- build sampled B-spline edges for curve intervals

Acceptance criteria:

- `Source Geometry` returns `CurveKind=source_geometry`
- simple tangent/tangent spans are straight lines
- vertical curves and horizontal curves display without point-row zigzags

### Stage 4: Diagnostics and fallback

Tasks:

- persist `SourceGeometryStatus`
- persist `SourceGeometryMessage`
- show fallback message in the panel
- keep fallback non-destructive

Acceptance criteria:

- source success is visible
- fallback reason is visible
- downstream `Centerline3DResult` contract is unchanged

### Stage 5: Validation

Tasks:

- add focused FreeCADCmd tests
- validate display mode normalization
- validate UI default
- validate source fallback
- validate B-spline and Polyline modes

Acceptance criteria:

- command tests pass
- preview consistency tests pass
- source geometry failures do not block review

## Future Link to Applied Sections

Applied Sections now reuse the Source Geometry station resolver for frame placement.

Rule:

- if Alignment/Profile source models are available, frame origin and tangent come from Source Geometry
- if source geometry cannot be resolved, frame origin and tangent fallback to `Centerline3DResult`
- frame notes expose `source=centerline3d_source_geometry`
- frame notes also keep a compatibility marker for existing downstream checks that still recognize `centerline3d_result`

Acceptance criteria:

- Applied Sections section frames show Source Geometry as the primary source
- Supplemental Applied Sections inherit the same source-based frame placement
- downstream surface/solid builders still recognize centerline-driven frames
- fallback diagnostics remain visible in frame notes

## Implementation Status

Completed:

- `Source Geometry`, `B-spline`, and `Polyline` display modes are available
- `Source Geometry` is the default display mode
- arc-fit tolerance controls and diagnostics are visible
- Source Geometry frame resolution is available as an evaluation service
- Applied Sections frame placement now prefers Source Geometry
- `Centerline3DResult` fallback remains available for compatibility

Remaining follow-up:

- remove duplicated arc-fit helper logic from the command layer after downstream behavior is stable
- keep older fallback-specific contracts explicit when they intentionally validate `Centerline3DResult` fallback behavior

## Non-goals

- do not use smoothed preview geometry as engineering source truth
- do not change Applied Sections placement in this plan
- do not hide source geometry fallback from the user
