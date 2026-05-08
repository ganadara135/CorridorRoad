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
- A `Drainage` toolbar/menu entry opens the first Drainage editor task panel.
- A `V1DrainageModel` document object can persist element, policy, collection, source reference, and validation diagnostic rows.

Main gaps:

- no separate Drainage Review viewer
- no drainage quantity/report pipeline
- no Applied Section drainage evaluation from `DrainageModel` rows yet
- Region and Assembly references are currently text refs, not source-object pickers

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

Status: completed

Tasks:

- add `obj_drainage.py`
- serialize/deserialize `DrainageModel`
- place drainage objects under the v1 `05_Drainage` project folder when possible
- add validation diagnostics for duplicate ids, invalid ranges, and missing policy refs

Acceptance criteria:

- a document can store and reload one `DrainageModel`
- validation messages are stable and readable

Completed:

- `V1DrainageModel` document object stores element, policy, and collection-region rows
- `to_drainage_model` restores the source contract from the document object
- `v1_drainage_model` routes to `05_Drainage`
- Watertight Solid target discovery reads the document DrainageModel and can promote matching ditch/channel elements as lined ditch solid owners
- `DrainageValidationService` reports duplicate element/policy/collection ids, invalid station ranges, missing policy ids, and missing policy refs
- `V1DrainageModel` stores validation status and diagnostic rows on update

### D3. Drainage Editor shell

Status: first slice complete

Tasks:

- replace placeholder message with a task panel
- show Drainage Source selector
- add element table
- add policy table
- add collection/discharge table
- add Apply and Close behavior

Acceptance criteria:

- opening the editor loads an existing `DrainageModel` or a non-persistent starter model
- Apply creates or updates a `DrainageModel`
- selected rows remain editable without generated geometry ownership

Completed:

- Drainage command opens `V1DrainageEditorTaskPanel`
- editor shows element, policy, and collection tables
- Validate runs `DrainageValidationService`
- Apply persists `V1DrainageModel`
- invalid rows block Apply and keep diagnostics visible

Remaining:

- source selectors for existing Region and Assembly refs

### D4. Basic element authoring

Status: first slice complete

Tasks:

- support ditch, swale, channel, culvert reference, inlet reference, and outfall reference rows
- support station range, side, Region ref, Assembly component ref, and policy ref columns
- add simple defaults for left/right side ditch elements

Acceptance criteria:

- user can create a right-side ditch element for a station range
- user can link it to an existing Region and Assembly ditch component id

Completed:

- `DrainageElementRow` now stores `side`, `region_ref`, and `assembly_component_ref`.
- `V1DrainageModel` persists and restores side, Region refs, and Assembly component refs.
- Drainage editor element rows expose Side, Region, Assembly Component, Offset Rule, Policy, and Structure columns.
- Drainage editor includes left/right ditch default row actions.
- Drainage validation warns when a drainage side is outside `left`, `right`, `both`, or `center`.
- Watertight Solid lined-ditch target discovery uses `DrainageElementRow.side` before falling back to id/offset text.

Remaining:

- replace free-text Region and Assembly refs with source-object selectors

### D5. Region handoff

Status: first slice complete

Tasks:

- make Region editor show/select drainage refs when available
- preserve `RegionRow.drainage_refs`
- add diagnostics when a Region references missing drainage ids

Acceptance criteria:

- Region can reference one or more drainage elements
- missing references are visible before Applied Sections

Completed:

- Region editor reads available Drainage element ids from `V1DrainageModel`.
- Region editor provides an `Attach Drainage` action that appends the selected Drainage element id to the selected Region row.
- Region validation can receive `known_drainage_refs` and reports missing `drainage_ref` values before Apply.
- Existing `RegionRow.drainage_refs` persistence remains the source handoff contract.

Remaining:

- allow selecting multiple Drainage refs through a richer picker instead of a single append action
- mirror the same Region handoff from the Drainage editor side
- carry Drainage refs into Applied Section generated rows

### D6. Applied Section drainage evaluation

Status: first slice complete

Tasks:

- resolve Region drainage refs during Applied Section generation
- tag generated `ditch_surface` points with drainage refs where possible
- emit flowline hint rows or point roles for invert/flowline points
- preserve diagnostics for missing Assembly component refs or unsupported shape links

Acceptance criteria:

- Cross Section Viewer can show ditch points with source drainage refs
- Build Corridor drainage diagnostics can distinguish source-missing from geometry-missing cases

Completed:

- Applied Section generation reads active Region handoff `drainage_refs`.
- Ditch component result rows preserve matching Drainage refs by side when available.
- Generated `ditch_surface` points preserve `component_ref`, `side`, and `drainage_ref`.
- Applied Section source refs include active Drainage refs for downstream review and exchange traceability.
- `V1AppliedSectionSet` document persistence round-trips point and component Drainage context.

Remaining:

- add explicit flowline/invert point roles beyond the current shape roles
- add diagnostics for Region drainage refs that do not match any active ditch component side
- expose Drainage context directly in Cross Section Viewer labels/review tables

### D7. Drainage Review viewer

Status: first slice complete

Tasks:

- create read-only Drainage Review task panel
- show station coverage, element rows, flowline continuity, and diagnostics
- add marker focus for diagnostic rows
- add handoff buttons to Region, Assembly, Profile, and Cross Section Viewer

Acceptance criteria:

- user can identify stations without drainage coverage
- user can focus a drainage issue marker in the 3D view

Completed:

- `DrainageReviewMapper` builds a `DrainageOutput` payload from `DrainageModel`, `RegionModel`, and `AppliedSectionSet`.
- Drainage Review command opens a read-only task panel after Drainage in the workflow toolbar.
- Review tables show Drainage elements, Region handoff refs, Applied Section ditch context, and summary counts.
- Region drainage refs missing from the active `DrainageModel` are surfaced as first-slice review warnings.
- Applied Section `ditch_surface` point counts and Drainage ref coverage are visible without reading preview mesh geometry.

Remaining:

- add station issue markers and 3D focus for missing coverage rows
- add handoff buttons back to Region, Drainage, Assembly, Profile, and Cross Section Viewer
- add flowline continuity checks after explicit flowline/invert result roles exist

### D8. Corridor and surface integration

Status: complete first slice

Implemented:

- drainage surface generation consumes `ditch_surface` Applied Section point rows and preserves `drainage_ref`, `component_ref`, and `side` on generated TIN vertices
- supplemental drainage surface sampling carries matching source context from the original Applied Section rows instead of reading preview meshes
- `SurfaceModel` keeps drainage as a separate `drainage_surface` row and adds Drainage element refs to the drainage build relation
- drainage TIN quality/provenance rows report Drainage source-ref counts and missing source coverage

Acceptance criteria:

- [x] drainage surface follows Applied Section ditch rows
- [x] drainage surface diagnostics reference source drainage ids
- [ ] explicit flowline/invert rows remain a later refinement

### D9. Quantities and reports

Status: complete first slice

Implemented:

- `QuantityBuildService` creates `drainage_ditch_length` fragments by Drainage element id from source-tagged Applied Section `ditch_surface` rows
- `QuantityBuildService` creates `drainage_flowline_length` fragments when paired flowline/invert-style ditch point ids are available
- `QuantityFragment` and `QuantityFragmentRow` preserve `drainage_ref`
- `DrainageReviewMapper` can include drainage quantity rows and summary lengths when a `QuantityModel` is supplied
- missing Drainage source refs or insufficient station spans are reported as quantity diagnostics

Acceptance criteria:

- [x] ditch length and flowline length can be reported by Drainage element id
- [x] diagnostics identify missing quantity source rows
- [ ] persisted document-level Drainage Review loading of the latest QuantityModel remains a later UI/output integration step

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
