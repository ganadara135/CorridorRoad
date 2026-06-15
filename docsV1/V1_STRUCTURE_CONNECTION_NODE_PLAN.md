# Parametric Road V1 Structures Enhancement Plan

Date: 2026-05-20
Status: Updated implementation plan from the current v1 code baseline

Depends on:

- `docsV1/V1_MASTER_PLAN.md`
- `docsV1/V1_STRUCTURE_MODEL.md`
- `docsV1/V1_STRUCTURE_GEOMETRY_CONTRACT.md`
- `docsV1/V1_DRAINAGE_MODEL.md`
- `docsV1/V1_DRAINAGE_FLOW_ROUTE_IMPLEMENTATION_PLAN.md`
- `docsV1/V1_BUILD_PARAMETRIC_STABILIZATION_PLAN.md`
- `docsV1/V1_WATERTIGHT_SOLID_TARGET_EXPANSION_PLAN.md`

## 1. Purpose

This document defines the next Structures enhancement work from the current code state.

The goal is to make Structures a connection-ready v1 source domain that can support:

- general corridor structures
- drainage structures such as inlets, culverts, outlets, and headwalls
- 3D review and project-tree visibility
- Build Parametric context review
- Watertight Solid target discovery and simulation-ready output

Structures are source intent.

Structure preview objects, pipe previews, generated solids, and export geometry are outputs.

## 2. Current Code Baseline

The current implementation already provides these pieces:

| Area | Current state |
|---|---|
| Source model | `StructureModel`, `StructureRow`, `StructurePlacement`, `StructureGeometrySpec`, kind-specific geometry specs, and `StructureConnectionPoint` exist. |
| Geometry source | `StructureRow.geometry_source_mode` supports `native` and `external_ref`; `native_type` is stored on the row. |
| Editor | Structures panel has a compact main table and a `Selected Structure Detail` area. |
| Removed UI direction | The old visible `Geometry Specs` editing surface is no longer the target UX; geometry spec rows remain internal source contracts. |
| Native authoring | Native types include box/pipe culvert, bridge deck, retaining wall, headwall, inlet, and outlet. |
| Connection points | The editor can derive defaults, pick from 3D, preview points, and focus selected connection points. |
| Tree output | Structure preview objects and connection point preview objects are routed to the project tree. |
| Drainage handoff | Drainage Elements reference Structures; Flow Routes resolve pipe endpoints from Structure-owned connection points. |
| Drainage preview | `Show Flow Network` can create pipeline preview geometry from resolved Structure connection points. |
| Build Parametric | Region focus can include actual Structure and Drainage preview objects instead of placeholder boxes. |
| Watertight Solids | `structure_body`, `drainage_pipeline_body`, and `drainage_pipeline_network_body` targets exist; native/external structure body handling has first-slice support. |

## 3. Core Rule

Drainage and Watertight Solids must not connect to anonymous preview geometry.

They must connect through stable source ids:

```text
StructureRow
-> StructureConnectionPoint
-> DrainageElement
-> FlowRoute
-> DrainagePipelineSegment
-> Watertight Solid output
```

Preview geometry may show this relationship, but it must not become the design source.

## 4. Target Mental Model

Use four distinct layers:

| Layer | Owner | Meaning |
|---|---|---|
| Structure source | `StructureModel` | Physical or reference structure placed in station/offset space. |
| Geometry source | `StructureModel` | Native parametric body or external referenced body. |
| Connection points | `StructureModel` | Stable named ports such as `pipe_in`, `pipe_out`, `upstream`, `downstream`, `discharge`. |
| Pipeline/solid outputs | Drainage and Watertight outputs | Generated pipe segments, network solids, structure bodies, and export geometry. |

The user edits Structures as source rows.

The system evaluates those rows into preview, drainage, and solid output contracts.

## 5. Workflow Position

Structures stay in the source-authoring part of the workflow:

```text
Alignment
-> Stations
-> Profile
-> 3D Centerline
-> Assembly
-> Regions
-> Structures
-> Drainage
-> Applied Sections
-> Build Parametric
-> Watertight Solids
```

Why this order:

- Structures need accepted Region and 3D Centerline context.
- Drainage needs accepted Structure refs and connection points.
- Build Parametric should review generated corridor and domain outputs.
- Watertight Solids should consume completed Build Parametric and source/result contracts.

## 6. Structure Families

Structures should support two broad families.

| Family | Examples | Drainage behavior |
|---|---|---|
| General corridor structure | bridge, retaining wall, barrier, custom object | May affect corridor context, quantities, and solids; not automatically a drainage node. |
| Drainage-ready structure | inlet, outlet, headwall, culvert, manhole, junction box | Must expose connection points before Drainage pipeline output can be trusted. |

Assembly remains limited to reusable road section Subassemblies.

Drainage-related physical nodes belong in Structures, not Assembly.

## 7. Native And External Geometry Strategy

Each Structure row has one geometry source mode.

| Mode | Meaning | User-facing expectation | Validation |
|---|---|---|---|
| `native` | Parametric Road builds a simplified body from source dimensions. | User picks Native Type and practical dimensions in `Selected Structure Detail`. | Require native type and valid dimensions. |
| `external_ref` | User references an existing FreeCAD/imported object. | User picks an external body and maps connection points. | Require geometry ref; drainage-ready external refs require mapped connection points. |

Native and external geometry share the same connection point contract.

Drainage should not care how the body was authored once endpoints are available.

## 8. Selected Structure Detail

`Selected Structure Detail` is the single user-facing place for detailed Structure editing.

It should own:

- geometry source mode
- native type
- external geometry ref
- common dimensions
- native type-specific dimensions
- shape/material/display role
- connection point rows
- validation status for the selected Structure

The main Structures table should remain compact:

- `Structure ID`
- `Kind`
- `Role`
- `Start STA`
- `End STA`
- `Offset`
- `Region`
- short status columns only when useful

The user should not have to edit internal `Spec ID`, `Structure Ref`, or `Length Mode`.

## 9. Connection Point Contract

`StructureConnectionPoint` is the stable source endpoint for Structure-to-Drainage connectivity.

Current source fields:

- `connection_point_id`
- `structure_ref`
- `point_role`
- `station`
- `offset`
- `elevation`
- `invert_elevation`
- `diameter`
- `width`
- `height`
- `shape_kind`
- `direction`
- `connection_order`
- `region_ref`
- `notes`

Recommended role meanings:

| Role | Meaning |
|---|---|
| `inlet` | Open collection point from ditch/surface into a structure. |
| `pipe_in` | Closed pipe enters this structure. |
| `pipe_out` | Closed pipe leaves this structure. |
| `upstream` | Culvert upstream endpoint when legacy naming is used. |
| `downstream` | Culvert downstream endpoint when legacy naming is used. |
| `discharge` | Final outfall/discharge point. |

Preferred drainage route resolution:

```text
from Structure -> use outgoing role such as pipe_out/downstream
to Structure   -> use incoming role such as pipe_in/upstream
outlet target  -> use pipe_in/discharge context depending on target role
```

## 10. Current Gaps

The remaining Structures gaps are:

| Gap | Effect |
|---|---|
| Structure validation is still broad and partially warning-based. | Bad drainage nodes can reach later previews before the user sees a clear blocking reason. |
| Connection point role semantics need to be stricter. | Inlet-to-culvert and culvert-to-outlet routing can drift when endpoint choice is ambiguous. |
| Native shape detail is first-slice. | Culvert, inlet, outlet, and headwall bodies are useful but not yet detailed civil structure models. |
| External Ref mapping is manual-first. | Imported structure bodies need clearer port mapping and validation. |
| Watertight integration is first-slice. | Structure bodies can participate in drainage network solids, but robust boolean and port overlap QA need more work. |
| Tests are focused on contracts and command behavior. | More fixture coverage is needed for real drainage-chain and structure-solid scenarios. |

## 11. Implementation Plan

### ST-S1. Source Contract Cleanup

Status: Done

Tasks:

- [x] Keep `StructureModel` as the durable owner of structure geometry intent and connection points.
- [x] Treat `geometry_spec_rows` as internal source contracts behind `Selected Structure Detail`.
- [x] Keep the internal geometry-spec table detached from the visible UI and non-editable.
- [x] Remove unused internal geometry-spec delete helper from the editor.
- [x] Review compatibility fields and keep only fields still used by active commands/tests.
- [x] Keep source ids stable: `structure:*`, `geometry-spec:*`, `connection:*`.

Acceptance:

- [x] Structures can round-trip through the FreeCAD object without losing selected detail fields.
- [x] No UI path requires users to edit internal geometry spec ids.
- [x] Native and External Ref detail edits continue to write the same source contract.

Compatibility decision:

| Field / Surface | Decision | Reason |
|---|---|---|
| `geometry_spec_rows` | Keep, internal only | Needed for native dimensions, preview, solid, and object round-trip. |
| Hidden geometry-spec table | Keep as detached internal store | Current editor uses it as a compact table-backed source cache; it is not a user editing surface. |
| `geometry_spec_ref` | Keep | Stable link from `StructureRow` to common and kind-specific geometry specs. |
| `geometry_ref` | Keep | External Ref workflow needs a durable object/source reference. |
| `geometry_source_mode` | Keep | Explicitly separates `native` and `external_ref` behavior. |
| `native_type` | Keep | Drives practical defaults, validation, preview, and derived ports. |
| `reference_mode` | Keep as compatibility bridge | Active tests and object round-trip still use it to preserve source/external reference semantics. |

### ST-S2. Validation Upgrade

Status: Done

Tasks:

- [x] Add stricter drainage-ready validation for inlet, outlet, headwall, culvert, manhole, and junction box.
- [x] Validate supplied Region refs and station range against Region boundaries.
- [x] Validate connection point station range against the owning Structure placement.
- [x] Validate endpoint size by shape kind.
- [x] Validate role pairs:
  - inlet should have `inlet` and `pipe_out` when used as a pipe source
  - outlet/headwall should have `pipe_in` and optional `discharge`
  - culvert should have `pipe_in`/`pipe_out` or upstream/downstream equivalents
- [x] Return diagnostics with stable codes for UI and tests.

Acceptance:

- [x] Invalid drainage-ready examples report targeted diagnostics.
- [x] Valid `Drainage Structures` preset validates without blocking errors.

### ST-S3. Selected Structure Detail Polish

Status: Done

Tasks:

- [x] Keep table row selection synchronized with `Selected Structure Detail`.
- [x] Keep `Apply` and `Apply+Preview` behavior persistent after closing/reopening the panel.
- [x] Make disabled fields visually clear for non-applicable native/external modes.
- [x] Show selected Structure validation summary inside the detail area.
- [x] Keep connection point markers as clear sphere-style review helpers.

Acceptance:

- [x] Clicking any Structure row updates the detail area.
- [x] Applying, closing, and reopening shows the applied source data.
- [x] Connection point preview looks like intentional point markers, not broken geometry.

### ST-S4. Native Shape Authoring Upgrade

Status: Done

Tasks:

- [x] Keep native authoring simple and practical.
- [x] Improve type-specific defaults for:
  - `pipe_culvert`
  - `box_culvert`
  - `inlet`
  - `outlet`
  - `headwall`
  - `retaining_wall`
  - `bridge_deck`
- [x] Apply practical Structure kind and role defaults when Native Type changes.
- [x] Derive connection points from native type and dimensions when a selected Structure has no authored ports yet.
- [x] Make inlet/outlet/headwall defaults larger and easier to inspect in 3D.
- [x] Keep detailed grates, wingwalls, rebar, and vendor-level parts out of the first stable workflow.

Acceptance:

- [x] Native drainage structures are visually understandable.
- [x] Derived connection points align with the native body and pipeline preview.
- [x] User-authored connection points are not overwritten by native defaults.

### ST-S5. External Ref Mapping

Status: Done

Tasks:

- [x] Keep external body references separate from connection points.
- [x] Add `Pick External` guidance in `Selected Structure Detail` so the selected 3D/tree object can become the external body reference.
- [x] Keep `Pick From 3D` for connection-point mapping only.
- [x] Validate mapped connection points against the external object bounding box when the referenced object exists in the document.
- [x] Add diagnostics when a drainage-ready external ref has no mapped ports.
- [ ] Later: suggest ports from circular faces, named IFC ports, or object metadata.

Acceptance:

- [x] External Ref Structures can become drainage-ready through explicit connection point rows.
- [x] Replacing the external body does not destroy source-level endpoint ids.
- [x] External body validation reports connection points outside the referenced object bounds.

### ST-S6. Drainage Handoff Hardening

Status: Done

Tasks:

- [x] Keep Drainage Elements referencing Structures, not Structure preview objects.
- [x] Keep Flow Routes connecting Elements.
- [x] Resolve endpoint connection points by route direction and Structure role.
- [x] Preserve explicit Structure connection points instead of snapping every culvert `pipe_in` or `pipe_out` role to placement start/end.
- [x] Snap only derived/default culvert `upstream` and `downstream` endpoints to the current Structure placement when needed.
- [x] Double-clicking Flow Route rows can highlight resolved pipe/network objects in 3D.
- [x] Preserve connection point provenance in pipeline output rows.

Acceptance:

- [x] Inlet-to-inlet, inlet-to-culvert, and culvert-to-outlet routes connect through the correct Structure ports.
- [x] Explicit culvert `pipe_in` ports keep their authored station and offset.
- [x] Flow network preview and Watertight target discovery use the same resolved endpoints.

### ST-S7. Build Parametric Integration

Status: Done

Tasks:

- [x] Continue using actual generated Structure preview objects for Region and guided review focus.
- [x] Do not recreate placeholder Structure boxes inside Build Parametric.
- [x] Resolve Structure context by `v1_structure_row_preview` + `StructureRef`, not only by a fixed object name.
- [x] Surface missing Structure context as diagnostics.
- [x] Keep tree-visible outputs update-in-place.

Acceptance:

- [x] Build Parametric can focus Structure context without creating fake geometry.
- [x] Build Parametric can focus Structure context even when the preview object name differs from the default generated name.
- [x] Rebuilding does not create duplicate Structure preview objects.

### ST-S8. Watertight Solid Integration

Status: Done

Tasks:

- [x] Keep `structure_body` targets discoverable from `StructureModel`.
- [x] Keep `drainage_pipeline_network_body` able to auto-build needed Structure body dependencies.
- [x] Improve structure-port overlap checks before boolean fuse.
- [x] Record structure body refs and connection point refs in solid output diagnostics.
- [x] Record structure-port terminal count and contact status in build messages and solid notes.
- [x] Treat failed fuse as a visible warning/fallback, not a silent success.

Acceptance:

- [x] Structure bodies and drainage pipeline network bodies remain traceable to source Structure refs.
- [x] Pipeline network solids report `structure_port_contact_status` as `direct`, `trimmed`, `bridged`, `gap`, or `pending_structure_body`.
- [x] Simulation-package QA can report missing or non-overlapping structure bodies.

### ST-S9. Tests And Manual QA

Status: Done

Tasks:

- [x] Add contract tests for stricter Structure validation.
- [x] Add command tests for selected-detail round-trip and connection point persistence.
- [x] Add drainage-chain fixture tests for:
  - ditch band to inlet
  - inlet to inlet
  - inlet to culvert
  - culvert to outlet
- [x] Add Watertight tests for native structure body output and network dependency inclusion.
- [x] Keep manual QA checklist aligned with v1.0.1 workflow.

Acceptance:

- [x] Focused tests can run without FreeCAD GUI where practical.
- [x] FreeCAD manual smoke confirms tree visibility, preview, route highlight, and solid target discovery.

## 12. Risk Analysis

| Risk | Impact | Mitigation |
|---|---|---|
| UI exposes too many internal source fields | Structures panel becomes confusing. | Keep `Selected Structure Detail` as the only detailed editor and hide internal ids. |
| Connection point role selection stays ambiguous | Pipes connect to wrong ports. | Enforce route-direction role rules and report ambiguous endpoint diagnostics. |
| Native shapes become too detailed too early | Work slows and source contracts churn. | Keep native shapes simple; detailed CAD can use External Ref. |
| External Ref is treated as topology source | Replacing imported solids breaks Drainage. | Persist explicit `StructureConnectionPoint` rows as source endpoints. |
| Watertight fuse masks bad overlap | Simulation package looks valid but leaks. | Add overlap diagnostics and visible fallback status. |
| Build Parametric recreates Structures | Duplicate or misleading objects appear. | Reuse actual Structure preview/output objects and report missing context. |

## 13. Non-goals

This plan does not:

- turn Parametric Road into a full hydraulic analysis package
- auto-size pipes or compute design storm capacity
- model detailed manufacturer parts for every structure
- replace external CAD/IFC structure workflows
- make generated preview geometry editable source

## 14. Immediate Next Steps

Recommended next implementation order:

1. ST-S1 source contract cleanup.

Build Parametric now consumes actual Structure preview contracts. The remaining cleanup should tighten source contracts and remove any obsolete compatibility surfaces that no active command/test depends on.
