<!-- SPDX-License-Identifier: LGPL-2.1-or-later -->
<!-- SPDX-FileNotice: Part of the Corridor Road addon. -->

# Structure Section Execution Plan

## Purpose
This document breaks Phase 1 structure-in-sections work into concrete file-level tasks.

Phase 1 goal:
1. create a `StructureSet` object
2. edit/import structure records
3. connect `SectionSet` to `StructureSet`
4. merge structure stations into section generation
5. tag child sections with structure metadata

This phase now includes simple 3D structure visualization, but it still does not include
full template solids, external shape placement, or corridor boolean logic.

## Current Status Snapshot

Implemented:
1. `StructureSet` object
2. `Edit Structures` task panel and command
3. project-tree placement under `Inputs/Structures`
4. simple 3D display using alignment-based solids

Pending:
1. `SectionSet` integration
2. station merge logic
3. child section metadata/tags
4. template geometry
5. external shape placement

## Sprint Status

### Sprint 1
Status:
1. functionally complete

Completed:
1. `obj_structure_set.py`
2. `cmd_edit_structures.py`
3. `task_structure_editor.py`
4. `init_gui.py`
5. project-tree placement under `Inputs/Structures`
6. simple 3D structure display

Remaining validation:
1. automated syntax/compile verification
2. FreeCAD runtime regression check in a live document

## Deliverables

### Required deliverables
1. new `StructureSet` object type
2. new `Edit Structures` task panel and command
3. `SectionSet` integration with linked structure source
4. sample structure CSV
5. wiki/user documentation

### Nice-to-have in the same phase
1. section child overlay markers for structure zones
2. warnings for daylight + structure override combinations

## File-Level Work Plan

## A. New object: `StructureSet`

### New file
1. `freecad/Corridor_Road/objects/obj_structure_set.py`

### Responsibilities
1. define `StructureSet` proxy type
2. own structure-record list properties
3. validate list lengths and record consistency
4. provide normalized record-read helper methods
5. expose `Status`
6. provide simple 3D display shapes
7. later host geometry-mode expansion hooks

### Suggested contents
1. `ensure_structure_set_properties(obj)`
2. `class StructureSet`
3. `class ViewProviderStructureSet`
4. helper methods such as:
   - `records(obj)`
   - `validate(obj)`
   - `active_records_at_station(obj, s)`
   - `structure_key_stations(obj, include_start_end=True, include_centers=True, before=0.0, after=0.0)`
   - `build_display_shape(obj, alignment_obj)`

### Acceptance criteria
1. object can be created in an empty document
2. properties are initialized safely
3. invalid record arrays produce readable status text
4. basic structure solids are visible in 3D when alignment data exists

## B. New UI: `Edit Structures`

### New files
1. `freecad/Corridor_Road/ui/task_structure_editor.py`
2. `freecad/Corridor_Road/commands/cmd_edit_structures.py`

### Responsibilities
1. table-based editing for structure rows
2. add/remove/sort rows
3. create or update `StructureSet`
4. optional CSV import
5. attach object to project tree
6. show completion or validation messages
7. support future geometry-mode fields without redesigning the panel

### Recommended table columns
1. `Id`
2. `Type`
3. `StartStation`
4. `EndStation`
5. `CenterStation`
6. `Side`
7. `Offset`
8. `Width`
9. `Height`
10. `BottomElevation`
11. `Cover`
12. `RotationDeg`
13. `BehaviorMode`
14. `Notes`

### Minimum UI actions
1. `Add Row`
2. `Remove Row`
3. `Sort by Station`
4. `Import CSV`
5. `Apply`

### Acceptance criteria
1. user can create a `StructureSet` from scratch
2. user can reopen the panel and edit existing rows
3. project tree places the structure object under `Inputs/Structures`
4. wide structure tables remain usable with horizontal scrolling

## C. Command and workbench registration

### Files to modify
1. `freecad/Corridor_Road/init_gui.py`
2. `freecad/Corridor_Road/commands/cmd_edit_structures.py`

### Work
1. import/register the new command
2. add `CorridorRoad_EditStructures` to toolbar/menu
3. place it near `Project Setup` / terrain / alignment input commands

### Recommended menu position
1. `New Project`
2. `Project Setup`
3. `PointCloud DEM`
4. `Edit Structures`
5. `Alignment`

### Acceptance criteria
1. workbench shows the new command in toolbar and menu
2. command opens the structure editor task panel

## D. Project linking and tree adoption

### Files to modify
1. `freecad/Corridor_Road/objects/obj_project.py`
2. `freecad/Corridor_Road/objects/project_links.py`

### Work
1. add hidden project link property:
   - `StructureSet`
2. teach `CorridorRoadProject.auto_link(...)` how to find the first `StructureSet`
3. teach target-container resolution to classify `StructureSet` into `Inputs/Structures`
4. ensure `link_project(...)` can adopt the object like other pipeline objects

### Acceptance criteria
1. newly created `StructureSet` is linked to project
2. project tree places it in the correct folder
3. no duplicate root placement appears

## E. SectionSet property integration

### Files to modify
1. `freecad/Corridor_Road/objects/obj_section_set.py`
2. `freecad/Corridor_Road/ui/task_section_generator.py`

### New `SectionSet` properties
1. `StructureSet`
2. `UseStructureSet`
3. `IncludeStructureStartEnd`
4. `IncludeStructureCenters`
5. `StructureBufferBefore`
6. `StructureBufferAfter`
7. `CreateStructureTaggedChildren`
8. `ApplyStructureOverrides`
9. `ResolvedStructureCount`
10. `ResolvedStructureTags`

### UI additions in `Generate Sections`
1. `Use StructureSet`
2. `Structure Source`
3. `Include start/end stations`
4. `Include center stations`
5. `Buffer before`
6. `Buffer after`
7. `Create structure-tagged child sections`
8. `Apply structure overrides`

### UI compatibility policy
1. keep legacy `Include Structure/Crossing Key Stations`
2. keep `Structure/Crossing Stations` text box
3. if `UseStructureSet=True`, prefer linked structure source
4. if `UseStructureSet=False`, legacy text workflow remains available

### Acceptance criteria
1. `Generate Sections` can select a `StructureSet`
2. settings persist to the `SectionSet` object
3. old manual station-text workflow still works

## F. Geometry mode expansion

### Main files
1. `freecad/Corridor_Road/objects/obj_structure_set.py`
2. `freecad/Corridor_Road/ui/task_structure_editor.py`

### New structure fields to plan for
1. `GeometryMode`
2. `TemplateName`
3. `ShapeSourcePath`
4. `ScaleFactor`

### Supported geometry stages
1. `box`
   - current simple 3D placeholder
2. `template`
   - parametric structure library geometry
3. `external_shape`
   - placed external STEP/BREP/FreeCAD geometry

### Acceptance criteria
1. geometry strategy is explicit per structure record
2. current `box` mode remains backward compatible
3. later `template` and `external_shape` can be added without changing `SectionSet` logic

## G. Station merge logic

### Main file
1. `freecad/Corridor_Road/objects/obj_section_set.py`

### Work
1. update station resolution logic to merge:
   - structure start station
   - structure end station
   - structure center station
   - optional before/after buffer stations
2. keep final station list sorted and deduplicated
3. expose `ResolvedStructureCount`
4. expose `ResolvedStructureTags`

### Suggested integration points
1. `resolve_station_values(...)`
2. `resolve_station_tags(...)`

### Acceptance criteria
1. structure stations appear deterministically in generated section list
2. buffer stations are added only when configured
3. duplicate stations do not create unstable repeats

## H. Child section metadata

### Main file
1. `freecad/Corridor_Road/objects/obj_section_set.py`

### Work
When rebuilding child sections, add properties such as:
1. `HasStructure`
2. `StructureIds`
3. `StructureTypes`
4. `StructureRole`

### Example roles
1. `normal`
2. `structure_start`
3. `structure_center`
4. `structure_end`

### Acceptance criteria
1. child sections in the tree show structure-aware labels or tags
2. metadata is inspectable in property view
3. non-structure sections remain clean

## I. Optional overlay behavior

### Main file
1. `freecad/Corridor_Road/objects/obj_section_set.py`

### Phase 1 recommendation
Keep this lightweight.

Allowed Phase 1 behaviors:
1. attach structure tags to section labels
2. add simple overlay points/segments for structure envelope visualization

Do not yet:
1. modify corridor loft logic based on structures
2. perform boolean or mesh clipping

### Acceptance criteria
1. structure zones are visually identifiable in section children
2. normal corridor generation remains unaffected

## J. CSV import support for structures

### New or modified files
1. `freecad/Corridor_Road/ui/task_structure_editor.py`
2. optional helper module:
   - `freecad/Corridor_Road/ui/common/structure_csv.py`

### Recommended CSV header
`Id,Type,StartStation,EndStation,CenterStation,Side,Offset,Width,Height,BottomElevation,Cover,RotationDeg,BehaviorMode,Notes,GeometryMode,TemplateName,ShapeSourcePath,ScaleFactor`

### Acceptance criteria
1. a valid CSV can populate the table
2. invalid rows are skipped or warned clearly
3. import does not crash on blanks or partial optional fields

## K. Samples and tests

### New sample files
1. `tests/samples/structures_basic.csv`
2. optional paired sample:
   - `tests/samples/structures_realistic_hilly.csv`

### Recommended sample contents
1. one culvert crossing
2. one retaining wall zone
3. one bridge/abutment zone

### Test targets
1. station merge correctness
2. child section structure tags
3. project-tree placement
4. backward compatibility of legacy structure station text
5. basic 3D structure display generation
6. geometry-mode fallback behavior

### Candidate test files
1. `tests/test_structure_set_basic.py`
2. `tests/test_section_structure_station_merge.py`
3. `tests/test_project_structure_adoption.py`

## L. Documentation

### Files to modify
1. `docs/ARCHITECTURE.md`
2. `README_Codex.md`
3. `docs/wiki/Menu-Reference.md`
4. `docs/wiki/Workflow.md`
5. `docs/wiki/CSV-Format.md`
6. `docs/wiki/Troubleshooting.md`

### Documentation work
1. describe `StructureSet`
2. explain `Edit Structures`
3. explain how `Generate Sections` uses structure data
4. define structure CSV format
5. define section tagging behavior
6. explain `box -> template -> external_shape` roadmap

## Suggested Implementation Order

## Sprint 1
1. `obj_structure_set.py`
2. `cmd_edit_structures.py`
3. `task_structure_editor.py`
4. `init_gui.py`

Done when:
1. user can create/edit a `StructureSet`
2. object appears in `Inputs/Structures`
3. simple structure solids appear in 3D

Current state:
1. completed functionally
2. verification follow-up still recommended

## Sprint 2
1. `obj_project.py`
2. `project_links.py`
3. `obj_section_set.py`
4. `task_section_generator.py`

Done when:
1. `SectionSet` can reference `StructureSet`
2. structure stations are merged into section generation

## Sprint 3
1. child section metadata
2. optional structure overlay
3. samples/tests
4. docs/wiki

Done when:
1. structure-tagged sections are visible
2. sample workflow is documented and reproducible

## Sprint 4
Status:
1. functionally complete

1. `GeometryMode` property integration
2. `template` geometry for `box_culvert`
3. `template` geometry for `retaining_wall`
4. UI support for template-specific fields

Done when:
1. at least two reusable parametric structure templates exist
2. users can choose between simple box and template geometry

Completed:
1. `StructureSet` supports `GeometryMode` and template-specific parameters
2. `box_culvert` template geometry is available for 3D structure display
3. `retaining_wall` template geometry is available for 3D structure display
4. `Structure Sections` overlays now reflect template-aware cross-section shapes
5. `Edit Structures` and CSV import support template fields

Remaining validation:
1. runtime tuning of culvert wall/cell display proportions
2. user-document calibration for when `box` is still preferable to `template`

## Sprint 5
Status:
1. functionally complete

1. external shape reference/path support
2. placement/orientation/scaling rules
3. import and validation messaging

Done when:
1. complex structures can be placed from external models
2. alignment-based placement remains consistent

Completed:
1. `GeometryMode=external_shape` supports `.step` / `.brep`
2. `GeometryMode=external_shape` supports `.FCStd#ObjectName`
3. external shape placement supports scale, placement mode, and source-base-bottom policy
4. `Edit Structures` exposes browse/status/color feedback for external shape paths
5. frame-placement diagnostics are reported for `centerline3d` vs `alignment` fallback

Remaining validation:
1. live FreeCAD runtime verification for multiple `.FCStd` object naming cases
2. optional UI enhancement for explicit FCStd object picker

## Sprint 6
1. corridor-mode fields in `StructureSet`
2. `skip_zone` implementation in `Corridor`
3. status/result reporting for skipped structure ranges
4. UI exposure for corridor structure handling

Done when:
1. corridor solids can omit structure-active spans intentionally
2. structure-aware segmented loft remains stable outside skipped ranges
3. results clearly report which station ranges were skipped

## Sprint 7
Status:
1. functionally complete

1. notch-aware section schema design
2. notch profile generation for `culvert` / `crossing`
3. transition-station driven notch ramping
4. boolean cut remains optional/later and is no longer required for the first notch-capable workflow

Done when:
1. first notch-capable corridor workflow exists without relying on boolean cut
2. notch transition remains loft-safe and reproducible

Completed:
1. `Corridor` can build notch-aware closed profiles for `culvert` and `crossing`
2. notch ramping follows structure transition stations
3. result reporting includes closed-profile schema version and notch-aware station count

Remaining validation:
1. FreeCAD runtime tuning for notch proportions in real projects
2. follow-up UI/document calibration for abutment and bridge-zone user guidance

## Definition Of Done For Phase 1
1. `Edit Structures` exists and is usable
2. `StructureSet` is stored in project tree
3. `Generate Sections` can use structure records directly
4. generated child sections contain structure tags/metadata
5. a sample structure CSV is included
6. docs explain the workflow clearly

## Definition Of Done For Geometry Expansion
1. `GeometryMode` is explicit in the data model
2. `box` remains the safe fallback
3. `template` supports at least culvert and retaining wall
4. `external_shape` placement works with clear source-path rules

## Definition Of Done For Corridor-Level Structure Consumption
1. `split_only` remains the safe default
2. `skip_zone` works for structure-active spans with readable status output
3. notch-capable profiles use an explicit schema instead of hidden point-count mutations
4. boolean cut stays opt-in and has a graceful fallback path

## Recommended First Coding Task
Start with:
1. `obj_structure_set.py`
2. `cmd_edit_structures.py`
3. `task_structure_editor.py`

Reason:
1. it creates the source-of-truth object first
2. it avoids mixing UI and section-generation changes too early
3. it gives something inspectable before section logic is modified
