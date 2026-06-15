# Parametric Road V1 Drainage Flow Route Implementation Plan

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
- `subassembly_ref`
- `policy_ref`

Supported node families:

- `ditch`
- `culvert_reference`
- `inlet_reference`
- `outfall_reference`
- future structure-backed drainage references

Assembly-generated drainage geometry is limited to ditch Subassemblies for the current slice. Culverts, inlets, and outfalls remain valid Drainage Elements, but they should be Structure-backed or reference nodes rather than Assembly-generated drainage Subassemblies.

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

### Ditch-to-Inlet Interpretation

A `ditch -> inlet_reference` Flow Route is an intake/capture edge.

It records that open ditch flow reaches the inlet, but it does not create a separate 3D pipe body.

Physical 3D pipe geometry starts when both route endpoints resolve to Structure-owned pipe connection points, such as:

```text
inlet pipe_out -> culvert upstream
culvert downstream -> outlet pipe_in
```

If the design needs a real short connector pipe from a ditch end into an inlet, represent that connector as its own Structure-backed Element or dedicated connector row in a later slice.

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
- Use an Assembly combo for ditch Subassemblies.
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
- missing Assembly Subassembly for `ditch`
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
- Drainage Review exposes first-slice `pipeline_segment_candidate` rows when Flow Route endpoints resolve to Structure connection points.
- Pipeline candidates are generated from Flow Route direction and Structure-owned connection points resolved from the referenced Drainage Elements; generated preview geometry is not used as source.
- Drainage Review can create a 3D `V1DrainagePipelineCandidatePreview` object for a selected candidate.
- Ready candidates are promoted into `DrainagePipelineResult.segment_rows` as `DrainagePipelineSegment` result records.
- Drainage output exposes dedicated `pipeline_segment_rows` so downstream preview, quantity, solid, and exchange work can consume resolved segments without reading review candidate rows.
- Drainage Review can create a 3D `V1DrainagePipelineSegmentPreview` object for a selected resolved segment.
- Pipeline candidate and segment previews use the active v1 Alignment station/offset frame when available, with a documented station/offset fallback when no Alignment source exists.
- Drainage output exposes dedicated `pipeline_geometry_rows` with centerline polyline points derived from `DrainagePipelineSegment` rows.
- Pipeline segment preview consumes `pipeline_geometry_rows` instead of rebuilding segment geometry inside the UI panel.
- Drainage output exposes dedicated `pipeline_solid_rows` with first-slice capped pipe solid candidate metadata, including length, volume, cap count, coordinate mode, and Flow Route provenance.
- Flow Route review rows expose pipeline solid readiness and cap/length summary when a route resolves to a pipe candidate.
- Drainage output exposes `pipeline_network_rows` that group ready pipe solid candidates into a first-slice pipeline network candidate.
- Pipeline network rows preserve segment refs, Flow Route refs, solid row refs, total length, total candidate volume, junction count, coordinate mode, and validation status.
- Drainage Review includes a `Pipeline Networks` tab so users can distinguish individual pipe segments from the grouped network candidate.
- Drainage Review can create a 3D `V1DrainagePipelineNetworkPreview` object for a selected network row or network-table double-click.
- Drainage output exposes `pipeline_junction_rows` for network endpoint topology, including junction/terminal kind, degree, coordinate point, segment refs, Flow Route refs, and `trim_status=pending`.
- Pipeline junction rows preserve endpoint `connection_point_refs` when they can be traced back to Structure connection points.
- Pipeline junction rows also preserve `structure_refs` resolved from those Structure connection points.
- Drainage Review includes a `Pipeline Junctions` tab so trimming and structure-connection cleanup targets are visible before boolean editing is attempted.
- Watertight Solid target discovery can expose a `drainage_pipeline_network_body` target for the grouped network.
- Network build first tries a best-effort `boolean_fuse` across capped pipe segment solids and falls back to `compound_fallback` when FreeCAD cannot fuse the shapes robustly.
- For degree greater than one junction rows, network build adds a small connector body at the junction point before boolean fuse so pipe segments have overlapping solid volume at the connection.
- For terminal rows with Structure connection point refs, network build adds terminal connector bodies so pipe endpoints have explicit overlap volume for the later Structure-body boolean step.
- Structure body targets can be built directly in Watertight Solids from the native StructureModel spec, producing reusable `structure_body` output shapes.
- Pipeline network builds auto-build available matching `structure_body` targets before reading reusable Structure body output shapes.
- `Build Enabled` orders Structure body targets before Drainage pipeline network targets so dependency shapes exist when both are enabled.
- `pipe_culvert` and circular culvert Structure body dependencies build as cylindrical solids so Drainage network connections can fuse against a pipe-like body.
- Circular culvert Structure body dependencies with `wall_thickness` build as hollow wall solids, preserving a pipe opening instead of a filled cylinder.
- External Ref Structure body dependencies can reuse a referenced FreeCAD object's Shape when `geometry_ref` resolves in the document.
- External Ref Structure body targets for Drainage-ready Structures are blocked until the Structure source has at least one mapped connection point.
- External Ref Structure body validation blocks a build when mapped connection point coordinates sit outside the referenced Shape bounding box tolerance.
- Native `inlet`, `outlet`, and `headwall` Structure body dependencies are placed from their connection point offset and invert/elevation when no explicit Structure placement offset is set, so the pipe endpoint can meet the body without a bridge connector.
- Native `inlet` bodies include an internal chamber cut, and native `outlet`/`headwall` bodies include a pipe opening cut from connection point diameter when available.
- When a Structure body exists but the pipe terminal point is outside that body, network build adds a first-slice port bridge connector from the terminal point toward the Structure body so boolean fuse has overlapping volume.
- Port bridge connectors first use the Structure connection point diameter/width/height and direction when available, then fall back to pipe diameter and Structure body center targeting.
- When a Structure-backed pipe terminal point starts inside a matched Structure body bounding box, network build trims that endpoint to the Structure body exit face before creating pipe and connector solids.
- If matching `structure_body` Watertight Solid output objects already exist for the terminal `structure_refs`, network build includes those Structure body shapes in the same best-effort fuse input.
- Detailed wingwalls, inlet grates, external face/port inference, and terrain boolean interaction remain later steps.

## Acceptance Criteria

- No new user-facing Drainage UI uses the term `Receiver`.
- New Drainage objects persist Flow Route outlet data through `FlowRouteOutletRefs`.
- Active Drainage code no longer writes `FlowRouteReceiverRefs`.
- Active Drainage code no longer writes legacy `Collection*` route properties.
- Active Drainage dataclasses no longer expose `expected_receiver_ref`.
- Flow Route validation blocks broken Element references and cycles.
- Flow Route validation warns when a route chain has no final outfall or outlet context.
- Drainage Review can show at least one readable chain preview.
- Drainage Review can show pipeline candidate status, endpoint connection point refs, station range, invert range, shape, and diameter.
- Selected pipeline candidates can be reviewed as lightweight 3D pipe/line preview output.
- Ready pipeline candidates are promoted to traceable result/output segment rows.
- Selected resolved pipeline segments can be reviewed as lightweight 3D pipe preview output.
- Pipeline preview objects record whether they were built from `alignment_station_offset` or `station_offset_fallback` coordinates.
- Pipeline geometry rows preserve segment id, Flow Route ref, coordinate mode, centerline point list, diameter, and shape kind.
- Pipeline solid rows preserve segment id, Flow Route ref, capped state, candidate volume, and derived length for later quantity and Watertight Solid handoff.
- Watertight Solid target discovery can expose `drainage_pipeline_body` targets for ready pipeline segments.
- Drainage output can expose a grouped pipeline network candidate with route/segment provenance and junction count.
- Drainage output can expose endpoint junction rows so network trimming targets are explicit and traceable.
- Selected pipeline networks can be reviewed as a 3D compound preview while keeping individual segment provenance.
- Watertight Solid target discovery can expose `drainage_pipeline_network_body` for the grouped Drainage pipe network.
- Network solid build records the actual fuse mode: `boolean_fuse`, `single_segment`, or `compound_fallback`.
- `compound_fallback` keeps capped pipe segments traceable when boolean fuse is not robust enough for the current geometry.
- Network solid build records `connector_count` so added junction connector bodies remain visible in output provenance.
- Terminal connector bodies are output build helpers. They do not replace the StructureModel connection point source rows.
- Watertight Solids can build `structure_body` targets from Structure native spec rows without going through road-body Applied Section profile logic.
- Drainage pipeline network build records `dependencies_built` when it auto-builds matching Structure body targets before network fuse.
- Drainage pipeline network build records `port_connector_count` and `port_connector_status` when first-slice port bridge bodies are added for Structure-backed terminals.
- Drainage pipeline network build records `endpoint_trim_count` and `endpoint_trim_status` when Structure-backed pipe terminals are moved from an internal Structure point to the body exit face.
- Watertight Solid pipeline network output preserves terminal `structure_refs` and `connection_point_refs` so the later Structure-body boolean step can target the correct source-owned Structures.
- Watertight Solid pipeline network output records `structure_body_count`, `structure_body_object_refs`, and `structure_fuse_status` when it can include already built Structure body outputs.
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
