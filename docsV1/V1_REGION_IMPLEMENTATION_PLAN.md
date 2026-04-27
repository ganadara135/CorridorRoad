# CorridorRoad V1 Region Implementation Plan

Date: 2026-04-27
Branch: `v1-dev`
Status: Draft implementation plan
Depends on:

- `docsV1/V1_MASTER_PLAN.md`
- `docsV1/V1_ARCHITECTURE.md`
- `docsV1/V1_REGION_MODEL.md`
- `docsV1/V1_SECTION_MODEL.md`
- `docsV1/V1_CORRIDOR_MODEL.md`
- `docsV1/V1_STRUCTURE_MODEL.md`
- `docsV1/V1_DRAINAGE_MODEL.md`
- `docsV1/V1_RAMP_MODEL.md`
- `docsV1/V1_INTERSECTION_MODEL.md`

## 1. Purpose

This document defines the first practical implementation sequence for v1 Regions.

The goal is to make Regions the station-range control layer between completed Alignment/Profile/TIN work and later Assembly, Structure, Drainage, and Corridor generation.

## 2. Core Decision

Region rows are not single-purpose labels.

Each region should be represented as:

- one `primary_kind`
- zero or more `applied_layers`
- explicit references to assembly, structure, drainage, ramp, intersection, and override sources
- station start and end values
- priority and diagnostics

This supports realistic overlap such as:

- bridge + drainage + ditch
- normal road + culvert + guardrail
- intersection + widening + drainage
- ramp + retaining wall + side ditch

## 3. Current Baseline

Completed upstream work:

- Alignment creates v1 alignment source and compiled geometry.
- Stations are generated and reviewed through the unified v1 Stations command.
- Profile creates v1 FG source rows and can show profile preview.
- TIN builds, edits, previews, and reviews existing ground through the unified TIN workflow.
- Region concept is documented in `V1_REGION_MODEL.md`.

Missing implementation:

- no native `RegionModel` source model yet
- no region validation service yet
- no region resolution service yet
- no native Region task panel yet
- no downstream corridor consumer for resolved region context yet

## 4. Implementation Boundary

The first Region slice should stay source/model focused.

Do not implement full Corridor generation in the same slice.

Do not build Assembly authoring deeply inside the Region editor.

Do not hide bridge, culvert, drainage, ramp, or intersection meaning inside ad-hoc region strings.

## 5. Object Families

Initial code objects:

- `RegionModel`
- `RegionRow`
- `RegionPolicySet`
- `RegionResolutionResult`
- `RegionDiagnosticRow`

Deferred code objects:

- `RegionTransitionRow`
- `RegionConflictSet`
- advanced layer-specific policy rows
- automatic region splitting tools

## 6. Recommended Code Placement

New source model files:

- `freecad/Corridor_Road/v1/models/source/region_model.py`

New service files:

- `freecad/Corridor_Road/v1/services/evaluation/region_validation_service.py`
- `freecad/Corridor_Road/v1/services/evaluation/region_resolution_service.py`

New command/UI files:

- `freecad/Corridor_Road/v1/commands/cmd_region_editor.py`

New tests:

- `tests/contracts/v1/test_region_model.py`
- `tests/contracts/v1/test_region_resolution_service.py`
- `tests/contracts/v1/test_region_editor_command.py`

Possible existing files to update:

- `freecad/Corridor_Road/v1/models/source/__init__.py`
- `freecad/Corridor_Road/v1/services/evaluation/__init__.py`
- `freecad/Corridor_Road/init_gui.py`
- `freecad/Corridor_Road/objects/obj_project.py`

## 7. RegionModel Contract

Minimum root fields:

- `schema_version`
- `project_id`
- `region_model_id`
- `alignment_id`
- `label`
- `region_rows`
- `policy_sets`
- `source_refs`
- `diagnostic_rows`

Minimum `RegionRow` fields:

- `region_id`
- `region_index`
- `primary_kind`
- `applied_layers`
- `station_start`
- `station_end`
- `assembly_ref`
- `structure_refs`
- `drainage_refs`
- `ramp_ref`
- `intersection_ref`
- `policy_set_ref`
- `template_ref`
- `superelevation_ref`
- `override_refs`
- `priority`
- `source_ref`
- `notes`

Minimum primary kinds:

- `normal_road`
- `bridge`
- `culvert`
- `intersection`
- `ramp`
- `drainage`
- `transition`
- `structure_influence`
- `daylight_control`

Minimum applied layer examples:

- `ditch`
- `drainage`
- `guardrail`
- `culvert`
- `retaining_wall`
- `widening`
- `side_ditch`
- `deck_drain`

## 8. Validation Rules

The first validation service should check:

- station start is lower than station end
- primary kind is supported
- applied layer names are normalized
- region id is not empty
- region ids are unique
- priority is numeric
- assembly/template references are not contradictory
- structure and drainage references are preserved as lists
- overlapping rows with equal priority produce a warning
- gaps between required normal road coverage produce a warning, not an auto-fix

The service should return diagnostic rows instead of silently changing source intent.

## 9. Resolution Rules

The first resolution service should answer:

- active region at a station
- overlapping regions at a station
- regions intersecting a station range
- nearest region boundary stations

Initial winner rule:

1. choose rows where `station_start <= station <= station_end`
2. sort by highest `priority`
3. if priorities tie, sort by lowest `region_index`
4. preserve non-winning overlaps in diagnostics

Resolution result fields:

- `station`
- `active_region_id`
- `active_primary_kind`
- `active_applied_layers`
- `active_assembly_ref`
- `active_template_ref`
- `resolved_structure_refs`
- `resolved_drainage_refs`
- `resolved_ramp_ref`
- `resolved_intersection_ref`
- `overlap_region_ids`
- `diagnostic_rows`

## 10. Region Editor MVP

The first Region editor should be a table-based source editor.

Recommended columns:

- `Start STA`
- `End STA`
- `Primary Kind`
- `Layers`
- `Assembly`
- `Structures`
- `Drainage`
- `Priority`
- `Notes`

Recommended controls:

- `Add Region`
- `Delete Selected`
- `Sort by Station`
- `Load Starter Regions`
- `Validate`
- `Apply`
- `Close`

Opening the panel should not modify the document.

`Apply` should create or update a durable v1 Region source object.

`Validate` should run the region validation service without changing source state.

## 11. Starter Region Strategy

For the first usable slice, starter regions may be derived from:

- generated station range from Stations
- active alignment length when available
- manual fallback range `0.000` to `100.000`

Initial starter rows:

- one `normal_road` region covering the available station range
- no applied layers
- blank assembly, structure, and drainage references
- priority `10`

The starter should be loaded only when the user clicks `Load Starter Regions`.

## 12. Tree Placement

Recommended v1 tree placement:

- `04_Corridor Model / Regions`

If the current tree does not have a dedicated Regions folder under Corridor Model yet, route the first source object under the closest existing `04_Corridor Model` group and record a follow-up to split child folders.

Region objects should not be placed under legacy v0 `Regions001` style containers.

## 13. Implementation Phases

### Phase R1: Source Model

Tasks:

- [ ] create `RegionModel`, `RegionRow`, `RegionPolicySet`, and diagnostic dataclasses
- [ ] export source model from `models/source/__init__.py`
- [ ] add model contract tests

Acceptance criteria:

- [ ] a bridge region with ditch and drainage layers can be represented
- [ ] list fields round-trip as lists, not comma-only strings
- [ ] empty optional references stay explicit

### Phase R2: Validation and Resolution Services

Tasks:

- [ ] implement region validation service
- [ ] implement active station resolution
- [ ] implement overlap diagnostics
- [ ] add focused service tests

Acceptance criteria:

- [ ] a station inside one region resolves deterministically
- [ ] overlapping regions resolve by priority
- [ ] equal-priority overlap emits a warning
- [ ] invalid station ranges emit errors

### Phase R3: FreeCAD Source Object Bridge

Tasks:

- [ ] create or update a durable v1 Region source object
- [ ] store station, kind, layer, reference, and priority rows as object properties
- [ ] route the object to the v1 project tree
- [ ] keep source fields readable by tests and future corridor services

Acceptance criteria:

- [ ] Apply creates one region source object
- [ ] repeated Apply updates the same object
- [ ] tree placement is under the v1 Corridor Model area

### Phase R4: Region Editor MVP

Tasks:

- [ ] add native `Regions` command
- [ ] add table editor with starter rows
- [ ] make opening non-destructive
- [ ] add Validate and Apply actions
- [ ] add command contract tests

Acceptance criteria:

- [ ] user can create a normal road region
- [ ] user can create a bridge region with drainage and ditch layers
- [ ] user can apply without creating corridor geometry
- [ ] validation messages are visible before Apply

### Phase R5: Downstream Handoff

Tasks:

- [ ] expose `RegionResolutionService` for future AppliedSection and Corridor services
- [ ] add a small handoff summary helper for viewers
- [ ] document how Assembly and Structure editors should reference Region rows

Acceptance criteria:

- [ ] a future corridor service can ask for resolved region context at a station
- [ ] viewer summaries can show primary kind, layers, assembly, structure, and drainage references

## 14. Manual QA Flow

Recommended first manual flow:

1. Create or open a v1 project.
2. Build TIN.
3. Create Alignment.
4. Generate Stations.
5. Create Profile.
6. Open Regions.
7. Click `Load Starter Regions`.
8. Change one row to `bridge`.
9. Add layers `ditch, drainage`.
10. Add structure and drainage references as text ids.
11. Click `Validate`.
12. Click `Apply`.

Expected result:

- one v1 Region source object exists
- region rows preserve primary kind and applied layers
- no corridor geometry is generated yet
- validation diagnostics are readable

## 15. Stop Conditions

Pause and realign if:

- Region editor starts generating final corridor solids
- bridge or drainage meaning is stored only as free-form notes
- applied layers replace explicit `StructureModel` or `DrainageModel` references
- overlapping rows are silently resolved without diagnostics
- v0 region containers become the durable v1 source

## 16. Recommended Next Coding Slice

Implement Phase R1 and R2 first.

The first code change should add:

- `freecad/Corridor_Road/v1/models/source/region_model.py`
- `freecad/Corridor_Road/v1/services/evaluation/region_resolution_service.py`
- `tests/contracts/v1/test_region_resolution_service.py`

This gives us the source contract and deterministic resolver before any UI decisions harden.
