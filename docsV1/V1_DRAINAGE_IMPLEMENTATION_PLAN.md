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

Detailed Flow Route graph implementation is tracked in `V1_DRAINAGE_FLOW_ROUTE_IMPLEMENTATION_PLAN.md`.

## 2. Scope

This plan includes:

- Drainage toolbar command and editor shell
- `DrainageModel` object persistence
- drainage element node creation and editing
- flow-route edge creation and editing
- Drainage Element Region assignment workflow
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

Drainage Elements own their Region assignment.

Applied Sections, corridor surfaces, review markers, and reports are generated results or outputs. They must not become the durable editing source.

## 4. Current State

Implemented or partially available:

- `DrainageModel` source dataclasses exist.
- Assembly supports ditch components and shape-aware ditch parameters.
- Applied Sections can emit `ditch_surface` point rows.
- Build Corridor has Drainage diagnostics and a drainage surface preview from ditch points.
- A `Drainage` toolbar/menu entry opens the first Drainage editor task panel.
- A `V1DrainageModel` document object can persist element, policy, flow-route, source reference, and validation diagnostic rows.

Main gaps:

- no drainage quantity/report pipeline
- Assembly references are currently text refs, not source-object pickers

## 5. Target Workflow

The target user workflow is:

1. Define TIN, Alignment, Profile, and Stations.
2. Define Assembly ditch shapes when roadside drainage geometry is needed.
3. Define Regions and station ranges.
4. Define Structures and assign them to Regions when structure context is needed.
5. Open Drainage and create drainage Element nodes.
6. Assign drainage elements to Regions from the Drainage panel.
7. Create Flow Route edges between Elements where connection intent is needed.
8. Run Applied Sections.
9. Review ditch points, flowlines, and diagnostics.
10. Build Corridor drainage surface from Applied Section outputs.
11. Review Drainage diagnostics and quantities.
12. Export drainage-aware outputs where supported.

Toolbar order:

`Assembly -> Regions -> Structures -> Drainage -> Applied Sections -> Build Corridor`

## 6. Source Contracts

### 6.1 DrainageModel

Required fields for the first implementation:

- `drainage_model_id`
- `project_id`
- `label`
- `element_rows`
- `policy_rows`
- `flow_route_rows`
- `diagnostic_rows`

Core graph rule:

- `element_rows` are drainage nodes.
- `flow_route_rows` are drainage edges.
- Final outlets should be represented as `outfall_reference` Elements when possible.
- Optional route-level `outlet_ref` is summary metadata, not the primary connection edge.

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
- `route_rule`
- `discharge_rule`
- `earthwork_priority`

### 6.4 DrainageFlowRoute

Required first-slice fields:

- `flow_route_id`
- `from_element_ref`
- `to_element_ref`
- `direction`
- `risk_level`
- `notes`

Optional first-slice field:

- `outlet_ref`

`from_element_ref -> to_element_ref` is the graph edge. `outlet_ref` is only used when the final outlet must be preserved for review or reporting without walking the graph.

## 7. Evaluation Flow

The evaluation flow should be:

1. Resolve active Region at station.
2. Resolve active `DrainageElementRow` objects by `region_ref` and station span.
4. Resolve Flow Route edges connected to the active elements.
5. Resolve Assembly ditch components linked by `assembly_component_ref`.
6. Generate station-specific ditch surface points and flowline hints in `AppliedSection`.
7. Preserve `drainage_ref`, `component_ref`, side, and role metadata on evaluated points.
8. Build drainage surface and diagnostics from these result rows.

## 8. Review Flow

Drainage Review should expose:

- element coverage by station range
- missing or invalid Drainage Element Region assignments
- ditch point availability by station and side
- flowline continuity
- low-point and minimum-grade warnings
- missing outlet or discharge target
- broken Flow Route edge references
- cross-Region Flow Route warnings
- cycles that prevent outlet tracing
- culvert/reference coordination warnings
- source references back to Region, Structure, Assembly, and DrainageModel rows

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

- `V1DrainageModel` document object stores element, policy, and flow-route rows
- `to_drainage_model` restores the source contract from the document object
- `v1_drainage_model` routes to `05_Drainage`
- Watertight Solid target discovery reads the document DrainageModel and can promote matching ditch/channel elements as lined ditch solid owners
- `DrainageValidationService` reports duplicate element/policy/flow-route ids, invalid ranges, missing policy ids, and missing policy refs
- `V1DrainageModel` stores validation status and diagnostic rows on update

### D3. Drainage Editor shell

Status: first slice complete

Tasks:

- replace placeholder message with a task panel
- show Drainage Source selector
- add element table
- add policy table
- add flow-route table
- add Apply and Close behavior

Acceptance criteria:

- opening the editor loads an existing `DrainageModel` or a non-persistent starter model
- Apply creates or updates a `DrainageModel`
- selected rows remain editable without generated geometry ownership

Completed:

- Drainage command opens `V1DrainageEditorTaskPanel`
- editor shows element, policy, and flow-route tables
- editor provides Preset data for roadside ditch, dual side ditches, and culvert crossing source sets
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
- Drainage editor element rows expose Side, Region, Assembly, Policy, and Structure Ref columns.
- Drainage editor includes left/right ditch default row actions.
- Drainage validation warns when a drainage side is outside `left`, `right`, `both`, or `center`.
- Watertight Solid lined-ditch target discovery uses `DrainageElementRow.side` before falling back to Drainage element id text.

Remaining:

- replace free-text Assembly refs with source-object selectors

### D5. Drainage-owned Region assignment

Status: supersedes the old Region-to-Drainage handoff

Tasks:

- keep Region selection in the Drainage Elements table
- validate missing or invalid Region refs from Drainage
- validate Drainage Element station ranges against the selected Region
- report Flow Routes that intentionally cross Region boundaries

Acceptance criteria:

- Drainage Elements can reference Regions without editing Region rows
- missing or invalid Region references are visible before Applied Sections
- Flow Routes can connect Elements in different Regions with an explicit warning

Completed:

- Drainage editor Region cells are row-level combos populated from `V1RegionModel`.
- Drainage validation checks Element station ranges against selected Region boundaries.
- Flow Route validation reports cross-Region Element connections as warnings.
- Drainage `Structure Ref` values are validated against StructureModel when available.

Remaining:

- update Applied Section generation to resolve Drainage from `DrainageModel.region_ref` instead of Region handoff refs

### D6. Applied Section drainage evaluation

Status: first slice complete, Applied Section Region-assignment resolver implemented

Tasks:

- resolve Drainage Elements by Region assignment during Applied Section generation
- tag generated `ditch_surface` points with drainage refs where possible
- emit flowline hint rows or point roles for invert/flowline points
- preserve diagnostics for missing Assembly component refs or unsupported shape links

Acceptance criteria:

- Cross Section Viewer can show ditch points with source drainage refs
- Build Corridor drainage diagnostics can distinguish source-missing from geometry-missing cases

Completed:

- Applied Section generation resolves Drainage Elements from `DrainageModel.region_ref` and station span.
- Ditch component result rows preserve matching Drainage refs by side when available.
- Generated `ditch_surface` points preserve `component_ref`, `side`, and `drainage_ref`.
- Applied Section source refs include active Drainage refs for downstream review and exchange traceability.
- `V1AppliedSectionSet` document persistence round-trips point and component Drainage context.

Remaining:

- add explicit flowline/invert point roles beyond the current shape roles
- add diagnostics for Drainage Elements that do not match any active ditch component side
- expose Drainage context directly in Cross Section Viewer labels/review tables

### D7. Drainage Review viewer

Status: first slice complete

Tasks:

- create read-only Drainage Review task panel
- show station coverage, element rows, flowline continuity, and diagnostics
- add marker focus for diagnostic rows
- add navigation buttons to Region, Assembly, Profile, and Cross Section Viewer

Acceptance criteria:

- user can identify stations without drainage coverage
- user can focus a drainage issue marker in the 3D view

Completed:

- `DrainageReviewMapper` builds a `DrainageOutput` payload from `DrainageModel`, `RegionModel`, and `AppliedSectionSet`.
- Drainage Review command opens a read-only task panel after Drainage in the workflow toolbar.
- Review tables show Drainage elements, Region assignment context, Applied Section ditch context, and summary counts.
- Missing Drainage Region assignments and cross-Region Flow Routes are surfaced as first-slice review warnings.
- Applied Section `ditch_surface` point counts and Drainage ref coverage are visible without reading preview mesh geometry.
- Region assignment review reads Drainage Element `region_ref` values and no longer reads Region-owned Drainage refs.
- Cross Section Viewer source ownership rows can expose Drainage context when a section carries Drainage Element refs.

Remaining:

- add station issue markers and 3D focus for missing coverage rows
- add navigation buttons back to Region, Drainage, Assembly, Profile, and Cross Section Viewer
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
5. Select the owning Region in the Drainage element row.
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
- Flow Routes that cross Region boundaries are valid when intentional, but they must be visible as review diagnostics.

## 13. Release Note

For the current release, Drainage is exposed as a planned v1 stage with a toolbar/menu command and placeholder message.

Functional editing, review, and output work should begin with D2 and D3 after release stabilization.
