# Typical Section Execution Plan

This document tracks the staged rollout of the `TypicalSectionTemplate` workflow.

## Status Summary

### Sprint A: Data Model
Status: complete

Completed:
- `TypicalSectionTemplate` object added
- component array properties added
- validation helpers added
- preview top-profile wire added

Key files:
- `freecad/Corridor_Road/objects/obj_typical_section_template.py`

### Sprint B: Editing UI
Status: complete

Completed:
- `Typical Section` task panel added
- command/menu/toolbar registration added
- component-table editing added
- component CSV import added

Key files:
- `freecad/Corridor_Road/ui/task_typical_section_editor.py`
- `freecad/Corridor_Road/commands/cmd_edit_typical_section.py`
- `freecad/Corridor_Road/init_gui.py`

### Sprint C: Project Integration
Status: complete

Completed:
- `TypicalSectionTemplate` project link added
- project-tree adoption/routing added
- alignment resolution for template objects added
- `ALN_Unassigned` fallback issue corrected for typical-section apply workflow

Key files:
- `freecad/Corridor_Road/objects/obj_project.py`

### Sprint D: SectionSet Integration
Status: complete

Completed:
- `SectionSet` link to `TypicalSectionTemplate`
- `UseTypicalSectionTemplate` toggle
- component-based top profile used during section-wire generation
- legacy `AssemblyTemplate` fallback retained

Key files:
- `freecad/Corridor_Road/objects/obj_section_set.py`

### Sprint E: Sections Panel Integration
Status: complete

Completed:
- `Use Typical Section Template` option in `Generate Sections`
- `Typical Section Source` selection
- project/SectionSet link persistence

Key files:
- `freecad/Corridor_Road/ui/task_section_generator.py`

### Sprint F: Earthwork-Oriented Components
Status: complete

Completed:
- `curb` step behavior
- `ditch` sag/V-style break behavior
- `berm` flat-platform behavior
- top-profile edge tracking for outer component types
- advanced component parameters for roadside work:
  - `ExtraWidth`
  - `BackSlopePct`
- advanced component usage count/result reporting

Current scope:
- `curb`, `ditch`, and `berm` stay within the current section-wire contract
- advanced parameters extend the profile shape without introducing a new corridor schema

Key files:
- `freecad/Corridor_Road/objects/obj_typical_section_template.py`
- `freecad/Corridor_Road/objects/obj_section_set.py`

### Sprint G: Consumer Stabilization
Status: functionally complete

Completed:
- `SectionSchemaVersion=2` for typical-section driven section output
- `TopProfileSource=typical_section`
- `TopProfileEdgeSummary` propagated to:
  - `SectionSet`
  - `Corridor`
  - `DesignGradingSurface`
- corridor completion dialog enriched with:
  - points per section
  - source section schema
  - top profile source
  - top profile edges
- automatic legacy ruled-fallback preference for richer typical-section edge conditions
- automatic retry when typical-section corridor surface assembly is unstable

Current scope:
- quality/stability focused
- not a new corridor geometry schema beyond current section-wire contract

Key files:
- `freecad/Corridor_Road/objects/obj_section_set.py`
- `freecad/Corridor_Road/objects/obj_corridor.py`
- `freecad/Corridor_Road/objects/obj_design_grading_surface.py`
- `freecad/Corridor_Road/ui/task_corridor_loft.py`

### Sprint H: Pavement Data (First Pass)
Status: complete

Completed:
- pavement layer data model added to `TypicalSectionTemplate`
- pavement layer table added to `Typical Section` task panel
- pavement CSV import added
- pavement summary results added:
  - `PavementLayerCount`
  - `EnabledPavementLayerCount`
  - `PavementTotalThickness`
- pavement preview offset wires added to `TypicalSectionTemplate`
- pavement summary propagated to:
  - `SectionSet`
  - `Corridor`
  - `DesignGradingSurface`
- `TypicalSectionPavementDisplay` now provides separate pavement geometry/report output
- pavement layer report rows now propagate downstream with the summary fields

Current scope:
- pavement layers are still not separate corridor solids
- pavement promotion currently stops at the display/report-object level and downstream reporting

Key files:
- `freecad/Corridor_Road/objects/obj_typical_section_template.py`
- `freecad/Corridor_Road/ui/task_typical_section_editor.py`
- `freecad/Corridor_Road/objects/obj_section_set.py`
- `freecad/Corridor_Road/objects/obj_corridor.py`
- `freecad/Corridor_Road/objects/obj_design_grading_surface.py`

### Sprint I: Samples and Documentation
Status: complete

Completed:
- sample component CSVs added:
  - `tests/samples/typical_section_basic_rural.csv`
  - `tests/samples/typical_section_urban_complete_street.csv`
  - `tests/samples/typical_section_with_ditch.csv`
- sample pavement CSV added:
  - `tests/samples/typical_section_pavement_basic.csv`
- user docs updated:
  - `README.md`
  - wiki pages
- developer docs updated:
  - `README_Codex.md`
  - `docs/ARCHITECTURE.md`
- wiki remote synchronized

### Sprint J: 3D Live Preview UX
Status: planned

Goal:
- allow users to edit `Typical Section` while directly seeing the section shape in the FreeCAD 3D view
- keep the implementation aligned with the existing `TypicalSectionTemplate` and `PavementDisplay` objects instead of introducing a separate preview subsystem

Design review:
- considered approaches:
  - `Task panel only` 2D preview:
    - simple
    - but does not satisfy the need to work in the 3D view directly
  - `Separate custom preview widget`:
    - flexible
    - but duplicates rendering logic and adds maintenance cost
  - `Use existing TypicalSectionTemplate + PavementDisplay objects as live preview`:
    - best fit for current architecture
    - reuses existing `Shape` generation
    - preserves tree/project integration
    - easiest to keep consistent with downstream `Sections`
- selected approach:
  - use `TypicalSectionTemplate` as the main preview object in the 3D view
  - keep `PavementDisplay` as the optional pavement overlay object
  - enhance the editor so these objects feel like live editing previews rather than apply-only outputs

Planned phases:

1. Preview visibility and naming baseline
- ensure the current template object is always easy to find in the tree
- keep preview naming simple and user-facing
- confirm `PavementDisplay` naming and visibility policy are consistent

2. Manual preview refresh controls
- add an explicit `Refresh Preview` action in `Edit Typical Section`
- make preview refresh cheaper than full downstream workflow recompute
- ensure `TypicalSectionTemplate` and `PavementDisplay` can refresh together

3. Auto preview during editing
- add an `Auto Preview` toggle in the task panel
- when enabled:
  - table edits
  - pair helper insertion
  - pavement edits
  trigger preview recompute for the active typical section
- use debounced refresh to avoid recompute on every keystroke

4. 3D readability improvements
- keep the main section preview as wireframe by default
- add optional preview fill / stronger display tint if needed
- preserve low visual noise so the section remains readable in the 3D scene
- keep pavement display independently togglable

5. Row-to-geometry feedback
- when a component row is selected in the table, visually emphasize the matching part of the preview
- scope:
  - first pass may use color emphasis or temporary line-weight emphasis
  - deeper per-component sub-shape highlighting can come later if the shape contract needs it

6. Safe recompute contract
- preview updates must not:
  - force `Sections`
  - force `Corridor`
  - force grading/terrain analysis
- only the local `TypicalSectionTemplate` and linked `PavementDisplay` should recompute during preview work

Planned user-facing options:
- `Show Preview Wire`
  - keep as the base visibility control
- `Auto Preview`
  - new editor toggle
- `Refresh Preview`
  - new editor button
- optional later follow-up:
  - `Show Pavement Preview`
  - `Preview Fill`

Planned key files:
- `freecad/Corridor_Road/ui/task_typical_section_editor.py`
- `freecad/Corridor_Road/objects/obj_typical_section_template.py`

Verification targets:
- editing rows updates the visible typical section preview in 3D
- pavement edits update `PavementDisplay` consistently
- preview refresh does not trigger unrelated downstream objects
- task panel remains responsive while editing

## Current Overall State

`Typical Section` is now usable as a real finished-grade top-profile source for:
- `Sections`
- `Corridor`
- `Design Grading Surface`

It currently supports:
- component editing
- component CSV import
- pavement layer editing
- pavement CSV import
- helper insertion for common roadside pairs
- preview wire
- separate pavement display/report geometry
- section/corridor/grading summary + pavement-report propagation
- planned next UX step:
  - 3D live preview-oriented editing around `TypicalSectionTemplate` + `PavementDisplay`

## Open Follow-up Work

1. pavement layers as true corridor solids or section-only faces if a later scope needs them
2. richer runtime validation on complex mixed workflows
3. broader sample CSV coverage for advanced roadside parameter combinations
4. `Typical Section` 3D live preview refresh/highlight workflow
