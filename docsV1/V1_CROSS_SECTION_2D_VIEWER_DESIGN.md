# CorridorRoad V1 Cross Section 2D Viewer Design

Date: 2026-04-28
Status: Draft detail plan
Depends on:

- `docsV1/V1_REVIEW_VIEWER_ROLE_DECISION.md`
- `docsV1/V1_CROSS_SECTION_VIEWER_EXECUTION_PLAN.md`
- `docsV1/V1_SECTION_OUTPUT_SCHEMA.md`

## 1. Purpose

This document defines the detailed direction for making `Cross Section Viewer` a station-by-station 2D section review screen.

## 2. Scope

The first redesign focuses on:

- dominant 2D section drawing
- station navigation
- FG and EG line review
- pavement, subgrade, side slope, ditch, and drainage display
- source and diagnostic support panels

## 3. Core Rule

The 2D section drawing is the main product experience.

Tables support the drawing.

Tables do not replace the drawing.

The v1 viewer should preserve the successful v0 drawing-style experience:

- section geometry is presented like a 2D engineering section drawing, not as a small chart
- component labels and values are drawn on or near their owning section spans
- width, depth, and overall section dimensions are shown as dimension annotations
- the lower dimension band remains part of the review contract
- label/value rows should use drawing-rule placement to avoid clutter
- exportable drawing payloads should remain possible after the v1 payload contract stabilizes

The v1 reset changes the data ownership, not the expected visual language.

The v0 viewer can be used as the visual behavior reference.

The v1 viewer must not reuse v0 `SectionSet` as source truth for new behavior.

## 4. Main User Questions

The viewer should answer:

- Is this station's cross section correct?
- Where are EG and FG?
- Are side slopes and ditches shaped correctly?
- Are pavement and subgrade layers visible?
- Which Assembly and Region produced the result?
- What needs to be edited if this station is wrong?

## 5. Required Inputs

Minimum inputs:

- `SectionOutput.geometry_rows`
- `SectionOutput.component_rows`
- `SectionOutput.quantity_rows`
- focused station row
- source inspector payload

High-value inputs:

- TIN sampled EG line
- corridor build result rows
- drainage/ditch component rows
- earthwork area rows
- diagnostics rows

## 6. UI Layout

Recommended layout:

1. Station navigation bar
2. Large 2D section canvas
3. Compact status strip
4. Lower detail tabs

Station navigation bar:

- `Review Navigation Stations`
- `Focus Previous`
- `Focus Selected`
- `Focus Next`
- station entry or selected-station combo

2D canvas:

- fills most of the panel
- shows offset on the horizontal axis
- shows elevation on the vertical axis
- supports auto-scale to visible section geometry
- uses distinct styles for FG, EG, subgrade, ditch, drainage, and structure context
- draws a centerline reference marker
- draws component labels and values at component span midpoints when available
- draws dimension guides in a lower band
- uses collision-aware placement for labels and dimension text
- keeps labels readable in dark mode

Lower detail tabs:

- Components
- Terrain
- Corridor Results
- Quantities / Earthwork
- Diagnostics
- Source / Handoff

## 7. Drawing Style

Initial style:

- FG: strong warm line
- EG: green terrain line
- subgrade: muted dashed or lower line
- pavement/layers: filled or banded polygons when available
- ditch/drainage: cyan or blue section shape
- structure influence: amber or gray marker region

The style should remain readable in dark mode.

Drawing annotation requirements:

- `lane`, `shoulder`, `ditch`, `slope`, `subgrade`, and drainage labels should be readable without opening tables
- component value rows should appear near their component labels when there is enough room
- ditch annotations should include shape-specific dimensions when available, such as bottom width and depth
- slope annotations should show side and slope meaning, not only generic linework
- daylight markers should be visually distinct from ordinary component labels
- the overall section width dimension should be available in the lower band
- component width dimensions should remain visible when `Show dimensions` is enabled

The first v1 implementation may start with FG, subgrade, ditch, and slope-face annotations from `AppliedSectionSet`.

EG/TIN terrain annotation can be layered after the v1 section drawing payload is stable.

## 8. User Actions

Required first actions:

- navigate station
- inspect section drawing
- double-click corridor result row to focus 3D preview object
- open source editor from handoff buttons

Deferred actions:

- section annotation editing
- direct geometry editing
- custom section bookmarks

## 9. Diagnostics

Diagnostics should explain:

- missing EG line
- missing FG/design line
- no applied section at selected station
- missing corridor build result
- unresolved Assembly or Region reference
- TIN no-hit condition
- side-slope or ditch generation issue

## 10. Non-Goals

The 2D viewer does not edit generated section geometry.

The 2D viewer does not replace Assembly, Region, Profile, or TIN editors.

The 2D viewer does not generate final sheets.

## 11. Implementation Milestones

1. Define `CrossSectionDrawingPayload` from v1 `AppliedSectionSet`.
2. Map station-local `AppliedSectionPoint` rows into offset/elevation drawing geometry.
3. Generate drawing spans for FG, subgrade, ditch, drainage, and slope-face review.
4. Generate label rows and dimension rows from the drawing spans.
5. Reuse v0-style drawing-rule placement for labels, values, and lower-band dimensions.
6. Replace the small preview widget with a dominant 2D section canvas.
7. Move supporting tables into tabs.
8. Add dark-mode-readable FG/EG/layer styles.
9. Add offset/elevation axes and scale labels.
10. Add missing-data empty states.
11. Layer EG/TIN section sampling after v1 section geometry is stable.
12. Validate against a real corridor build document.

## 12. V0 Behavior To Preserve

The following v0 viewer behaviors should be treated as visual requirements for v1:

- large `QGraphicsView`-based 2D drawing canvas
- pan and zoom behavior
- station selector and previous/next navigation
- `Show dimensions`
- component labels and values drawn in the section drawing
- lower-band dimension strategy
- SVG/PNG export path after the payload stabilizes
- focused component highlighting
- daylight marker labeling
- structure overlay capability as a later layer

These behaviors should be reconnected to v1 payloads.

They should not cause new v1 code to depend on v0 source objects as authoritative design state.
