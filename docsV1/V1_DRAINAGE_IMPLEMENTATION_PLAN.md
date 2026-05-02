# CorridorRoad V1 Drainage Implementation Plan

Date: 2026-05-02
Status: Draft implementation plan
Scope: v1-native drainage source, evaluation, review, and output workflow

Depends on:

- `docsV1/V1_MASTER_PLAN.md`
- `docsV1/V1_DRAINAGE_MODEL.md`
- `docsV1/V1_DITCH_SHAPE_CONTRACT.md`
- `docsV1/V1_REGION_MODEL.md`
- `docsV1/V1_SECTION_MODEL.md`
- `docsV1/V1_SURFACE_MODEL.md`
- `docsV1/V1_QUANTITY_MODEL.md`

## 1. Purpose

This plan defines how CorridorRoad v1 should implement Drainage after the first placeholder toolbar entry.

The goal is to make drainage design intent explicit, editable, reviewable, and traceable through Applied Sections, Corridor Build, quantities, and later exchange outputs.

## 2. Scope

This plan includes:

- Drainage toolbar command and editor shell
- `DrainageModel` object persistence
- drainage element creation and editing
- Region-to-Drainage reference workflow
- Assembly ditch shape connection to drainage intent
- Applied Section drainage point and flowline evaluation
- Build Corridor drainage surface consumption
- Drainage Review diagnostics
- first-slice drainage quantities and outputs

This plan excludes:

- full hydraulic solver behavior
- automatic pipe sizing
- storm sewer network design
- v0 drainage import or migration
- direct editing of generated drainage meshes as source truth

## 3. Core Rule

`DrainageModel` owns drainage intent.

Assembly owns reusable ditch section shape.

Region owns where drainage intent is active.

Applied Sections, corridor surfaces, review markers, and reports are generated results or outputs. They must not become the durable editing source.

## 4. Current State

Implemented or partially available:

- `DrainageModel` source dataclasses exist.
- `RegionRow.drainage_refs` exists.
- Assembly supports ditch components and shape-aware ditch parameters.
- Applied Sections can emit `ditch_surface` point rows.
- Build Corridor has Drainage diagnostics and a drainage surface preview from ditch points.
- A `Drainage` toolbar/menu entry exists and shows a temporary under-development message.

Main gaps:

- no real Drainage Editor task panel
- no FreeCAD document object for persisted `DrainageModel`
- no create/update workflow for drainage elements
- no first-class link between drainage elements and Assembly ditch components
- no separate Drainage Review viewer
- no drainage quantity/report pipeline

## 5. Target Workflow

The target user workflow is:

1. Define TIN, Alignment, Profile, and Stations.
2. Define Assembly ditch shapes when roadside drainage geometry is needed.
3. Define Regions and station ranges.
4. Open Drainage and create drainage elements.
5. Link drainage elements to Regions through `drainage_refs`.
6. Run Applied Sections.
7. Review ditch points, flowlines, and diagnostics.
8. Build Corridor drainage surface from Applied Section outputs.
9. Review Drainage diagnostics and quantities.
10. Export drainage-aware outputs where supported.

Toolbar order:

`Assembly -> Structures -> Region -> Drainage -> Applied Sections -> Build Corridor`

## 6. Source Contracts

### 6.1 DrainageModel

Required fields for the first implementation:

- `drainage_model_id`
- `project_id`
- `label`
- `element_rows`
- `policy_rows`
- `collection_region_rows`
- `diagnostic_rows`

### 6.2 DrainageElementRow

Required first-slice fields:

- `drainage_element_id`
- `element_kind`
- `station_start`
- `station_end`
- `side`
- `alignment_ref`
- `region_ref`
- `assembly_component_ref`
- `offset_rule`
- `policy_set_ref`
- `structure_ref`
- `notes`

Recommended first-slice element kinds:

- `ditch`
- `swale`
- `channel`
- `culvert_reference`
- `inlet_reference`
- `outfall_reference`

### 6.3 DrainagePolicySet

Required first-slice fields:

- `policy_set_id`
- `flow_intent`
- `min_grade_rule`
- `low_point_rule`
- `collection_rule`
- `discharge_rule`
- `earthwork_priority`

## 7. Evaluation Flow

The evaluation flow should be:

1. Resolve active Region at station.
2. Read Region `drainage_refs`.
3. Resolve referenced `DrainageElementRow` objects.
4. Resolve Assembly ditch components linked by `assembly_component_ref`.
5. Generate station-specific ditch surface points and flowline hints in `AppliedSection`.
6. Preserve `drainage_ref`, `component_ref`, side, and role metadata on evaluated points.
7. Build drainage surface and diagnostics from these result rows.

## 8. Review Flow

Drainage Review should expose:

- element coverage by station range
- missing or invalid `drainage_refs`
- ditch point availability by station and side
- flowline continuity
- low-point and minimum-grade warnings
- missing outlet or discharge target
- culvert/reference coordination warnings
- source references back to Region, Assembly, and DrainageModel rows

The review surface is read-only. Corrections should return users to Drainage, Region, Assembly, or Profile editors.

## 9. Output Flow

First-slice output rows should include:

- drainage element summary rows
- ditch length rows
- flowline length rows
- ditch lining area placeholders where lining parameters exist
- culvert reference count/length placeholders
- drainage diagnostic rows

Later output rows may include:

- drainage report table
- drainage quantity package
- exchange package references for culverts, inlets, outlets, and outfalls

## 10. Implementation Steps

### D1. Toolbar and placeholder command

Status: completed

Acceptance criteria:

- Drainage command is visible after Region and before Applied Sections.
- Clicking Drainage shows a clear under-development message.
- Drainage has a distinct icon.

### D2. Document object persistence

Status: pending

Tasks:

- add `obj_drainage.py`
- serialize/deserialize `DrainageModel`
- place drainage objects under the v1 `05_Drainage` project folder when possible
- add validation diagnostics for duplicate ids, invalid ranges, and missing policy refs

Acceptance criteria:

- a document can store and reload one `DrainageModel`
- validation messages are stable and readable

### D3. Drainage Editor shell

Status: pending

Tasks:

- replace placeholder message with a task panel
- show Drainage Source selector
- add element table
- add policy table
- add collection/discharge table
- add Apply and Close behavior

Acceptance criteria:

- opening the editor does not create sample data
- Apply creates or updates a `DrainageModel`
- selected rows remain editable without generated geometry ownership

### D4. Basic element authoring

Status: pending

Tasks:

- support ditch, swale, channel, culvert reference, inlet reference, and outfall reference rows
- support station range, side, Region ref, Assembly component ref, and policy ref columns
- add simple defaults for left/right side ditch elements

Acceptance criteria:

- user can create a right-side ditch element for a station range
- user can link it to an existing Region and Assembly ditch component id

### D5. Region handoff

Status: pending

Tasks:

- make Region editor show/select drainage refs when available
- preserve `RegionRow.drainage_refs`
- add diagnostics when a Region references missing drainage ids

Acceptance criteria:

- Region can reference one or more drainage elements
- missing references are visible before Applied Sections

### D6. Applied Section drainage evaluation

Status: pending

Tasks:

- resolve Region drainage refs during Applied Section generation
- tag generated `ditch_surface` points with drainage refs where possible
- emit flowline hint rows or point roles for invert/flowline points
- preserve diagnostics for missing Assembly component refs or unsupported shape links

Acceptance criteria:

- Cross Section Viewer can show ditch points with source drainage refs
- Build Corridor drainage diagnostics can distinguish source-missing from geometry-missing cases

### D7. Drainage Review viewer

Status: pending

Tasks:

- create read-only Drainage Review task panel
- show station coverage, element rows, flowline continuity, and diagnostics
- add marker focus for diagnostic rows
- add handoff buttons to Region, Assembly, Profile, and Cross Section Viewer

Acceptance criteria:

- user can identify stations without drainage coverage
- user can focus a drainage issue marker in the 3D view

### D8. Corridor and surface integration

Status: pending

Tasks:

- make drainage surface generation consume source-tagged Applied Section rows
- preserve drainage output rows separately from finished-grade and slope-face surfaces
- avoid deriving drainage design intent from preview meshes

Acceptance criteria:

- drainage surface follows Applied Section ditch/flowline rows
- drainage surface diagnostics reference source drainage ids

### D9. Quantities and reports

Status: pending

Tasks:

- add drainage quantity fragments
- add drainage output mapper
- show drainage quantity summary in review/output surfaces

Acceptance criteria:

- ditch length and flowline length can be reported by drainage element id
- diagnostics identify missing quantity source rows

## 11. Manual QA

Minimum manual QA scenario:

1. Create a simple road project.
2. Create Assembly with ditch components.
3. Create Region for a station range.
4. Create Drainage element for the same range and side.
5. Link Region to the Drainage element.
6. Run Applied Sections.
7. Confirm ditch/flowline rows carry drainage context.
8. Build Corridor.
9. Confirm drainage surface and diagnostics are visible.
10. Confirm Drainage Review can focus issue markers.

## 12. Known Risks

- Drainage can be confused with Assembly ditch shape if ownership is not explicit.
- Region may become overloaded if drainage intent is stored as free text.
- Build Corridor may hide drainage problems if it only checks point counts.
- Flowline continuity needs stable station ordering and side metadata.
- Culvert references must stay coordinated with StructureModel without duplicating structure ownership.

## 13. Release Note

For the current release, Drainage is exposed as a planned v1 stage with a toolbar/menu command and placeholder message.

Functional editing, review, and output work should begin with D2 and D3 after release stabilization.
