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
  - `CorridorLoft`
  - `DesignGradingSurface`
- corridor completion dialog enriched with:
  - points per section
  - source section schema
  - top profile source
  - top profile edges
- automatic ruled-loft preference for richer typical-section edge conditions
- automatic ruled retry when typical-section lofting is unstable

Current scope:
- quality/stability focused
- not a new corridor geometry schema beyond current section-wire contract

Key files:
- `freecad/Corridor_Road/objects/obj_section_set.py`
- `freecad/Corridor_Road/objects/obj_corridor_loft.py`
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
  - `CorridorLoft`
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
- `freecad/Corridor_Road/objects/obj_corridor_loft.py`
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

## Current Overall State

`Typical Section` is now usable as a real finished-grade top-profile source for:
- `Sections`
- `Corridor Loft`
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

## Open Follow-up Work

1. pavement layers as true corridor solids or section-only faces if a later scope needs them
2. richer runtime validation on complex mixed workflows
3. broader sample CSV coverage for advanced roadside parameter combinations
