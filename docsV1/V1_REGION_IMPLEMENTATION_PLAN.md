# CorridorRoad V1 Region Implementation Plan

Date: 2026-04-27
Branch: `v1-dev`
Status: Phase R1/R2/R3/R4/R5 initial handoff slice complete
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

- native `RegionModel` source model exists and now supports primary kind, applied layers, and domain references
- region validation service exists for station ranges, ids, kind warnings, and overlap diagnostics
- region resolution service exists for active station, range overlap, and boundary queries
- durable v1 Region source object bridge exists and routes to `04_Corridor Model / Regions`
- native Region task panel exists for source-row authoring
- downstream handoff summaries exist for future AppliedSection and Corridor services
- no full corridor consumer has been implemented yet

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

- [x] create `RegionModel`, `RegionRow`, `RegionPolicySet`, and diagnostic dataclasses
- [x] export source model from `models/source/__init__.py`
- [x] add model contract tests

Acceptance criteria:

- [x] a bridge region with ditch and drainage layers can be represented
- [x] list fields round-trip as lists, not comma-only strings
- [x] empty optional references stay explicit

### Phase R2: Validation and Resolution Services

Tasks:

- [x] implement region validation service
- [x] implement active station resolution
- [x] implement overlap diagnostics
- [x] add focused service tests

Acceptance criteria:

- [x] a station inside one region resolves deterministically
- [x] overlapping regions resolve by priority
- [x] equal-priority overlap emits a warning
- [x] invalid station ranges emit errors

### Phase R3: FreeCAD Source Object Bridge

Tasks:

- [x] create or update a durable v1 Region source object
- [x] store station, kind, layer, reference, and priority rows as object properties
- [x] route the object to the v1 project tree
- [x] keep source fields readable by tests and future corridor services

Acceptance criteria:

- [x] Apply creates one region source object
- [x] repeated Apply updates the same object
- [x] tree placement is under the v1 Corridor Model area

### Phase R4: Region Editor MVP

Tasks:

- [x] add native `Regions` command
- [x] add table editor with starter rows
- [x] make opening non-destructive
- [x] add Validate and Apply actions
- [x] add command contract tests

Acceptance criteria:

- [x] user can create a normal road region
- [x] user can create a bridge region with drainage and ditch layers
- [x] user can apply without creating corridor geometry
- [x] validation messages are visible before Apply

### Phase R5: Downstream Handoff

Tasks:

- [x] expose `RegionResolutionService` for future AppliedSection and Corridor services
- [x] add a small handoff summary helper for viewers
- [x] document how Assembly and Structure editors should reference Region rows

Acceptance criteria:

- [x] a future corridor service can ask for resolved region context at a station
- [x] viewer summaries can show primary kind, layers, assembly, structure, and drainage references

## 13.1 Downstream Handoff Contract

Future corridor, section, assembly, structure, drainage, ramp, and intersection services should consume Region state through `RegionResolutionService.resolve_handoff`.

Do not read Region editor table widgets as source truth.

Do not infer bridge, ramp, drainage, or intersection behavior from free-form notes.

Use these Region fields as downstream references:

- `primary_kind` selects the dominant station-range control mode.
- `applied_layers` adds non-exclusive context such as `ditch`, `drainage`, `guardrail`, or `widening`.
- `assembly_ref` points to the Assembly source to apply at the station.
- `template_ref` remains a compatibility/template-level hint until Assembly authoring is complete.
- `structure_refs` points to bridge, culvert, retaining wall, or other Structure sources.
- `drainage_refs` points to Drainage elements or collection/discharge context.
- `ramp_ref` and `intersection_ref` point to Ramp and Intersection sources when the Region is tied to those domains.
- `override_refs` points to station-specific or component-specific overrides.

Viewer and review tools should use `RegionContextSummary.to_review_items`.

The summary helper is read-only. It exposes resolved context but does not mutate Region source rows.

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

Phase R1, R2, R3, R4, and the initial R5 handoff slice are complete.

The next code change should begin the Assembly source/editor slice:

- define v1 `AssemblyModel` source rows around lanes, shoulders, side slopes, and layer components
- add an Assembly editor MVP that stores source rows only
- connect Region `assembly_ref` to Assembly lookup without generating corridor geometry yet

This lets Region rows point to real Assembly sources before corridor generation begins.
