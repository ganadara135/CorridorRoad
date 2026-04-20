<!-- SPDX-License-Identifier: LGPL-2.1-or-later -->
<!-- SPDX-FileNotice: Part of the Corridor Road addon. -->

# 3D Centerline Display Object Split Plan

Date: 2026-04-15

## Purpose

This document defines the next structural revision for `3D Centerline`.

The previous segmented-display work improved diagnostics, but it did not solve the
main user-facing issue well enough:

1. the visible centerline still looks zig-zag / wiggly
2. users still read segmentation artifacts as if the centerline itself were broken
3. semantic boundaries are still mixed into the same display object instead of being shown separately

The new target is:

1. keep one visible `3D Centerline` main wire
2. separate semantic boundary markers into child objects under that centerline
3. make the tree and 3D view explain segment boundaries without making the main wire look segmented

## Problem Statement

The current `Centerline3DDisplay` uses segment-aware sampling and diagnostics, but
the result still behaves as one sampled polyline problem in the user's eye.

That causes two different kinds of confusion to collapse together:

1. geometric confidence problem
   - users look at the main 3D wire and think the centerline itself is jagged
2. semantic boundary problem
   - users also want to know where region / structure / transition ranges begin and end

Those should not be solved with the same visible object.

## Target Outcome

### Main-wire contract

1. `Centerline3DDisplay` remains the main visible centerline object
2. its `Shape` should be one continuous wire in the tree and in the 3D view
3. it may still use segment-aware sampling internally, but the displayed result should read as one centerline

### Boundary-marker contract

1. semantic split stations should be materialized as separate child objects
2. each child object should draw a short cross-line marker at its station
3. markers should be tree-visible under the main `3D Centerline`
4. markers should carry source metadata such as:
   - region boundary
   - region transition
   - structure boundary
   - structure transition
   - optional start/end or debug markers

### Engineering contract

1. this change is display-only
2. station-based frame evaluation remains the engineering source of truth
3. sections, structures, and corridor generation do not inherit truth from the visible sampled wire

## Proposed Tree Model

Recommended tree shape:

1. `3D Centerline`
2. child `CenterlineBoundaryMarker` objects

Example:

1. `3D Centerline (H+V)`
2. `Boundary @STA 35.000`
3. `Boundary @STA 40.000`
4. `Boundary @STA 48.000`
5. `Boundary @STA 54.000`

Tree placement rule:

1. the alignment default tree should reserve a dedicated `3D Centerline` branch from the start
2. `3D Centerline (H+V)` should live in that branch as a sibling branch to `Horizontal`, `Stationing`, `VerticalProfiles`, `Assembly`, `Regions`, `Sections`, and `Corridor`
3. `CenterlineBoundaryMarker` objects should appear only under the `3D Centerline` object, not as separate top-level alignment folders/items

The main idea is simple:

1. the main wire shows the route itself
2. the children show where the route meaning changes

## Object Responsibility Split

### `Centerline3D`

Keep unchanged:

1. resolve point/tangent/frame at station
2. remain independent from display segmentation

### `Centerline3DDisplay`

New primary responsibilities:

1. build one continuous sampled wire for the main display
2. compute semantic split markers and diagnostics
3. own child `CenterlineBoundaryMarker` objects
4. expose counts / summary rows for marker sources

### `CenterlineBoundaryMarker`

New child display object:

1. one object per meaningful boundary station
2. geometry = short line crossing the centerline at that station
3. metadata:
   - `ParentCenterline3DDisplay`
   - `MarkerStation`
   - `MarkerKind`
   - `MarkerSources`

## Display Rules

### Main wire

1. always draw as one continuous wire
2. do not show segment breaks in the main object
3. if sampling is still not visually smooth enough, solve that by denser sampling, not by segment compounds

### Boundary markers

1. draw short cross-lines perpendicular to the local centerline tangent
2. default to internal semantic boundaries
3. start/end markers may stay optional
4. marker length should be adjustable on the parent display object

## Segment Source Policy

Boundary markers should be created from the merged split-station logic:

1. region boundaries
2. region transitions
3. structure boundaries
4. structure transitions
5. optional key stations when explicitly enabled

The parent display object can still keep `SegmentRows`, `SegmentSplitSourceSummary`,
and related diagnostics. The important change is that semantic splits become child
objects rather than visible breaks in the main wire shape.

## UX Policy

Task panel should explain the split clearly:

1. `3D Centerline` builds the main display wire
2. region/structure controls only add boundary markers and diagnostics
3. the visible main wire is not supposed to fragment into separate tree-level ranges

Suggested user-facing controls:

1. `Show Boundary Markers`
2. `Boundary Marker Length`
3. `Include Endpoint Markers`
4. existing region/structure segmentation toggles remain available

## Implementation Plan

## Current Status

1. `PR-1` completed
2. `PR-2` completed
3. `PR-3` completed
4. `PR-4` completed
5. `PR-5` completed
6. `PR-6` completed

### `PR-1` Object-split scaffolding

1. document the new main-wire vs boundary-marker model
2. add parent display properties for marker visibility / length / counts
3. add `CenterlineBoundaryMarker` child-object contract

### `PR-2` Main wire + child marker generation

1. make the main display shape one continuous wire again
2. keep segment-aware station planning internally
3. generate/update child boundary marker objects from merged split rows
4. show child markers under the main display in the tree

### `PR-3` Task-panel UX + diagnostics

1. expose marker visibility / length controls
2. update wording so users understand the main wire is continuous and markers show the splits
3. report marker count and split source summary in status/completion text
4. route boundary markers into the alignment tree so they can appear under the centerline object

### `PR-4` Tree/document integration + regression

1. harden tree ownership so child markers stay attached to the display object
2. add smoke coverage for:
   - marker object generation
   - parent-child linkage
   - unchanged station-based downstream behavior
3. add endpoint-marker option and marker-kind readability polish

### `PR-5` Alignment-root placement

1. move `3D Centerline` tree ownership from `VerticalProfiles` to the alignment root
2. keep boundary markers attached under `3D Centerline`
3. update tree-schema smoke coverage to lock the new ownership rule

### `PR-6` Dedicated tree branch + child-only markers

1. add `3D Centerline` as a first-class alignment-tree branch in the default schema
2. route `Centerline3DDisplay` into that branch
3. keep `CenterlineBoundaryMarker` objects out of project-folder ownership so they appear only as `3D Centerline` children

## Acceptance Criteria

1. `3D Centerline` remains one visible centerline object
2. semantic split locations are visible as child boundary-line objects
3. the tree makes split meaning easier to read than today
4. station-based engineering behavior remains unchanged
5. visual trust improves because the centerline itself no longer looks like a set of explicit segment objects
