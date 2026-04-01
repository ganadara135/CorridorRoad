<!-- SPDX-License-Identifier: LGPL-2.1-or-later -->
<!-- SPDX-FileNotice: Part of the Corridor Road addon. -->

# Cross Section Viewer Execution Plan

Date: 2026-04-01

Current implementation status:

- `Priority 1` initial delivery is now in progress in the codebase.
- Added:
  - `SectionSet.resolve_viewer_station_rows(...)`
  - `SectionSet.resolve_viewer_payload(...)`
  - `CorridorRoad_ViewCrossSection`
  - `task_cross_section_viewer.py`
- The first shipped scope is `station selector + previous/next + fit view + section wire + optional structure overlay + 3D selection sync`.
- The next shipped scope now also includes:
  - `Show labels`
  - `Show dimensions`
  - `Show diagnostics`
  - `Export PNG`
  - `Export SVG`
  - `Export Sheet SVG`
- Detailed follow-up layout planning is tracked separately in [CROSS_SECTION_VIEWER_LAYOUT_PLAN.md](/c:/Users/ganad/AppData/Roaming/FreeCAD/Mod/CorridorRoad/docs/CROSS_SECTION_VIEWER_LAYOUT_PLAN.md).
- The next layout-focused follow-up is now partially shipped:
  - `vertical component labels`
  - `span-fit font sizing`
  so narrow cross-section components remain readable without forcing every label into horizontal full-size text.
- The current follow-up direction is now refined further:
  - remove `Reach` from the main drawing
  - promote `actual component subdivision guides`
  - keep `component labels vertical by default`
  - move `dimension rows` farther below the section line

## Goal

Provide a practical cross-section review workflow so users can inspect each section as a full road cross-section drawing, not just as a 3D wire in the model.

Recommended direction:

1. `3D view` keeps the role of section-location context and station selection.
2. A separate `Cross Section Viewer` window becomes the main place to read the full section drawing.
3. The two views should stay synchronized.

This means the target architecture is a hybrid workflow:

- `3D view` for navigation, context, and picking the active station
- `2D viewer window` for readable section drawing, labels, and later dimensions/export

## Why Hybrid Is Recommended

`3D view` is already good at showing where a section lives along the corridor.
It is not ideal for reading a full cross-section like a sheet or profile drawing.

A dedicated 2D viewer is better for:

- road element labels
- bench / ditch / berm / curb interpretation
- daylight end reading
- structure overlay reading
- dimensions and export later

## Priority 1

### Objective

Deliver the first usable cross-section viewer that can show one section at a time as a clean 2D drawing.

### Scope

- New `Cross Section Viewer` task panel or dock window
- Station selector
- Previous / Next station buttons
- Fit-to-view
- Basic 2D rendering of section wire
- Optional structure overlay rendering
- 3D selection -> viewer synchronization

### Main UX

1. User runs `Generate Sections`
2. User opens `Cross Section Viewer`
3. Viewer lists available section stations
4. User chooses one station
5. Viewer renders the section in 2D
6. If a `SectionSlice` is selected in tree or 3D, the viewer follows that station

### Data Contract

Use `SectionSet` as the source of truth.

Needed viewer input contract per station:

- `station`
- `base_wire_points`
- `structure_overlay_wire_points`
- `station_tags`
- `structure_summary`

Recommended implementation shape:

- add a helper in `obj_section_set.py`
- example name: `SectionSet.resolve_viewer_section_payload(obj, station)`

The first payload can stay minimal:

- ordered 2D points in section local coordinates
- optional overlay wires
- metadata strings

### Implementation Tasks

1. Add a section-payload builder in [obj_section_set.py](/c:/Users/ganad/AppData/Roaming/FreeCAD/Mod/CorridorRoad/freecad/Corridor_Road/objects/obj_section_set.py)
2. Create a new viewer UI under `freecad/Corridor_Road/ui/`
3. Use `QGraphicsView` for first-pass 2D drawing
4. Draw:
   - base section polyline
   - centerline marker
   - optional structure overlay polyline
5. Add station navigation controls
6. Add selection sync from `SectionSlice`
7. Add one smoke test for payload contract

### Validation Criteria

- Viewer opens without GUI layout breakage
- One selected station renders consistently
- `SectionSlice` selection can drive the active station
- Bench and side-slope breakpoints are visible in the 2D linework
- Structure overlay appears when present

### Out Of Scope

- dimensions
- print layout
- SVG/PNG export
- EG/FG dual rendering
- area calculations

## Priority 2

### Objective

Turn the basic viewer into a practical review tool with readable road-element interpretation.

### Scope

- element labels
- style controls
- EG / FG overlay support
- component-aware highlighting
- bench / daylight / structure diagnostics in the viewer

### Main UX

The user should be able to answer these questions quickly:

- where is the lane / shoulder / median / ditch / berm
- where does daylight hit
- where is a bench inserted
- where does a structure affect the section

### Data Contract Expansion

Add viewer-friendly semantic rows:

- `component_rows`
- `bench_rows`
- `daylight_rows`
- `structure_rows`

Recommended result shape:

- `kind=component`
- `kind=bench`
- `kind=daylight`
- `kind=structure`

This can reuse the structured-report style already used elsewhere in the workbench.

### Implementation Tasks

1. Expand `SectionSet` payload builder with semantic rows
2. Add viewer toggles:
   - `Show Labels`
   - `Show Structure Overlay`
   - `Show EG`
   - `Show FG`
   - `Show Daylight Markers`
3. Add styled drawing layers:
   - road top
   - side slopes
   - benches
   - terrain line
   - structure overlays
4. Add hover/selection feedback for components in the 2D viewer
5. Add a small station summary panel in the viewer
6. Add regression for semantic payload rows

### Validation Criteria

- Bench and multi-bench sections are readable in 2D
- Daylight hit is visually distinguishable
- Structure-affected sections can be identified without reading raw status strings
- Typical-section derived top profile and simple assembly profile both display correctly

### Out Of Scope

- full dimensioning engine
- plotting/sheet output
- persistent annotations

## Priority 3

### Objective

Promote the viewer from inspection tool to deliverable-oriented section review workspace.

### Scope

- dimensions
- station title block
- export image/vector
- print-style layout
- optional section sheet templates
- area and width summaries

### Main UX

Users should be able to use the viewer for:

- design review
- internal checking
- image export
- later report/sheet generation

### Implementation Tasks

1. Add dimension rendering:
   - carriageway width
   - shoulder width
   - ditch / berm / bench widths
   - overall width
2. Add annotation layout rules:
   - title
   - station text
   - key labels
3. Add export commands:
   - `Export PNG`
   - `Export SVG`
   - `Export Sheet SVG`
4. Add optional print-frame mode
5. Add summary text block:
   - top width
   - pavement thickness
   - daylight side summary
   - structure summary
6. Add regression for export payload and drawing summary

### Validation Criteria

- exported image matches viewer content
- labels do not overlap excessively on common sample cases
- dimension text remains readable at common scales
- output works for simple, typical-section, structure, and bench cases

### Out Of Scope

- full CAD drafting replacement
- sheet set manager
- automatic multi-sheet production

## Technical Notes

### Recommended Rendering Strategy

Use a dedicated 2D scene, not the 3D view, for the main section drawing.

Recommended stack:

1. `SectionSet` builds section payload
2. viewer converts payload to 2D graphics items
3. 3D selection only changes the active station

### Why Not 3D-Only

`SectionSlice` in 3D is useful, but not enough for:

- readable labels
- dimensions
- print/export
- fast interpretation of dense sections

### Why `QGraphicsView` First

It is enough for:

- polylines
- markers
- text labels
- zoom/pan/fit

without introducing a heavier drawing framework too early.

## Suggested File Targets

- new UI:
  - `freecad/Corridor_Road/ui/task_cross_section_viewer.py`
- new command:
  - `freecad/Corridor_Road/commands/cmd_view_cross_section.py`
- source payload extension:
  - [obj_section_set.py](/c:/Users/ganad/AppData/Roaming/FreeCAD/Mod/CorridorRoad/freecad/Corridor_Road/objects/obj_section_set.py)
- docs:
  - [ARCHITECTURE.md](/c:/Users/ganad/AppData/Roaming/FreeCAD/Mod/CorridorRoad/docs/ARCHITECTURE.md)
  - [Menu-Reference.md](/c:/Users/ganad/AppData/Roaming/FreeCAD/Mod/CorridorRoad/docs/wiki/Menu-Reference.md)
  - [Workflow.md](/c:/Users/ganad/AppData/Roaming/FreeCAD/Mod/CorridorRoad/docs/wiki/Workflow.md)

## Recommended Delivery Order

1. Priority 1
2. Priority 2
3. Priority 3

Do not start with dimensions or export first.
The core success condition is: users can reliably open one station and read the whole section clearly.
