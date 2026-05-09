# CorridorRoad V1 Drainage Flow Route Implementation Plan

## Purpose

Define the implementation plan for Drainage Flow Routes as a source-level graph model.

This plan replaces the earlier collection-style drainage grouping idea with an explicit node-and-edge model:

- Drainage Elements are graph nodes.
- Flow Routes are graph edges.
- Final discharge wording is `Outlet`.

The goal is to make drainage intent readable, validateable, and reusable by review, quantities, exchange, and future watertight solid workflows.

## Scope

This plan covers:

- Drainage source model fields.
- Drainage editor UI behavior.
- Flow Route persistence.
- Validation rules.
- Drainage review handoff.
- Build Corridor and Watertight Solid context handoff.

This plan does not implement hydraulic sizing, storm capacity analysis, or automatic route generation.

## Core Rule

Drainage routing must be stored as source intent, not inferred from generated surface geometry.

Each drainage target is defined once as an Element. Each flow connection is defined once as a Flow Route edge. Generated ditches, surfaces, solids, and exchange outputs must trace back to these source rows.

## Source Model Contract

### Element Rows

Element rows define drainage nodes.

Required fields:

- `element_id`
- `kind`
- `start_station`
- `end_station`
- `region_ref`
- `assembly_component_ref`
- `policy_ref`

Supported node families:

- `ditch`
- `culvert_reference`
- `inlet_reference`
- `outfall_reference`
- future structure-backed drainage references

Assembly-generated drainage geometry is limited to ditch components for the current slice. Culverts, inlets, and outfalls remain valid Drainage Elements, but they should be Structure-backed or reference nodes rather than Assembly-generated drainage components.

### Flow Route Rows

Flow Route rows define graph edges between Element nodes.

Target fields:

- `flow_route_id`
- `from_element_ref`
- `to_element_ref`
- `outlet_ref`
- `direction`
- `risk_level`
- `notes`

`from_element_ref` and `to_element_ref` define the real graph edge. `outlet_ref` is optional route-level final discharge context and should reference an outfall Element, Structure outlet, or named external outlet when the row needs explicit final discharge ownership.

### Terminology Migration

Use `Outlet` everywhere in user-facing Drainage workflow.

Implementation cleanup targets:

- `expected_receiver_ref` -> `outlet_ref`
- `FlowRouteReceiverRefs` -> `FlowRouteOutletRefs`
- UI column `Receiver` -> `Outlet`
- documentation term `Receiver` -> `Outlet`

The migration should remove obsolete `Receiver*`, `expected_receiver_ref`, and old `Collection*` variables from active code instead of keeping duplicate compatibility paths.

Existing in-memory rows should be normalized once during the update:

- source dataclass fields should use `outlet_ref`
- FreeCAD object properties should use `FlowRouteOutletRefs`
- editor tables should read and write `Outlet`
- validation and review services should consume only Flow Route and Outlet fields

Old saved documents that contain only removed `Collection*` or `Receiver*` properties are not a required compatibility target for this v1 reset slice. If a temporary reader is needed during the refactor, it must be local to one conversion function and removed before the implementation phase is considered complete.

## UI Plan

### Elements Tab

The Elements tab remains the node authoring surface.

Required behavior:

- Keep `Kind` next to `Region`.
- Use a Region combo per row.
- Use an Assembly combo for ditch components.
- Disable and clear `Structure` for `ditch` rows.
- Enable `Structure` for non-ditch reference rows where a structure-backed drainage node is needed.
- Show Policy as the hydraulic or design policy selector for the Element.

The Element row answers: "What drainage object exists in this region and station range?"

### Flow Routes Tab

The Flow Routes tab becomes the connection authoring surface.

First implementation slice may remain table based, but it must use graph terminology:

| Column | Meaning |
| --- | --- |
| Flow Route ID | Stable edge id |
| From Element | Upstream or source node |
| To Element | Downstream or next node |
| Outlet | Optional final discharge context |
| Direction | Flow direction hint |
| Risk | Review priority or risk level |
| Notes | User notes |

Expected controls:

- `From Element` combo populated from Element rows.
- `To Element` combo populated from Element rows.
- `Outlet` combo populated from outfall/reference Elements and named outlet refs.
- `Add Flow Route`
- `Delete Selected`
- `Validate`
- `Apply`

The UI should also show a read-only route preview when possible:

```text
ditch:right-r2 -> culvert:01 -> outfall:right-01
```

Later, this can become a graph/tree view, but the stored source contract should remain row based and deterministic.

## Validation Plan

### Element Validation

Errors:

- missing `element_id`
- duplicate `element_id`
- missing Region assignment
- `start_station` outside selected Region boundary
- `end_station` outside selected Region boundary
- `end_station` before `start_station`
- missing Policy when the Element participates in routing
- missing Assembly component for `ditch`
- Structure assigned to `ditch`

Warnings:

- non-ditch reference Element without Structure or external reference
- Element exists but is not connected by any Flow Route

### Flow Route Validation

Errors:

- missing `flow_route_id`
- duplicate `flow_route_id`
- missing `from_element_ref`
- missing `to_element_ref`
- `from_element_ref` does not exist
- `to_element_ref` does not exist
- self-loop where `from_element_ref == to_element_ref`
- graph cycle in a route chain
- `outlet_ref` points to a missing Element or unknown outlet reference

Warnings:

- route chain has no final outfall or outlet context
- multiple outlets are reachable from one upstream chain
- disconnected route groups exist
- direction hint conflicts with station order

## Evaluation And Handoff

Applied Sections continue to use active Region drainage refs to generate station-wise ditch geometry.

Flow Routes add network context on top of those geometry rows:

- Drainage Review can show connected chains.
- Quantity output can group ditch lengths by Flow Route.
- Build Corridor can preserve route provenance on drainage surfaces.
- Watertight Solids can keep lined-ditch solid targets tied to Element and Flow Route ownership.
- Exchange output can export drainage nodes and edges instead of only generated geometry.

The Flow Route model should not directly build corridor surfaces. It provides ownership, validation, and downstream routing context.

## Implementation Phases

### Phase 1: Outlet Contract Rename

- Add `outlet_ref` to `DrainageFlowRoute`.
- Rename persisted output property to `FlowRouteOutletRefs`.
- Remove `expected_receiver_ref` from the active dataclass and call sites.
- Remove `FlowRouteReceiverRefs` from active object persistence.
- Remove old `Collection*` route properties from active object persistence.
- Remove route-related compatibility variables once the object update path writes the new contract.
- Update editor headers and status messages from `Receiver` to `Outlet`.
- Add focused round-trip tests for the new Outlet contract.
- Add cleanup tests or source scans that fail if active Drainage code still writes `Receiver*` or `Collection*` route properties.

### Phase 2: Flow Route Link Editing

- Populate `From Element`, `To Element`, and `Outlet` combos from current Element rows.
- Restrict `Outlet` candidates to outfall/reference Elements where possible.
- Add route preview text for selected route chain.
- Keep row order stable and deterministic.

### Phase 3: Graph Validation

- Add missing reference checks.
- Add self-loop checks.
- Add cycle detection.
- Add disconnected chain warnings.
- Add missing outlet warnings.
- Surface validation diagnostics in the editor and Drainage Review.

### Phase 4: Review Handoff

- Add Flow Route chain rows to Drainage Review.
- Show Element ownership, Region, Policy, and outlet context per chain.
- Keep generated ditch geometry review separate from source route review.

### Phase 5: Output And Solid Context

- Preserve Flow Route ids on drainage output rows where applicable.
- Group ditch quantities by Element and Flow Route.
- Preserve Flow Route provenance on lined-ditch Watertight Solid targets.
- Prepare exchange payloads with node and edge records.

First implementation slice:

- Drainage quantity fragments carry `flow_route_ref` when a DrainageModel route owns the active drainage Element.
- Quantity output fragments preserve `flow_route_ref`.
- Lined-ditch Watertight Solid targets preserve `flow_route_ref` from the owning Drainage Element.
- Watertight Solid output rows, persisted output objects, and exchange source-context rows preserve `flow_route_ref`.

## Acceptance Criteria

- No new user-facing Drainage UI uses the term `Receiver`.
- New Drainage objects persist Flow Route outlet data through `FlowRouteOutletRefs`.
- Active Drainage code no longer writes `FlowRouteReceiverRefs`.
- Active Drainage code no longer writes legacy `Collection*` route properties.
- Active Drainage dataclasses no longer expose `expected_receiver_ref`.
- Flow Route validation blocks broken Element references and cycles.
- Flow Route validation warns when a route chain has no final outfall or outlet context.
- Drainage Review can show at least one readable chain preview.
- Applied Sections and Build Corridor behavior remain compatible with existing ditch generation.

## Manual QA

1. Create or load station, assembly, and region sources.
2. Open Drainage.
3. Add ditch Elements for one or more Regions.
4. Add an `outfall_reference` Element.
5. Open Flow Routes.
6. Add a route from the ditch Element to the outfall Element.
7. Set Outlet to the outfall Element.
8. Validate.
9. Apply.
10. Reopen Drainage and confirm the Flow Route persists.
11. Open Drainage Review and confirm the route chain is readable.
12. Build Applied Sections and Build Corridor to confirm ditch geometry still follows Region drainage refs.

## Non-goals

- No automatic drainage network generation in this slice.
- No hydraulic capacity calculation in this slice.
- No pipe sizing or inlet spacing engine in this slice.
- No graph canvas requirement in this slice.
- No direct geometry editing from the Flow Routes tab.
