# Parametric Road V1 Watertight Solid UI Execution Plan

Date: 2026-05-07  
Status: Draft execution plan  
Scope: interactive `Watertight Solids` panel execution after WS0-WS8 backend contracts

Depends on:

- `docsV1/V1_MASTER_PLAN.md`
- `docsV1/V1_WATERTIGHT_SOLID_PLAN.md`
- `docsV1/V1_WATERTIGHT_SOLID_IMPLEMENTATION_PLAN.md`
- `docsV1/V1_CORRIDOR_MODEL.md`
- `docsV1/V1_OUTPUT_STRATEGY.md`

## 1. Purpose

This document defines how the existing watertight solid backend pipeline becomes an executable user workflow in the `Watertight Solids` task panel.

The backend contracts already cover:

- target discovery
- closed profile building
- topology edge-network validation
- FreeCAD Part solid mapping
- watertight solid output mapping
- quantity and exchange handoff

The remaining gap is interactive execution from the panel.

## 2. Current UI State

The current panel supports:

- prerequisite scan
- target discovery
- target table display
- row selection by clicking a target row
- selected target status text
- editable `Enabled` check state per target row
- `Validate` button readiness for an available selected target
- `Validate` execution for the selected target
- `Build Selected` execution for a validated selected target
- `Build Enabled` execution for enabled available targets
- `Show Solid`, `Hide Solid`, and `Focus Solid` for built outputs
- row double-click focus for built outputs
- dedicated project-tree group routing
- refresh

`Validate` is enabled only after an available target row is selected.
`Build Selected` is enabled after the selected target validates successfully.
`Build Enabled` is enabled after at least one available target row has `Enabled = true`.
Display controls are enabled after the selected target has a generated output object.

## 3. UX Rule

The target table is the primary interaction surface.

Target selection means:

```text
Click one target row in the target table.
```

For example:

```text
Click the row whose Target value is road_body_envelope.
```

Double-clicking a built target row runs `Focus Solid`.

## 4. Target Table Columns

Current columns:

- `Enabled`
- `Target`
- `Scope`
- `Source`
- `Status`
- `Validation`
- `Profiles`
- `Faces`
- `Edges`
- `Build`
- `Volume`
- `Output`
- `Diagnostics`

Required next columns:

- none for Slice UI4

Column meaning:

- `Enabled`: whether the row participates in `Build Enabled`
- `Target`: target family such as `road_body_envelope`, `region_body`, `pavement_layer_body`
- `Scope`: whole corridor, Region, station range, component, structure, drainage
- `Source`: source refs used to discover the target
- `Status`: discovery readiness such as `available` or `blocked`
- `Validation`: `not_validated`, `ok`, `blocked`, or `error`
- `Profiles`: closed profile count from validation
- `Faces`: topology face count
- `Edges`: topology edge count
- `Build`: `not_built`, `built`, `blocked`, or `error`
- `Volume`: generated Part solid volume when built
- `Output`: generated FreeCAD object name
- `Diagnostics`: discovery, validation, and build diagnostics

## 5. Panel State

The panel should maintain an in-memory execution state per target row.

Required state fields:

- `target_id`
- `selected`
- `enabled`
- `validation_status`
- `profile_set`
- `edge_network`
- `part_result`
- `watertight_output`
- `output_object`
- `diagnostic_rows`

State is regenerated when `Refresh` is pressed.

Generated output objects remain in the document.

## 6. Validate Button

### 6.1 Activation

`Validate` is enabled when:

- prerequisites are ready
- one target row is selected
- selected target readiness is `available`

### 6.2 Execution

`Validate` runs:

```text
selected SolidTargetRow
  -> AppliedSectionSolidProfileService
  -> SolidEdgeNetworkService
```

It does not create Part geometry.

It does not create or update a FreeCAD output object.

### 6.3 UI Result

On success:

- `Validation = ok`
- profile count is displayed
- face count and edge count are displayed
- diagnostics are displayed
- `Build Selected` remains disabled until Slice UI3

On failure:

- `Validation = error`
- diagnostics are displayed
- `Build Selected` remains disabled

## 7. Build Selected Button

### 7.1 Activation

`Build Selected` is enabled when:

- one target row is selected
- selected target has passed validation

If the selected target has not been validated, `Build Selected` may run validation first.

### 7.2 Execution

`Build Selected` runs:

```text
selected SolidTargetRow
  -> AppliedSectionSolidProfileService
  -> SolidEdgeNetworkService
  -> WatertightSolidPartMapper
  -> WatertightSolidOutputMapper
  -> create_or_update_v1_watertight_solid_output_object
```

### 7.3 Output Object

The generated object uses:

- `V1ObjectType = V1WatertightSolidOutput`
- `CRRecordKind = v1_watertight_solid_output`
- `Shape = generated Part.Solid`

Object name rule:

```text
V1WatertightSolidOutput_<safe target id>
```

Example:

```text
V1WatertightSolidOutput_solid_target_road_body_envelope
```

### 7.4 UI Result

On success:

- `Build Status = built`
- `Volume` is populated
- `Faces` is populated
- `Edges` is populated
- `Output Object` is populated
- the generated object is visible in the 3D view

On failure:

- `Build Status = failed`
- diagnostics explain the failure
- no topology repair is performed silently

## 8. Build Enabled Button

### 8.1 Activation

`Build Enabled` is enabled when:

- prerequisites are ready
- at least one available target row has `Enabled = true`

### 8.2 Execution

`Build Enabled` loops over enabled targets and runs the same pipeline as `Build Selected`.

Each target is isolated.

One target failure must not block later enabled targets.

### 8.3 UI Result

The panel summarizes:

- built count
- failed count
- total volume
- diagnostic count

## 9. Enabled Editing

The `Enabled` column should become editable as a checkbox.

Initial default:

- `road_body_envelope`: disabled
- `region_body`: disabled
- `pavement_layer_body`: disabled
- `structure_body`: disabled

Reason:

The user should explicitly choose which solid bodies to generate.

Bulk building should never run implicitly on all discovered targets.

## 10. Diagnostics UI

Diagnostics should appear in two places:

- target row summary
- detail panel for selected target

The detail panel should show:

- severity
- kind
- message
- notes

Blocking diagnostics are `error`.

Warnings do not block build unless they are promoted by validation policy.

## 11. Show, Hide, And Focus

Controls:

- `Show Solid`
- `Hide Solid`
- `Focus Solid`

Button behavior:

- `Show Solid`: sets output object visibility true
- `Hide Solid`: sets output object visibility false
- `Focus Solid`: selects the output object and fits view if GUI is available

Double-clicking a built target row should run `Focus Solid`.

Double-clicking an unbuilt target row should not create geometry.

In command-line validation where `ViewObject` or an active GUI view is unavailable, display actions must remain non-crashing and report the unavailable visibility/focus path in panel status.

## 12. Project Tree Placement

Watertight solid outputs should route under the final output stage.

Preferred route:

```text
09_Outputs & Exchange
  -> Watertight Solids
```

Objects with `CRRecordKind = v1_watertight_solid_output` route to this group.

## 13. Manual QA After UI Execution

Manual QA should verify:

1. Open a project with valid Build Corridor prerequisites.
2. Open `Watertight Solids`.
3. Click the `road_body_envelope` target row.
4. Confirm `Validate` becomes enabled.
5. Click `Validate`.
6. Confirm topology status, face count, edge count, and diagnostics update.
7. Confirm no Part solid is created by validation alone.
8. Click `Build Selected`.
9. Confirm a `V1WatertightSolidOutput` object is created.
10. Confirm the object has a visible Part solid shape.
11. Confirm volume is positive.
12. Click `Hide Solid`.
13. Confirm the output object is hidden.
14. Click `Show Solid`.
15. Confirm the output object is visible.
16. Click `Focus Solid`.
17. Confirm the generated object is selected and framed.

## 14. Implementation Slices

### Slice UI1: Selection And Button State

Status: implemented.

Tasks:

- track selected target row
- enable `Validate` for available selected target
- expose selected target details
- make `Enabled` editable

Acceptance:

- clicking `road_body_envelope` enables `Validate`
- blocked targets keep `Validate` disabled
- enabled checkbox updates panel state

### Slice UI2: Validate Execution

Status: implemented.

Tasks:

- resolve current AppliedSectionSet, CorridorModel, RegionModel, StructureModel
- run profile and edge-network builders
- store per-target validation result
- show diagnostics

Acceptance:

- `Validate` produces face/edge counts
- validation does not create Part geometry
- invalid target shows errors

### Slice UI3: Build Selected

Status: implemented.

Tasks:

- run validation if needed
- run Part mapper
- run output mapper
- create/update `V1WatertightSolidOutput` object
- update target row status

Acceptance:

- selected target creates a visible solid
- volume is shown
- output object name is shown

### Slice UI4: Build Enabled

Status: implemented.

Tasks:

- loop over enabled targets
- isolate failures per target
- summarize build results

Acceptance:

- enabled available targets build independently
- failed target diagnostics remain visible

### Slice UI5: Show/Hide/Focus

Status: implemented.

Tasks:

- add display action buttons
- implement row double-click focus for built targets
- preserve selected target after refresh when possible

Acceptance:

- built target can be shown, hidden, and focused

### Slice UI6: Tree Refinement

Status: implemented.

Tasks:

- add dedicated `Watertight Solids` group under `Outputs & Exchange`
- route generated output objects there
- route existing `V1WatertightSolidOutput` objects there when the Watertight Solids panel opens or refreshes

Acceptance:

- generated solids are easy to find in the project tree
- tree-visible solid objects can be hidden/shown and inspected through FreeCAD object properties

## 15. Non-goals

This UI plan does not change source models.

This UI plan does not make generated solids editable engineering intent.

This UI plan does not add lined ditch policy.

This UI plan does not implement IFC entity specialization.

This UI plan does not boolean-union all generated bodies.
