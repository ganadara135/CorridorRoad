# Parametric Road V1 Drainage Enhancement Plan

Date: 2026-05-20
Status: Updated enhancement plan, refreshed against current code
Scope: Drainage source authoring, Flow Route graph, Structure handoff, review, Build Parametric, and Watertight Solid readiness

Depends on:

- `docsV1/V1_MASTER_PLAN.md`
- `docsV1/V1_DRAINAGE_MODEL.md`
- `docsV1/V1_DRAINAGE_FLOW_ROUTE_IMPLEMENTATION_PLAN.md`
- `docsV1/V1_STRUCTURE_CONNECTION_NODE_PLAN.md`
- `docsV1/V1_REGION_MODEL.md`
- `docsV1/V1_SECTION_MODEL.md`
- `docsV1/V1_SURFACE_MODEL.md`
- `docsV1/V1_WATERTIGHT_SOLID_TARGET_EXPANSION_PLAN.md`

## 1. Purpose

This document resets the Drainage implementation plan to match the current code.

Drainage is now an active v1 source stage. It owns drainage Elements, Policies, Flow Routes, Region assignment, Structure references, and first-slice pipe-network intent.

The next goal is not a full hydraulic solver. The next goal is to make drainage intent stable enough that:

- open ditch geometry is traceable through Applied Sections and Build Parametric
- Structure-backed pipe networks are previewable and reviewable
- Watertight Solids can consume drainage pipe and lined-ditch targets
- later simulation/export work can trust source ids and endpoint ownership

Latest code checkpoint:

- Drainage authoring is no longer only a surface helper.
- Drainage Elements are graph nodes.
- Flow Routes are graph edges.
- Structure connection points are the physical pipe ports.
- Build Parametric consumes Drainage output as reviewable generated geometry.
- Watertight Solids can discover Drainage-related targets from the generated contracts.

## 2. Core Rule

`DrainageModel` owns drainage intent.

`StructureModel` owns physical drainage connection points such as `pipe_in`, `pipe_out`, inlet intake points, culvert ports, and outlet ports.

Assembly owns reusable ditch geometry.

Applied Sections, Build Parametric surfaces, Drainage Review rows, pipe previews, and Watertight Solid outputs are generated result/output layers. They must not become editable drainage source truth.

## 3. Current Code Baseline

| Area | Current status |
|---|---|
| Drainage source object | `V1DrainageModel` persists element, policy, flow-route, validation, and source refs. |
| Drainage editor | Elements, Policies, and Flow Routes tabs exist. |
| Element Region ownership | Elements choose `Region` in Drainage, not in Regions. |
| Element Assembly ownership | `Assembly` is active for `ditch` rows and disabled for non-ditch rows. |
| Element Structure ownership | `Structure Ref` is active for non-ditch rows and disabled for `ditch` rows. |
| Flow Routes | `From Element`, `To Element`, and `Outlet` graph fields are active. |
| Outlet terminology | User-facing `Receiver` / `Collection` wording has been replaced by `Outlet` / `Flow Route`. |
| Validation | Duplicate ids, missing refs, Region span checks, cross-Region warnings, self loops, cycles, policy refs, Structure refs, and connection point refs are covered in first slice. |
| Presets | Roadside ditch, dual side ditch, culvert crossing, and `Drainage Structures Flow` exist. |
| Structure-backed routing | Flow Routes resolve Structure-owned connection points by route direction. |
| Ditch-to-inlet routing | Treated as capture-only, not as a pipe body. |
| Pipeline result | Candidate, segment, geometry, solid, network, and junction rows exist in Drainage output. |
| 3D preview | `Show Flow Network` creates network preview, segment previews, and Structure pipe connection markers. |
| Tree exposure | Drainage preview/output objects are exposed in the FreeCAD tree so visibility and properties can be inspected. |
| Flow Route focus | Flow Route rows can be selected/focused without editing generated pipe geometry. |
| Build Parametric | Drainage surface consumes Applied Section `ditch_surface` rows with Drainage refs. |
| Build Parametric review | Guided Review exposes `Drainage Surface` and `Drainage Flow` as separate rows. |
| Quantity | First-slice ditch length and flowline length fragments preserve Drainage refs. |
| Watertight Solids | Lined ditch, pipe segment, pipeline network, and Structure body targets can be discovered/built in first slice. |
| Simulation package handoff | Watertight package output can preserve Drainage pipeline and Structure body provenance for later simulation QA. |

## 4. Active Source Contract

### 4.1 DrainageModel

Root fields:

- `drainage_model_id`
- `project_id`
- `label`
- `element_rows`
- `policy_rows`
- `flow_route_rows`
- `source_refs`
- `diagnostic_rows`

### 4.2 DrainageElementRow

Active fields:

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
- `connection_point_ref`
- `notes`

Current rule:

- `ditch` rows may use Assembly component refs.
- non-ditch rows may use Structure refs.
- `connection_point_ref` is an internal/direct mapping option; normal routing should resolve Structure ports by Flow Route direction.
- user-facing Drainage editing should not require users to manually pick `connection_point_ref` for normal inlet/culvert/outlet workflows.

### 4.3 DrainagePolicySet

Active fields:

- `policy_set_id`
- `flow_intent`
- `min_grade_rule`
- `low_point_rule`
- `route_rule`
- `discharge_rule`
- `earthwork_priority`
- `notes`

Current limitation:

Policies are descriptive and validation-oriented. They do not yet size pipes or run hydraulic capacity checks.

### 4.4 DrainageFlowRoute

Active fields:

- `flow_route_id`
- `from_element_ref`
- `to_element_ref`
- `outlet_ref`
- `direction`
- `risk_level`
- `notes`

Graph rule:

- `from_element_ref -> to_element_ref` is the edge.
- `outlet_ref` is final discharge context and should be editable only when `To Element` is an outlet/outfall Element.
- Intermediate route rows should leave `outlet_ref` empty.
- `outlet_ref` is not a third pipe segment endpoint. It is the terminal discharge context for the route chain.

## 5. Current Workflow

Recommended user workflow:

1. Build Project, TIN, Alignment, Stations, Profile, and 3D Centerline.
2. Create Assembly ditch components when open drainage geometry is needed.
3. Create Regions.
4. Create Structures and Structure connection points for inlets, culverts, headwalls, outlets, or external references.
5. Open Drainage.
6. Create Elements.
7. Assign each Element to a Region.
8. Assign `Assembly` only for ditch Elements.
9. Assign `Structure Ref` for Structure-backed Elements.
10. Create Flow Routes.
11. Validate and Apply Drainage.
12. Use `Show Flow Network` to review Structure-backed pipe connections.
13. Run Applied Sections.
14. Build Parametric and review Drainage Surface / Drainage Flow.
15. Use Watertight Solids for lined ditches, pipe segments, pipeline network bodies, and Structure body dependencies.

## 6. Interpretation Rules

### 6.1 Ditch

A `ditch` Element represents open-channel drainage intent tied to Assembly ditch geometry.

It does not own a Structure Ref.

It can participate in Flow Routes as a source node.

### 6.2 Ditch To Inlet

`ditch -> inlet_reference` means capture/intake.

It does not create a separate pipe body.

Physical pipe geometry starts after the inlet, from Structure-owned connection points.

Example:

```text
side-ditch-right-01 -> inlet-01       capture only
inlet-01 -> inlet-02                  pipe
inlet-02 -> culvert-01                pipe
culvert-01 -> outlet-01               pipe
```

### 6.3 Structure-Backed Pipe

When both Flow Route endpoints resolve to Structure-backed Elements, the pipe segment uses Structure connection points:

- source Element resolves to outgoing role, usually `pipe_out`
- target Element resolves to incoming role, usually `pipe_in`
- culvert used as a target resolves to `pipe_in`
- culvert used as a source resolves to `pipe_out`

Generated preview pipes connect port-to-port. They do not follow the road alignment unless a later source model explicitly adds bends/intermediate pipe nodes.

## 7. Implementation Plan

### DR-S1. Source Contract Cleanup

Status: Done

Completed:

- `Receiver` and `Collection` terminology was replaced in active user-facing Drainage workflow.
- `Flow Route` is the graph edge concept.
- `Outlet` is the final discharge context.
- Elements, Policies, and Flow Routes persist through `V1DrainageModel`.

Acceptance:

- [x] No active Drainage UI uses `Receiver`.
- [x] Flow Route outlet data persists through the current outlet contract.
- [x] Old Collection-style workflow is no longer the user model.

### DR-S2. Drainage Editor UX

Status: First slice complete

Completed:

- Elements, Policies, and Flow Routes tabs exist.
- Add buttons are scoped to the active tab.
- `Policy` cells use combos from policy rows.
- `Region` cells use combos from Region rows.
- `Assembly` cells are disabled for non-ditch rows.
- `Structure Ref` cells are disabled for ditch rows and use Structure ID combos where available.
- `Connection Point` is not exposed as a normal Element-column workflow.
- Flow Route rows support double-click preview/focus.
- Flow Route `Outlet` editing is enabled only when `To Element` is an outlet/outfall Element.

Remaining:

- add clearer inline route-chain text for selected Flow Route rows
- improve invalid-cell coloring for missing Region, Policy, Structure, and outlet cases
- add safer row templates for common node families such as inlet, outlet, and cross-drain
- make selected route endpoint resolution visible without opening code-level diagnostics

Acceptance:

- [x] Ditch rows feel different from Structure-backed rows.
- [x] Flow Routes are editable without exposing low-level pipeline result rows.
- [x] Outlet is treated as terminal context, not a required field on every route row.
- [ ] selected route chain is readable without opening Review.

### DR-S3. Preset Alignment

Status: First slice complete

Completed:

- `Drainage Structures Flow` aligns with Structures `Drainage Structures` preset.
- Preset data creates station-banded ditch Elements.
- Preset data creates inlet, culvert, and outlet Elements.
- Flow Route ids use `flowId-*`.
- Ditch-to-inlet rows are capture-only.
- inlet-to-inlet, inlet-to-culvert, and culvert-to-outlet rows become pipe candidates.

Remaining:

- add preset self-check diagnostics when matching Structures preset rows are missing
- add a short preset summary after `Load Preset`
- keep preset station ranges adapted to current Stationing/Alignment extents
- keep Structure and Drainage presets paired so inlet, culvert, outlet, and Flow Route ids do not drift

Acceptance:

- [x] Structures and Drainage presets can be used together without manual id repair.
- [x] Last inlet connects to culvert `pipe_in` through Flow Route resolution.
- [ ] preset loader warns when referenced Structures are not present.

### DR-S4. Validation Upgrade

Status: In progress, route-chain diagnostics expanded

Completed:

- duplicate id checks
- missing Element/Policy/Flow Route ids
- missing Region refs
- Element station range vs Region boundary
- missing or invalid Policy refs
- missing or invalid Structure refs
- Flow Route missing refs
- self-loop checks
- cycle checks
- cross-Region Flow Route warning
- Outlet ref validation
- route-chain warning when no outlet/outfall can be reached
- route-chain warning when one upstream chain can reach multiple outlets
- Structure-backed pipe warning when Flow Route ports cannot be resolved
- non-pipe `ditch -> inlet` capture rows remain non-blocking and do not create false pipe warnings

Next tasks:

- warn when connected Elements use incompatible Policies
- report capture-only vs pipe-producing routes explicitly in validation output
- report when a route expects a pipe but resolves only station-span fallback geometry

Acceptance:

- [x] invalid graph references are visible before Apply.
- [x] cross-Region routes are visible as warnings.
- [x] outlet reachability can be diagnosed from source rows before 3D preview.
- [x] unresolved Structure pipe ports can be diagnosed before 3D preview.
- [ ] policy incompatibility and capture/pipe summaries are complete.

### DR-S5. Structure Connection Handoff

Status: First slice complete, selected route endpoint summary added

Completed:

- Structure-backed Elements resolve pipe endpoints from Structure connection points.
- Direction-aware endpoint selection is implemented.
- Explicit Structure connection points are preserved.
- Derived/default culvert upstream/downstream can snap to current placement.
- `Show Flow Network` refreshes Structures preview before drawing the pipe network.
- Structure pipe-in/pipe-out markers are under Structures ownership.
- Connection point preview markers use clear sphere-style review helpers instead of broken-looking marker fragments.
- Drainage editor Flow Route preview now shows the resolved From Structure/Port and To Structure/Port for the selected route.
- Capture-only Flow Routes are labeled as no-pipe routes in the selected route preview.
- Unresolved pipe routes report missing endpoint status in the selected route preview.

Next tasks:

- add Review filters for unresolved, capture-only, and pipe-producing route rows
- expose the same endpoint summary in Drainage Review route rows where practical

Acceptance:

- [x] Pipe preview uses Structure-owned connection points.
- [x] Ditch capture rows do not create fake pipes.
- [x] Inlet-to-inlet, inlet-to-culvert, and culvert-to-outlet routes use direction-aware ports.
- [x] per-route endpoint resolution is visible before generating preview geometry.

### DR-S6. Drainage Review

Status: First slice complete

Completed:

- Drainage Review exists as a read-only review stage.
- Review can show Drainage Elements, Region assignment, Applied Section context, pipeline candidates, segments, networks, and junctions.
- Drainage Review can summarize quantities when a QuantityModel is supplied.
- Build Parametric can create Drainage diagnostic/focus markers for missing ditch-surface coverage.

Next tasks:

- expand 3D issue markers beyond missing coverage into unresolved port, broken route, and outlet-chain issues
- add direct navigation buttons back to Drainage, Regions, Assembly, Structures, and Cross Section Viewer
- add flowline continuity review after explicit flowline/invert roles are expanded

Acceptance:

- [x] Review shows source and result context separately.
- [x] Pipeline network and junction rows are visible.
- [x] missing coverage rows can be focused in 3D.
- [ ] unresolved Structure port rows can be focused in 3D.

### DR-S7. Applied Sections And Build Parametric

Status: First slice complete, side/component mismatch diagnostics expanded

Completed:

- Applied Sections resolve Drainage Elements from `DrainageModel.region_ref`.
- Ditch component result rows preserve matching Drainage refs by side.
- `ditch_surface` points preserve Drainage, component, and side context.
- Build Parametric creates a separate Drainage Surface preview from Applied Section ditch rows.
- Build Parametric Guided Review includes Drainage Surface and Drainage Flow.
- Drainage Flow focus uses Flow Route and Structure connection context.
- Build Parametric exposes generated Drainage preview objects in the tree instead of keeping them only as hidden helper geometry.
- Build Parametric Drainage Review compares active Drainage ditch rows against generated `ditch_surface` sides.
- Build Parametric Drainage Review reports missing source drainage refs on generated `ditch_surface` rows.
- Build Parametric Drainage Review reports Assembly component mismatches when the expected Drainage `assembly_component_ref` is not present on generated ditch points.

Next tasks:

- expose Drainage context more directly in Cross Section Viewer labels/tables
- add explicit flowline/invert point roles beyond current ditch shape roles

Acceptance:

- [x] Drainage surface follows source-tagged Applied Section ditch rows.
- [x] Build Parametric does not infer Drainage ownership from preview mesh geometry.
- [x] Drainage Flow focus distinguishes resolved pipe segments from fallback station-span focus.
- [x] side/component mismatch diagnostics are available in Build Parametric Drainage Review rows.
- [ ] Cross Section Viewer Drainage labels and explicit flowline/invert roles are complete.

### DR-S8. Quantities And Reports

Status: First slice complete

Completed:

- drainage ditch length quantities by Drainage element id
- flowline length quantities when paired flowline/invert-style point ids are available
- `QuantityFragment` and rows preserve Drainage refs
- Drainage Review can include quantity summary rows

Next tasks:

- persist and auto-load latest QuantityModel into Drainage Review where practical
- group quantities by Flow Route where ownership is unambiguous
- add report-ready rows for inlet count, culvert count, outlet count, and pipe length by policy

Acceptance:

- [x] ditch length can be reported by Drainage element.
- [ ] pipe length and structure count reports are source-traceable from Drainage + Structure.

### DR-S9. Watertight Solid Handoff

Status: First slice complete

Completed:

- lined ditch targets can be owned by Drainage Elements.
- pipe segment body targets can be discovered.
- pipeline network body targets can be discovered.
- Structure body dependencies can auto-build before pipeline network targets.
- network build records fuse mode, connector count, port connector count, endpoint trim count, Structure body refs, connection point refs, and port contact status.
- generated Watertight Solid output objects are exposed in the tree with source refs and route refs where available.

Next tasks:

- add Drainage-specific QA summary in Watertight Solids for:
  - capture-only routes
  - pipe-producing routes
  - unresolved Structure ports
  - network fuse fallback
- add package-level simulation readiness labels for drainage components
- add clearer user-facing distinction between lined ditch solids, pipe solids, and Structure body solids

Acceptance:

- [x] Watertight Solid output can trace pipeline network bodies back to Flow Routes, Structures, and connection points.
- [ ] simulation package QA can summarize complete Drainage readiness in one place.

### DR-S10. Future Hydraulic Layer

Status: Deferred

Future scope:

- pipe sizing
- inlet spacing
- storm event assumptions
- capacity checks
- HGL/EGL analysis
- ponding and spread calculations
- external hydraulic software exchange

Non-goal for current implementation:

- Do not block source authoring, review, or solid generation on hydraulic solver availability.

## 8. Priority Order

Recommended next implementation order:

1. DR-S4 validation upgrade for route-chain outlet reachability, multi-outlet ambiguity, and unresolved Structure ports.
2. DR-S5 selected Flow Route endpoint summary showing From Structure/Port and To Structure/Port.
3. DR-S7 side/component mismatch diagnostics in Applied Sections and Build Parametric.
4. DR-S6 3D issue markers for unresolved Structure ports, broken routes, and outlet-chain problems.
5. DR-S8 report rows for pipe length, inlet count, culvert count, outlet count, and policy grouping.
6. DR-S9 simulation-readiness summary in Watertight Solids and exported packages.

This order improves correctness and review clarity before adding new hydraulic behavior.

## 9. Manual QA

Minimum current QA:

1. Create or load Alignment, Stations, Profile, and 3D Centerline.
2. Create Assembly with right-side ditch.
3. Create Regions.
4. Load Structures `Drainage Structures` preset and Apply.
5. Open Drainage.
6. Load Drainage `Drainage Structures Flow` preset.
7. Confirm ditch rows have Region, Assembly, Policy, and no Structure Ref.
8. Confirm inlet/culvert/outlet rows have Structure Ref and no Assembly.
9. Validate.
10. Apply.
11. Click `Show Flow Network`.
12. Confirm ditch-to-inlet rows are capture-only and do not draw fake pipes.
13. Confirm inlet-to-inlet, inlet-to-culvert, and culvert-to-outlet pipes connect Structure ports.
14. Run Applied Sections.
15. Build Parametric.
16. Confirm Drainage Surface and Drainage Flow guided review rows are available.
17. Open Drainage Review and inspect pipeline candidates, segments, networks, and junctions.
18. Open Watertight Solids and confirm lined ditch / pipeline network / Structure body targets are discoverable.

## 10. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Drainage Element and Flow Route concepts feel duplicated | Users may not know where to edit a pipe path. | Keep Elements as nodes and Flow Routes as edges; add selected-route summary. |
| Ditch capture rows are mistaken for pipe rows | Users may expect ditch-to-inlet pipes in 3D. | Label capture-only rows clearly in validation and Review. |
| Structure port resolution is hidden | Pipe preview may look wrong without obvious source reason. | Show From/To Structure port summary per route. |
| Region / station mismatches remain subtle | Ditch geometry may not appear downstream. | Strengthen side/component and Region span diagnostics. |
| Watertight Solid network fuse falls back silently | Simulation geometry may appear valid but remain a compound. | Surface fuse mode and readiness summary in panel and package QA. |
| Hydraulic expectations grow too early | Scope creep can destabilize source contracts. | Keep hydraulic solver deferred and keep current work focused on traceable source/result/output contracts. |

## 11. Non-goals

This plan does not:

- implement full hydraulic analysis
- auto-size pipes
- auto-place inlets
- replace Structure connection point ownership
- infer drainage source truth from generated meshes
- make Flow Network preview geometry directly editable
