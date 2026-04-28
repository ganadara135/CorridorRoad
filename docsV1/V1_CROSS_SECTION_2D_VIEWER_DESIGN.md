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

1. Rename navigation controls to match v1 review language.
2. Replace the small preview widget with a dominant 2D section canvas.
3. Move supporting tables into tabs.
4. Add dark-mode-readable FG/EG/layer styles.
5. Add offset/elevation axes and scale labels.
6. Add missing-data empty states.
7. Validate against a real corridor build document.
