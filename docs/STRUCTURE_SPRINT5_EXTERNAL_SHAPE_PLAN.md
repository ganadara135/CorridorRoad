<!-- SPDX-License-Identifier: LGPL-2.1-or-later -->
<!-- SPDX-FileNotice: Part of the Corridor Road addon. -->

# Sprint 5: External Shape Placement Plan

This sprint adds external geometry placement for structures that are too complex to express
with the current `box` and `template` modes.

Primary goal:
1. place `STEP`, `BREP`, or existing `FreeCAD` shape geometry at structure stations
2. keep placement rules consistent with `Structure Sections` and `Centerline3D`
3. keep `box` and `template` as safe fallbacks when external geometry fails

This sprint is about external structure display and placement.
It does not require full corridor boolean consumption in the first pass.

## Scope

In scope:
1. `GeometryMode = external_shape`
2. source-path support for `STEP`, `BREP`, and native document shape references
3. placement at station/offset/rotation using the same frame policy as `StructureSet`
4. validation/status reporting when the source cannot be loaded
5. sample workflow and CSV support

Out of scope for first pass:
1. persistent import caching across sessions
2. automatic corridor boolean cut from imported shapes
3. editing external geometry inside `Edit Structures`
4. deep unit-conversion inference from arbitrary CAD files

## Target User Story

1. user defines a structure row in `Edit Structures`
2. user sets `GeometryMode = external_shape`
3. user provides either:
   - `ShapeSourcePath`
   - or a `FreeCAD` object reference mode later
4. user clicks `Apply`
5. structure appears in the 3D model at the same station/frame used by `Structure Sections`

## Data Model Additions

Add these properties to `StructureSet`:
1. `ShapeSourcePaths` (`App::PropertyStringList`)
2. `ScaleFactors` (`App::PropertyFloatList`)
3. `PlacementModes` (`App::PropertyStringList`)
4. `UseSourceBaseAsBottom` (`App::PropertyBoolList`)
5. `ResolvedShapeSourceKinds` (`App::PropertyStringList`)

Recommended row-level meaning:
1. `ShapeSourcePath`
   - path to external `STEP`, `BREP`, or optionally `.FCStd` source
2. `ScaleFactor`
   - multiplicative shape scale
   - default `1.0`
3. `PlacementMode`
   - first pass recommended values:
     - `center_on_station`
     - `start_on_station`
4. `UseSourceBaseAsBottom`
   - when true, the source shape's local bottom is aligned to resolved `z0`
   - when false, the source shape origin is placed directly at the resolved station frame
5. `ResolvedShapeSourceKind`
   - runtime result:
     - `step`
     - `brep`
     - `fcstd_link`
     - `invalid`

## Placement Rules

The most important rule is consistency with existing section generation.

Placement frame priority:
1. `Centerline3D.frame_at_station(...)`
2. `HorizontalAlignment` fallback

Placement station:
1. if `PlacementMode = center_on_station`, use `CenterStation`
2. else if start/end exist and `PlacementMode = start_on_station`, use `StartStation`
3. else fallback to current `_station_for_record(...)`

Placement axes:
1. `T` = centerline tangent
2. `N` = left/right normal
3. `Z` = global up

Placement origin:
1. start from the loaded source shape in its local coordinates
2. apply scale
3. determine a local reference point:
   - center or start-based longitudinal reference
   - bottom or raw origin vertical reference
4. transform shape into the station frame
5. apply row `Offset` along `N`
6. apply row `RotationDeg` around `Z`

Z resolution:
1. if `BottomElevation` is set, use it
2. else if `Cover` is set, derive `z0 = z_ref - cover - source_height`
3. else use frame point `z`

## Source Loading Policy

First-pass supported formats:
1. `.step`
2. `.stp`
3. `.brep`
4. `.brp`

Optional second pass:
1. `.FCStd` shape extraction by object name or link syntax

Recommended loader behavior:
1. normalize path
2. confirm file exists
3. load shape with `Part.read(...)` when possible
4. reject null/invalid shapes
5. if load fails:
   - add a status note
   - fallback to `box` display geometry if width/height data exists

## UI Plan

File:
1. `freecad/Corridor_Road/ui/task_structure_editor.py`

New columns:
1. `ShapeSourcePath`
2. `ScaleFactor`
3. `PlacementMode`
4. `UseSourceBaseAsBottom`

Recommended UI behavior:
1. when `GeometryMode != external_shape`, these columns stay visible but de-emphasized
2. when `GeometryMode = external_shape`, source-path-related columns become the primary editable fields
3. add a `Browse Shape` helper button later if needed, but it is not mandatory for first pass

Type recommendations:
1. keep current template recommendations for built-in types
2. do not auto-switch to `external_shape`
3. let the user opt into it explicitly

## Execution Breakdown

### Task 5.1
Extend `StructureSet` data model.

Files:
1. `freecad/Corridor_Road/objects/obj_structure_set.py`

Work:
1. add list properties for external-shape fields
2. extend `records(...)`
3. extend validation rules

Done when:
1. structure rows can carry external-shape metadata without breaking old rows

### Task 5.2
Add source loading helpers.

Files:
1. `freecad/Corridor_Road/objects/obj_structure_set.py`

Work:
1. implement `_load_external_shape(path)`
2. implement `_transform_external_shape(shape, frame, rec, ...)`
3. add safe fallback to `box` geometry

Done when:
1. a valid `STEP` or `BREP` file can become a placed solid

### Task 5.3
Integrate external placement into structure display execution.

Files:
1. `freecad/Corridor_Road/objects/obj_structure_set.py`

Work:
1. route `GeometryMode = external_shape` to the new loader/placer
2. keep `box` and `template` behavior unchanged
3. add status notes for source kind and fallback path

Done when:
1. mixed datasets with `box`, `template`, and `external_shape` all render together

### Task 5.4
Expose editing fields in `Edit Structures`.

Files:
1. `freecad/Corridor_Road/ui/task_structure_editor.py`

Work:
1. add columns for source path and scale
2. add placement-mode combo
3. make CSV import/export recognize the new fields

Done when:
1. user can define an external-shape structure entirely from the task panel

### Task 5.5
Add samples and documentation.

Files:
1. `tests/samples/`
2. `README.md`
3. `docs/wiki/CSV-Format.md`
4. `docs/wiki/Menu-Reference.md`
5. `docs/wiki/Workflow.md`

Work:
1. provide at least one sample row for `external_shape`
2. document supported formats and path rules
3. explain fallback behavior

Done when:
1. a user can reproduce the workflow from docs without code reading

### Task 5.6
Validation and runtime checks.

Files:
1. `freecad/Corridor_Road/objects/obj_structure_set.py`
2. optional lightweight test/docs support

Work:
1. report invalid path
2. report invalid shape
3. report fallback-to-box
4. confirm placement uses the same centerline/frame policy as sections

Done when:
1. failures are diagnosable from `Status` without guessing

## Acceptance Criteria

Sprint 5 is functionally complete when:
1. `GeometryMode = external_shape` works in `Edit Structures`
2. `STEP` and `BREP` placement both work
3. external shapes use the same station frame policy as structure sections
4. invalid source files do not break document recompute
5. fallback behavior is visible in `Status`
6. documentation and a sample workflow exist

## Risks To Watch

1. external CAD files may come with arbitrary local origins
2. some source geometry may not be solids
3. source units may not match project expectations
4. document recompute can become slow if the same file is reloaded many times

Mitigation:
1. keep scale explicit
2. keep placement mode explicit
3. keep `box` fallback
4. report source kind and fallback use in `Status`

## Recommended First Implementation Order

1. Task 5.1 data model
2. Task 5.2 loader and transform helpers
3. Task 5.3 structure display integration
4. Task 5.4 task-panel and CSV exposure
5. Task 5.5 samples/docs
6. Task 5.6 validation pass
