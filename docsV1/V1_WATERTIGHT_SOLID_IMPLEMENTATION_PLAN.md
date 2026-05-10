# Parametric Road V1 Watertight Solid Implementation Plan

Date: 2026-05-07  
Status: Draft implementation plan  
Scope: v1 final-stage watertight solid command, contracts, validation, preview, and output

Depends on:

- `docsV1/V1_MASTER_PLAN.md`
- `docsV1/V1_WATERTIGHT_SOLID_PLAN.md`
- `docsV1/V1_WATERTIGHT_SOLID_TARGET_EXPANSION_PLAN.md`
- `docsV1/V1_WATERTIGHT_SOLID_UI_EXECUTION_PLAN.md`
- `docsV1/V1_CORRIDOR_MODEL.md`
- `docsV1/V1_SECTION_MODEL.md`
- `docsV1/V1_SURFACE_MODEL.md`
- `docsV1/V1_REGION_MODEL.md`
- `docsV1/V1_STRUCTURE_GEOMETRY_CONTRACT.md`
- `docsV1/V1_DITCH_SHAPE_CONTRACT.md`
- `docsV1/V1_OUTPUT_STRATEGY.md`

## 1. Purpose

This document turns the watertight solid direction into implementation slices.

The goal is to add a final v1 toolbar stage named `Watertight Solids` that can generate reviewable, validated watertight solid outputs after `Build Corridor` has produced accepted corridor prerequisites.

## 2. Implementation Boundary

Watertight solid generation is not part of initial source editing.

It consumes:

- `V1AppliedSectionSet`
- `V1CorridorModel`
- `V1SurfaceModel` where available
- `RegionModel`
- `AssemblyModel`
- `StructureModel`
- future `DrainageModel`

It produces:

- solid target rows
- closed station profiles
- edge network rows
- face/shell validation rows
- FreeCAD Part solid preview objects where possible
- normalized watertight solid output rows

It must not:

- make generated solids editable source geometry
- infer durable engineering intent from viewer meshes
- require boolean union of every component body in the first implementation
- replace `SurfaceModel`

## 3. Core Decision: Topology First

Watertight Solid implementation must be topology-first.

This implementation follows the representation strategy table in `docsV1/V1_MASTER_PLAN.md`.

The implementation must build and validate semantic topology before accepting generated geometry.

Primary topology objects:

- closed station profiles
- semantic profile nodes
- semantic profile edges
- station-direction edge network
- face rows
- shell edge adjacency
- cap faces

Part geometry is created only after topology validation passes.

Implementation rule:

```text
Topology contracts first
  -> topology validation
  -> Part face/shell/solid mapping
  -> geometry validity checks
```

This prevents the system from depending on unstable FreeCAD display edge names or stitched viewer mesh artifacts.

## 4. Current Baseline

Available now:

- Applied Sections persist frame and point rows.
- Build Corridor creates `V1CorridorModel` and `V1SurfaceModel`.
- Build Corridor can preview design, subgrade, daylight, drainage, Region Boundary, and Surface Transition results.
- Structure solid output exists for structure-focused output and exchange paths.
- Surface and solid representation boundaries are documented.

Main gaps:

- no `Watertight Solids` toolbar command
- no solid target source/result contract for corridor bodies
- no closed profile result model
- no topology-first edge/face/shell validation service
- no corridor-body Part solid mapper
- no final solid review UI
- no generic `WatertightSolidOutput` contract

## 5. Target Build Flow

```text
Watertight Solids command
  -> prerequisite scan
  -> target discovery
  -> target selection
  -> closed profile build
  -> profile validation
  -> edge network build
  -> face set build
  -> shell validation
  -> FreeCAD Part solid mapping
  -> output object persistence
  -> 3D preview and diagnostics
```

The first code path should build a simple `road_body_envelope` target.

Region, pavement layer, drainage, and structure targets should build on the same contracts after the envelope path is stable.

Target-family expansion beyond the baseline envelope is detailed in `docsV1/V1_WATERTIGHT_SOLID_TARGET_EXPANSION_PLAN.md`.

## 6. Code Placement

### 6.1 New source model files

- `freecad/Corridor_Road/v1/models/source/solid_target_model.py`

Primary classes:

- `SolidTargetModel`
- `SolidTargetRow`
- `SolidTargetDiagnosticRow`

### 6.2 New result model files

- `freecad/Corridor_Road/v1/models/result/solid_profile.py`
- `freecad/Corridor_Road/v1/models/result/solid_edge_network.py`
- `freecad/Corridor_Road/v1/models/result/watertight_solid_result.py`

Primary classes:

- `AppliedSectionSolidProfileSet`
- `AppliedSectionSolidProfile`
- `SolidProfileNode`
- `SolidProfileEdge`
- `SolidEdgeNetwork`
- `SolidNetworkNode`
- `SolidNetworkEdge`
- `SolidFaceRow`
- `WatertightSolidResult`
- `WatertightSolidDiagnosticRow`

### 6.3 New output model files

- `freecad/Corridor_Road/v1/models/output/watertight_solid_output.py`

Primary classes:

- `WatertightSolidOutput`
- `WatertightSolidOutputRow`
- `WatertightSolidSegmentRow`
- `WatertightSolidOutputDiagnosticRow`

### 6.4 New object bridge files

- `freecad/Corridor_Road/v1/objects/obj_solid_target.py`
- `freecad/Corridor_Road/v1/objects/obj_watertight_solid.py`

Object responsibilities:

- persist solid targets
- persist accepted output rows and diagnostics
- route objects under a v1 output or corridor result tree location
- keep generated Part solid preview objects marked as outputs

### 6.5 New service files

- `freecad/Corridor_Road/v1/services/builders/solid_target_discovery_service.py`
- `freecad/Corridor_Road/v1/services/builders/solid_profile_builder.py`
- `freecad/Corridor_Road/v1/services/builders/solid_edge_network_builder.py`
- `freecad/Corridor_Road/v1/services/builders/watertight_solid_builder.py`
- `freecad/Corridor_Road/v1/services/evaluation/solid_profile_validation_service.py`
- `freecad/Corridor_Road/v1/services/evaluation/watertight_shell_validation_service.py`
- `freecad/Corridor_Road/v1/services/mapping/watertight_solid_part_mapper.py`
- `freecad/Corridor_Road/v1/services/mapping/watertight_solid_output_mapper.py`

### 6.6 New command/UI files

- `freecad/Corridor_Road/v1/commands/cmd_watertight_solids.py`

Optional later UI extraction:

- `freecad/Corridor_Road/v1/ui/editors/watertight_solids_panel.py`

### 6.7 Files likely to update

- `freecad/Corridor_Road/init_gui.py`
- `freecad/Corridor_Road/v1/models/source/__init__.py`
- `freecad/Corridor_Road/v1/models/result/__init__.py`
- `freecad/Corridor_Road/v1/models/output/__init__.py`
- `freecad/Corridor_Road/v1/objects/__init__.py`
- `freecad/Corridor_Road/v1/services/builders/__init__.py`
- `freecad/Corridor_Road/v1/services/evaluation/__init__.py`
- `freecad/Corridor_Road/v1/services/mapping/__init__.py`
- `freecad/Corridor_Road/objects/obj_project.py`

## 7. UI Implementation Plan

### 7.1 Toolbar command

Add top-level command:

`CorridorRoad_V1_WatertightSolids`

Toolbar label:

`Watertight Solids`

Toolbar placement:

```text
... -> Outputs & Exchange -> AI Assist -> Watertight Solids
```

The command is the final toolbar item.

### 7.2 Activation and gating

The command should be visible but blocked until prerequisites exist.

First implementation can use a disabled-like command behavior if dynamic toolbar enablement is difficult in FreeCAD:

- command remains visible
- opening it without prerequisites shows a clear panel/message
- build buttons remain disabled

Prerequisites:

- `V1AppliedSectionSet` exists
- `V1CorridorModel` exists
- `V1SurfaceModel` exists or a future corridor build record says surface output was intentionally skipped
- selected target family has enough semantic section data

Blocked message:

`Run Build Corridor before generating watertight solids.`

### 7.3 Task panel layout

Recommended first task panel:

1. `Prerequisites`
2. `Solid Targets`
3. `Target Scope`
4. `Validation`
5. `Output`
6. `Diagnostics`

### 7.4 Solid Targets table

Columns:

- `Enabled`
- `Target`
- `Scope`
- `Start STA`
- `End STA`
- `Source`
- `Profiles`
- `Faces`
- `Volume`
- `Status`
- `Diagnostics`

Rows should be generated by target discovery, not manually typed at first.

### 7.5 Target Scope controls

Controls:

- target family combo
- Region combo
- station range combo or start/end station controls
- Assembly component combo
- Structure combo
- Drainage reference combo

First slice may enable only:

- target family: `road_body_envelope`
- scope: `whole corridor`

### 7.6 Buttons

Buttons:

- `Refresh Targets`
- `Validate`
- `Build Selected`
- `Build Enabled`
- `Show Solid`
- `Hide Solid`
- `Close`

Button behavior:

- `Validate` runs model and topology validation without creating Part solids.
- `Build Selected` creates or updates one preview/output.
- `Build Enabled` processes all enabled targets that pass validation.
- `Show Solid` focuses the generated Part object.

## 8. Data Contracts

### 8.1 SolidTargetRow

Required first fields:

- `target_id`
- `target_family`
- `scope_kind`
- `station_start`
- `station_end`
- `region_ref`
- `assembly_ref`
- `component_ref`
- `structure_ref`
- `drainage_ref`
- `enabled`
- `priority`
- `material_ref`
- `notes`

Target families:

- `road_body_envelope`
- `region_body`
- `pavement_layer_body`
- `lined_ditch_body`
- `structure_body`

Scope kinds:

- `whole_corridor`
- `region`
- `station_range`
- `assembly_component`
- `structure`
- `drainage`

### 8.2 AppliedSectionSolidProfile

Required first fields:

- `profile_id`
- `target_id`
- `station`
- `applied_section_ref`
- `region_ref`
- `profile_role`
- `node_rows`
- `edge_rows`
- `is_closed`
- `orientation`
- `notes`

### 8.3 SolidProfileNode

Required first fields:

- `node_id`
- `semantic_role`
- `x`
- `y`
- `z`
- `lateral_offset`
- `vertical_offset`
- `source_point_ref`

### 8.4 SolidProfileEdge

Required first fields:

- `edge_id`
- `start_node_id`
- `end_node_id`
- `semantic_role`
- `source_ref`

### 8.5 SolidFaceRow

Required first fields:

- `face_id`
- `target_id`
- `face_kind`
- `node_ids`
- `edge_ids`
- `station_start`
- `station_end`
- `source_refs`

Face kinds:

- `top`
- `bottom`
- `left_side`
- `right_side`
- `start_cap`
- `end_cap`
- `transition`

### 8.6 WatertightSolidOutputRow

Required first fields:

- `output_object_id`
- `target_id`
- `target_family`
- `scope_kind`
- `station_start`
- `station_end`
- `source_refs`
- `generated_object_ref`
- `validation_status`
- `is_watertight`
- `is_valid_solid`
- `volume`
- `face_count`
- `edge_count`
- `diagnostic_refs`

## 9. Build Algorithms

### 9.1 Target discovery

First discovery rules:

- if Applied Sections and CorridorModel exist, create one `road_body_envelope` candidate
- if RegionModel exists, create one `region_body` candidate per Region
- if StructureModel rows exist, create one `structure_body` candidate per eligible structure
- if Assembly component/layer semantics exist, create future `pavement_layer_body` candidates
- if ditch material policy indicates lining or structural material, create future `lined_ditch_body` candidates

### 9.2 Road body envelope profile

First slice profile:

1. read each Applied Section frame
2. find or derive top-left and top-right points
3. find or derive bottom-left and bottom-right points
4. build closed profile:

```text
top_left -> top_right -> bottom_right -> bottom_left -> top_left
```

Initial bottom rule:

- prefer `subgrade_surface` point rows where available
- otherwise use design top points with a configured fallback depth

The fallback depth must be stored in diagnostics and should not pretend to be material-specific design truth.

### 9.3 Region body profile

Region body generation uses the same profile rule as road body envelope, but filters Applied Sections by active Region and inserts boundary profiles at Region start/end where needed.

### 9.4 Pavement layer profile

Deferred until component/layer semantics are stable.

Profile should use material layer thickness and component boundaries rather than the simplified envelope depth.

### 9.5 Lined ditch profile

First-slice profile generation is available when side-specific `ditch_surface` rows and lining policy are present.

Profile should be closed by offsetting ditch surface roles according to lining thickness policy.

Current first TS3 rule:

- `ditch_surface` rows may discover side-specific `lined_ditch_body` target candidates.
- candidates without material and positive lining thickness remain blocked.
- candidates with surface rows and lining policy are available.
- Applied Section component rows preserve ditch parameters such as `lining_thickness`.
- the profile builder uses the side-specific ditch surface polyline plus section-normal lining-thickness offsets.
- when intermediate ditch surface points are present, they are preserved as profile nodes and an info diagnostic records `lined_ditch_polyline_normal_offset`.

### 9.6 Structure body profile

Structure body should reuse or align with existing structure solid output work.

The watertight solid stage should first reference existing structure outputs, then later support richer corridor-following structure bodies.

## 10. Topology Rules

Topology rules are the primary acceptance rules for watertight solid generation.

Coordinate geometry may be corrected or rejected by validation, but it must not silently override topology.

### 10.1 Profile orientation

All profiles for one target must use the same node order.

First `road_body_envelope` orientation:

```text
top_left -> top_right -> bottom_right -> bottom_left
```

### 10.2 Longitudinal direction

Longitudinal edges follow increasing station.

### 10.3 Face creation

For adjacent profiles `i` and `i+1`, create side faces by matching semantic node ids.

For a four-node profile:

- top face strip
- right side face strip
- bottom face strip
- left side face strip
- start cap
- end cap

The topology `SolidFaceRow` remains the engineering face contract.

The FreeCAD Part mapper may split a validated topology face into triangular `Part.Face` objects when FreeCAD cannot build one polygon face, such as a slightly non-planar corridor strip.

This is a representation step, not topology repair.

The mapper must preserve a warning diagnostic such as `part_face_triangulated` so the user can review where Part geometry differed from the topology face contract.

### 10.4 Validation tolerance

Initial tolerance:

- coordinate match tolerance: `1.0e-6 m`
- short edge warning threshold: `1.0e-4 m`
- tiny face area warning threshold: `1.0e-8 m2`

Tolerance should be centralized in one constants block.

### 10.5 Edge usage rule

A watertight shell requires every topological edge to be used by exactly two faces.

Validation should report:

- dangling edge
- duplicate edge
- non-manifold edge
- missing cap
- invalid profile order

### 10.6 Geometry quality warning rule

Closed topology can still be risky geometry.

Validation should report non-blocking warnings for:

- `short_topology_edge` when an edge length is below `1.0e-4 m`
- `tiny_topology_face_area` when a face area is below `1.0e-8 m2`

These warnings do not block `validation_status = ok`.

They must be preserved in diagnostics so the user can review low-quality solids before export.

### 10.7 Topology-before-geometry gate

The Part mapper must reject any target that has topology errors.

Required gate:

```text
profile validation status == ok
edge network validation status == ok
shell topology validation status == ok
```

Only then may the mapper create `Part.Face`, `Part.Shell`, or `Part.Solid`.

## 11. FreeCAD Part Mapping

### 11.1 Mapper purpose

`WatertightSolidPartMapper` converts validated face rows into FreeCAD Part shapes.

It is a mapper, not the owner of engineering logic.

It must not repair topology silently.

### 11.2 First mapping strategy

For the first slice:

- build planar polygon faces from four-node strips and cap profiles
- triangulate a validated topology face only when FreeCAD rejects direct polygon face creation
- create a `Part.Shell`
- create a `Part.Solid`
- run FreeCAD validity checks

Expected calls may include:

- `Part.makePolygon`
- `Part.Face`
- `Part.Shell`
- `Part.Solid`
- `shape.isValid()`
- `shape.Volume`

FreeCAD object creation should be skipped in headless contexts where Part is not available.

The mapper should report geometry failures separately from topology failures.

If triangulation also fails, report `part_face_creation_failed` with both direct-face and triangulation details.

### 11.3 Preview object properties

Generated preview/output objects should include:

- `CRRecordKind = v1_watertight_solid_preview`
- `V1ObjectType = V1WatertightSolidPreview`
- `TargetId`
- `TargetFamily`
- `ScopeKind`
- `StationStart`
- `StationEnd`
- `ValidationStatus`
- `IsWatertight`
- `Volume`
- `FaceCount`
- `SourceRefs`

## 12. Diagnostics

Diagnostic severity:

- `info`
- `warning`
- `error`

Blocking errors:

- missing Applied Sections
- missing CorridorModel
- fewer than two profiles
- any profile is not closed
- semantic node mismatch between profiles
- missing start cap
- missing end cap
- dangling shell edge
- non-manifold shell edge
- invalid Part solid
- non-positive volume

Warnings:

- fallback bottom depth used
- short edges found
- tiny faces found
- self-intersection not fully checked
- structure target delegated to existing Structure Output

## 13. Tests

### 13.1 Contract tests

New tests:

- `tests/contracts/v1/test_watertight_solid_models.py`
- `tests/contracts/v1/test_solid_target_discovery_service.py`
- `tests/contracts/v1/test_solid_profile_builder.py`
- `tests/contracts/v1/test_watertight_shell_validation_service.py`
- `tests/contracts/v1/test_watertight_solid_part_mapper.py`
- `tests/contracts/v1/test_watertight_solids_command.py`

### 13.2 Required first test cases

Model tests:

- solid target rows round-trip through dataclasses
- output rows preserve source refs and diagnostics

Discovery tests:

- no Applied Sections returns blocked target state
- valid corridor state returns one `road_body_envelope` target
- RegionModel returns Region target candidates

Profile tests:

- road body envelope creates closed four-node profiles
- missing subgrade rows uses fallback depth warning
- mismatched profile nodes raise validation error

Topology tests:

- valid two-profile envelope has no dangling edges
- missing end cap reports open shell
- duplicated face reports non-manifold or duplicate edge diagnostic
- Part mapping is skipped when topology validation fails

Part mapper tests:

- valid simple envelope maps to a positive-volume solid when FreeCAD Part is available
- invalid topology does not create a Part solid

Command tests:

- command is registered after `AI Assist`
- command reports Build Corridor prerequisite when missing
- command opens target table when prerequisites exist
- `Validate` updates diagnostics without creating solids
- `Build Selected` creates or updates one preview object

## 14. Implementation Phases

### Phase WS0: Documentation and command placeholder

Status: Complete for toolbar placeholder, prerequisite gate, panel shell, and contract tests.

Tasks:

- add this implementation plan
- add placeholder `cmd_watertight_solids.py`
- register command after `AI Assist`
- show prerequisite message when Build Corridor outputs are missing

Acceptance:

- toolbar contains `Watertight Solids` at the end
- command does not crash without prerequisites
- no solid geometry is generated yet

### Phase WS1: SolidTarget contracts and discovery

Status: Complete for source contracts, discovery service, target table population, blocked-state diagnostics, and contract tests. Target persistence as document objects is deferred until a later slice proves it is needed.

Tasks:

- implement `SolidTargetModel`
- implement target discovery service
- defer object bridge until target persistence is required
- add target table UI

Acceptance:

- `road_body_envelope` target appears after Build Corridor
- Region targets appear when RegionModel exists
- blocked states are visible and diagnostic

### Phase WS2: Closed profile builder

Status: Complete for AppliedSection solid profile contracts, road/Region envelope profile building, boundary-station interpolation inside the Watertight Solid result stage, fallback-depth diagnostics, and contract tests. FreeCAD Part geometry is still deferred to later phases.

Tasks:

- implement `AppliedSectionSolidProfile`
- build `road_body_envelope` profiles from Applied Sections
- derive bottom points from subgrade or fallback depth
- validate profile closure and node order

Acceptance:

- at least two closed profiles are produced for a valid corridor
- missing semantic rows produce clear diagnostics
- Region boundary profiles can be interpolated without mutating Applied Sections

### Phase WS3: Edge network and shell validation

Status: Complete for topology-only edge-network contracts, deterministic face rows, canonical edge usage counting, closed-shell validation, and contract tests. FreeCAD Part mapping remains deferred to WS4.

Tasks:

- implement edge network builder
- implement face row generation
- implement shell topology validation independent of FreeCAD shape names
- enforce the topology-before-geometry gate

Acceptance:

- valid envelope has zero dangling edges
- every generated topology edge is used by exactly two faces
- invalid profile order blocks face generation before geometry mapping
- missing cap and node mismatch tests fail clearly
- Part mapper cannot run for invalid topology

### Phase WS4: Part solid mapper and preview

Status: Complete for validated topology-to-Part shape mapping, positive-volume solid validation, topology gate blocking, and contract tests. Document preview object creation and show/hide/focus actions remain deferred to the UI/output slice.

Tasks:

- implement Part mapper
- defer create/update preview object to the UI/output slice
- defer show/hide/focus actions to the UI/output slice
- defer preview-object validation properties to the output object bridge

Acceptance:

- simple road body envelope creates a valid positive-volume Part solid
- invalid topology is blocked before Part mapping
- generated shape result reports watertight, valid-solid, volume, face count, edge count, and diagnostics

### Phase WS5: WatertightSolidOutput

Status: Complete for output dataclasses, output mapping, segment metadata, diagnostic preservation, FreeCAD summary/shape object bridge, object lookup, and round-trip contract tests. UI summary exposure remains deferred to the interactive panel slice.

Tasks:

- implement output dataclasses
- map result and preview metadata to output rows
- persist output object summary and generated shape
- defer output summary exposure in UI to the interactive panel slice

Acceptance:

- generated solid rows round-trip through object bridge
- output rows preserve source refs, volume, and diagnostics
- generated Part shape can be stored on the v1 watertight solid output object

### Phase WS6: Region target

Status: Complete for Region-body profile filtering, start/end boundary cap profile insertion, non-target Region station skipping diagnostics, missing Region source profile diagnostics, independent capped topology, Part solid mapping, output mapping, and contract tests.

Tasks:

- filter profiles by selected Region
- insert source Region boundary profiles when needed
- build Region start/end caps

Acceptance:

- selected Region can produce an independent capped solid
- Region boundary diagnostics identify missing source rows
- station profiles from other Regions inside the target range are skipped with diagnostics

### Phase WS7: Component target expansion

Status: Complete for first-slice pavement-layer, subbase, shoulder, and lined-ditch target discovery, component-scoped closed profile building from Applied Section component width/thickness/side, independent topology/Part/output validation, StructureModel `structure_body` target discovery for review, and contract tests. Lined ditch generation supports multi-point ditch surface polylines with section-normal lining offsets. Lined ditch output diagnostics now preserve shape and lining-policy provenance, exchange source context preserves drainage/material refs, panel show/hide/focus status keeps drainage side context visible, target discovery can promote a matching `DrainageModel` ditch/channel element to the lined ditch solid owner, persisted `V1DrainageModel` document objects feed Watertight Solid discovery, and component parameters can control `normal_average` versus `miter` join behavior with a miter limit fallback diagnostic.

Tasks:

- add pavement layer target
- defer lined ditch target until material policies are stable
- connect structure target review to existing StructureModel/StructureSolidOutput source context

Acceptance:

- component targets appear only when their source semantics are available
- each target remains independently validatable
- structure targets appear when StructureModel rows expose station placement and native geometry specs

### Phase WS8: Quantity and exchange handoff

Status: Complete for accepted watertight solid volume quantity fragments, total volume aggregation, exchange package metadata, separate watertight solid rows/segments, watertight source-context rows, and contract tests. IFC-specific solid entity mapping remains a later exchange-format specialization.

Tasks:

- map accepted watertight solids to quantity rows
- add exchange package payload fields where appropriate
- defer IFC entity specialization for validated solids to a later exchange-format slice

Acceptance:

- accepted solids can feed quantity summaries
- exchange output carries target/source/validation metadata
- watertight solid exchange payloads remain separate from structure solid payloads

## 15. Manual QA

Current interactive panel QA should verify:

1. Open a project with valid TIN, Alignment, Stations, Profile, Assembly, Region, Applied Sections, and Build Corridor outputs.
2. Confirm `Watertight Solids` appears after `AI Assist`.
3. Open `Watertight Solids`.
4. Confirm prerequisites show ready.
5. Refresh targets.
6. Confirm the target table contains a `Target` value of `road_body_envelope`.
7. Click the `road_body_envelope` row in the target table. This is the intended selection action.
8. Confirm the row selection highlight moves to `road_body_envelope`.
9. Confirm `Validate` becomes enabled for the available selected target.
10. Toggle the `Enabled` cell and confirm the panel status updates the enabled target count.
11. Click `Validate`.
12. Confirm validation status, profile count, face count, edge count, and diagnostics update in the target table.
13. Confirm no Part solid or output object is created by validation alone.
14. Confirm `Build Selected` becomes enabled after successful validation.
15. Click `Build Selected`.
16. Confirm a `V1WatertightSolidOutput_<safe target id>` object is created.
17. Confirm the generated object has `V1ObjectType = V1WatertightSolidOutput`.
18. Confirm the generated object has positive `Shape.Volume`.
19. Confirm `Build`, `Volume`, and `Output` update in the target table.
20. Enable at least one additional available target when present.
21. Confirm `Build Enabled` becomes enabled when an available target has `Enabled = true`.
22. Click `Build Enabled`.
23. Confirm each enabled available target builds independently.
24. Confirm the panel shows built count, failed count, target count, and total volume.
25. Select a built target row.
26. Click `Hide Solid` and confirm the generated solid is hidden.
27. Click `Show Solid` and confirm the generated solid is visible.
28. Click `Focus Solid` and confirm the generated solid is selected and framed when the GUI view is available.
29. Double-click the built target row and confirm the same focus behavior runs.
30. Confirm generated watertight solid output objects appear under `09_Outputs & Exchange -> Watertight Solids`.

Future interactive build QA should verify after the UI execution slice is implemented:

1. Confirm failed bulk targets keep diagnostics visible while later targets continue.
2. Change Region or Assembly source.
3. Rebuild Applied Sections and Build Corridor.
4. Rebuild the solid and confirm diagnostics update.

## 16. Risks

Primary risks:

- Applied Sections do not yet provide enough semantic nodes for clean layer solids
- fallback envelope depth may be mistaken for real pavement material thickness
- FreeCAD Part face creation may fail on twisted or non-planar profile strips
- large corridors may create too many faces for interactive preview
- Region boundaries may require inserted profiles to avoid gaps

Mitigations:

- start with a simple four-node envelope
- label fallback geometry clearly
- validate topology before Part mapping
- block geometry creation when topology fails
- build selected targets before bulk build
- keep generated solids as outputs

## 17. Non-goals

This implementation plan does not deliver full pavement material design in the first slice.

This implementation plan does not deliver hydraulic analysis.

This implementation plan does not boolean-union all corridor, drainage, and structure bodies.

This implementation plan does not make generated Part solids editable source geometry.
