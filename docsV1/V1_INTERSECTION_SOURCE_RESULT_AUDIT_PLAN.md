# V1 Intersection Source/Result Audit Plan

Date: 2026-06-21
Status: In progress

Related process redesign:

- [V1_INTERSECTION_CREATION_PROCESS_REDESIGN_PLAN.md](./V1_INTERSECTION_CREATION_PROCESS_REDESIGN_PLAN.md)

Depends on:

- [V1_MASTER_PLAN.md](./V1_MASTER_PLAN.md)
- [V1_INTERSECTION_MODEL.md](./V1_INTERSECTION_MODEL.md)
- [V1_INTERSECTION_ENHANCEMENT_PLAN.md](./V1_INTERSECTION_ENHANCEMENT_PLAN.md)
- [V1_REGION_MODEL.md](./V1_REGION_MODEL.md)
- [V1_APPLIED_SECTION_SUPPLEMENTAL_SAMPLING_REDESIGN_PLAN.md](./V1_APPLIED_SECTION_SUPPLEMENTAL_SAMPLING_REDESIGN_PLAN.md)
- [V1_GENERAL_ROAD_PARAMETRIC_DESIGN_AUDIT_PLAN.md](./V1_GENERAL_ROAD_PARAMETRIC_DESIGN_AUDIT_PLAN.md)

## 1. Purpose

This document defines the source/result audit and improvement plan for v1 intersection design.

The goal is not to improve final solid geometry at this stage.

The goal is to make intersection design parametric enough that downstream geometry can be generated from durable source data and accepted result contracts.

## 2. Scope

Included:

- intersection source ownership
- control area source data
- participating road, Region, Alignment, Profile, Superelevation, Assembly, and Subassembly references
- curb return source data
- lane connection and edge mapping source data
- intersection grading policy source data
- drainage tie-in and low-point intent
- Applied Section supplemental rows generated for intersection control areas
- intersection result contracts consumed by Build Corridor and review surfaces
- diagnostics that explain missing or ambiguous source intent

Excluded for now:

- deep watertight solid geometry QA
- final boolean/fuse robustness
- detailed non-manifold or self-intersection repair
- automatic interchange synthesis without explicit source rules
- direct editing of generated surface or preview geometry

## 3. Core Rule

Intersection geometry must be generated from source intent and evaluated result contracts.

Generated preview wires, surfaces, patches, and solids are outputs.

They must not become the source of intersection design meaning.

## 4. Source/Result Boundary

Source owns:

- intersection id and type
- participating Alignment refs
- participating Region refs
- leg ids and approach/departure roles
- control area boundary intent
- curb return definitions
- lane connection rules
- edge-of-pavement, shoulder, sidewalk, ditch, and side-slope tie-in policies
- grading policy
- drainage low-point and flow-route context
- structure interaction refs where applicable

Evaluation owns:

- resolving station/offset/elevation frames on each participating Alignment
- detecting control boundary stations
- resolving curb return contact stations
- generating supplemental Applied Section station rows
- assigning source refs and diagnostic refs
- resolving precedence where Region, Intersection, Drainage, and Structure policies overlap

Result owns:

- intersection Applied Section rows
- junction surface patch contracts
- curb return result rows
- lane/edge connection result rows
- drainage tie-in result rows
- diagnostics and traceability rows

Output owns:

- review graphics
- surface meshes
- exported geometry
- optional future watertight solid targets

## 5. Status Dashboard

| Step | Status | Owner boundary | Output |
| --- | --- | --- | --- |
| 1. Baseline inventory | Done | source/result/output | list current objects, commands, services, and tests |
| 2. Source contract audit | Done | source | identify missing durable source fields |
| 3. Evaluation contract audit | Done | evaluation | identify hidden geometry decisions and implicit sampling |
| 4. Result contract audit | Done | result | define required result rows and diagnostics |
| 5. Consumer audit | Done | result/output | check Applied Sections, Build Corridor, Drainage, Watertight handoff consumers |
| 6. UX and review audit | Done | presentation | define user-visible status, source refs, and edit handoff |
| 7. Preset/sample data audit | Done | source | ensure starter T/Cross/Y data is sufficient and parametric |
| 8. Implementation backlog | Done | mixed | convert findings into ordered implementation tasks |
| 9. Validation plan | Done | contracts/QA | define focused tests and manual QA checklist |

Status meanings:

- `Pending`: not started.
- `In progress`: actively being analyzed or implemented.
- `Blocked`: waiting on another subsystem or decision.
- `Done`: accepted for this audit stage.

## 6. Step 1 - Baseline Inventory

Status: Done

Goal:

- identify current intersection source, result, output, command, service, preset, and test surfaces.

Tasks:

- inventory `IntersectionModel` source fields.
- inventory intersection command/task panel behavior.
- inventory intersection result/service builders.
- inventory Applied Sections intersection consumption.
- inventory Build Corridor intersection consumption.
- inventory drainage and structure references into or from intersections.
- inventory current tests and manual QA docs.

Acceptance:

- the audit has a named list of existing source/result/output artifacts.
- each artifact is classified as source, evaluation, result, output, or presentation.

### Step 1 Inventory Result

| Artifact | Boundary | Current role | Notes |
| --- | --- | --- | --- |
| `models/source/intersection_model.py` | source | Owns `IntersectionModel`, leg rows, control areas, arm policies, edge policies, curb-return policies, grading policies, drainage policies, and intersection rows. | Directionally correct source container, but anchor/corner/lane-connection intent is still not explicit enough for a full creation workflow. |
| `objects/obj_intersection.py` and object registration paths | source persistence | Persist and restore IntersectionModel data in the FreeCAD document. | Useful source persistence layer; should remain the durable state boundary. |
| `commands/cmd_intersection_editor.py` | presentation/source authoring | Existing Intersections panel and source editor. | Current flow can build or edit a model, but too many fields are defaulted or inferred in one interaction. |
| `commands/cmd_intersection_presets.py` | source starter/presentation | Creates starter sources or links existing Alignments, creates IntersectionModel, and can preview edge networks. | Helpful onboarding path, but starter creation is still compressed and should become staged source authoring. |
| `services/evaluation/intersection_evaluation_service.py` | evaluation | Evaluates topology, edge network, surface zones, corridor clipping, grading context, drainage hints, and slope-face loops. | This is the main result-contract path and should be preserved. |
| `models/result/intersection_topology.py` | result | Stores leg span and control-area topology results. | Good contract basis for later staged previews. |
| `models/result/intersection_edge_network.py` | result | Stores leg, daylight, curb-return, and related edge rows. | Good contract basis; needs stronger source-stage traceability for edge-family policy. |
| `models/result/intersection_surface_zone.py` | result | Stores surface-zone responsibility rows. | Good contract basis; should eventually separate accepted source-driven zones from inferred fallback zones. |
| `models/result/intersection_corridor_clipping.py` | result | Stores ordinary corridor clipping responsibility around intersection control areas. | Correct result boundary, but consumers must not treat it as source intent. |
| `models/result/intersection_grading_context.py` | result | Stores grading context rows. | Useful, but source vertical/grading intent should be authored earlier. |
| `models/result/intersection_drainage_hint.py` | result | Stores drainage hint rows from evaluated surface zones. | Useful review output; not a substitute for drainage source intent. |
| `models/result/intersection_slope_face_loop.py` | result | Stores source-traceable Slope Face loop candidates and diagnostics. | Current stabilization path is aligned with edge-network-first direction. |
| `models/result/intersection_boundary_segment.py`, `intersection_patch_boundary.py`, `intersection_slope_face_boundary.py`, `intersection_tie_in_edge.py`, `intersection_trim_boundary.py` | result/mixed legacy support | Support older patch, boundary, tie-in, and trim workflows. | Must be classified carefully so boundary/trim outputs are not treated as missing source intent. |
| `services/builders/applied_section_service.py` | evaluation/result builder | Adds intersection context to Applied Sections and supplemental rows. | Correct consumer of intersection source/result context; must keep diagnostics visible when falling back. |
| `commands/cmd_generate_applied_sections.py` | presentation/result command | Builds AppliedSectionSet with intersection context. | Should remain a result generation command, not source editor. |
| `commands/cmd_build_corridor.py` | output/presentation consumer | Creates Intersection Surface, Intersection Slope Face Surface, review rows, highlights, and diagnostics. | This is the highest-risk area for late repair logic; it should consume accepted contracts and report missing source. |
| `services/builders/corridor_surface_geometry_service.py` | output builder | Builds ordinary corridor and slope-face surface geometry with intersection context. | Output-only; should not infer intersection source meaning from generated TINs. |
| `ui/viewers/cross_section_viewer.py` and `commands/cmd_view_sections.py` | presentation | Shows active intersection control area, edge, zone, grading, drainage, and clip context. | Correct review surface; should expose source refs and fallback status clearly. |
| `commands/cmd_watertight_solids.py` | output handoff | Discovers intersection-related solid targets and trim closure previews. | Keep shallow for now; final solid robustness remains out of scope. |
| `docsV1/V1_INTERSECTION_MANUAL_QA.md` | validation/QA | Manual QA procedure for T, Cross, Y, and slope-face loop review. | Real-document visual QA remains manual. |

### Late Repair Or Preview Paths To Watch

These paths can remain as review/output helpers, but they must not become source intent:

- intersection patch surface generation in `cmd_build_corridor.py`
- curb-return arc sampling properties on generated preview objects
- patch boundary and refined intersection surface preview objects
- intersection trim closure preview/output helpers in `cmd_watertight_solids.py`
- ordinary Slope Face suppression based on generated intersection surface footprints
- nearest-edge or TIN-derived boundary selection used only for output construction
- manual hide/show review objects used to inspect contracts

### Step 1 Conclusion

The current implementation already has useful source and result contracts.

The weak point is not the absence of all contracts.

The weak point is that the creation process still compresses too many source decisions into default generation, then relies on Build Corridor and preview/output logic to reveal or repair missing intent.

## 7. Step 2 - Source Contract Audit

Status: Done

Goal:

- determine whether current source data is enough to regenerate intersection geometry without reading generated output geometry as source intent.

Questions:

- Are control area boundaries represented as durable source intent?
- Are curb return definitions explicit enough to regenerate contact points and station ranges?
- Are lane connection rules explicit?
- Are edge roles clear for lane, shoulder, curb, sidewalk, ditch, side slope, and median?
- Are grading rules explicit enough for crown, sag, low point, and tie-in decisions?
- Are drainage low-point and flow-route references source-owned?
- Are Region refs explicit and stable?

Acceptance:

- missing source fields are listed.
- fields that already exist are marked as sufficient or insufficient.
- no output geometry is accepted as a substitute for missing source intent.

### Step 2 Source Field Checklist

Classification:

- `Required`: must exist as durable source or user-approved source before result generation.
- `Optional`: useful when available, but not required for the first source-complete workflow.
- `Derived`: may be detected or calculated, but must be stored with source status and review visibility if it affects design.
- `Future`: important later, but not required for the current redesign slice.

| Source field or row | T | Cross | Y | Current status | Classification | Gap / action |
| --- | --- | --- | --- | --- | --- | --- |
| Intersection id and kind | yes | yes | yes | `IntersectionRow.intersection_id` and `intersection_kind` exist. | Required | Sufficient. |
| Source mode | yes | yes | yes | `IntersectionRow.source_mode` exists. | Required | Sufficient, but UI should show whether rows came from starter defaults or user approval. |
| Primary and secondary Alignment refs | yes | yes | yes | `primary_alignment_ref` and `secondary_alignment_refs` exist. | Required | Sufficient for first slice. |
| Profile refs per leg | yes | yes | yes | `IntersectionLegRow.profile_ref` exists but is often default/empty. | Required | Needs source-completeness validation. |
| 3D Centerline refs per leg | yes | yes | yes | `IntersectionLegRow.centerline3d_ref` exists but may be empty. | Required | Needs validation and fallback diagnostics before Applied Sections. |
| Intersection anchor point | yes | yes | yes | `intersection_point_x/y/z`, `primary_station`, and `secondary_station_refs` exist on `IntersectionRow`. | Derived | Missing anchor method/status/tolerance fields; add or promote an `IntersectionAnchorRow`. |
| Anchor lock/manual/detected state | yes | yes | yes | Not explicit. | Required | Add source status so detected points are not silently accepted as design truth. |
| Leg ids and roles | yes | yes | yes | `IntersectionLegRow.leg_id` and `leg_role` exist. | Required | Sufficient structurally; UI must make role approval explicit. |
| Approach/departure station spans | yes | yes | yes | `approach_station_start/end` exist. | Required | Needs validation against stationing and control area intent. |
| Leg priority / mainline priority | yes | yes | yes | `IntersectionLegRow.priority` exists. | Required | Sufficient for first slice. |
| Region refs per leg | yes | yes | yes | `IntersectionLegRow.region_ref` and `control_region_refs` exist. | Required | Needs validation that Region refs match control-area intent. |
| Control area source intent | yes | yes | yes | `IntersectionControlArea.station_ranges`, `influence_ranges`, and `control_region_refs` exist. | Required | Insufficient: current control area is mostly Region-driven; add `control_area_intent` fields or row. |
| Control area boundary method | yes | yes | yes | Not explicit. | Required | Add source method such as station range, offset envelope, curb-return envelope, or manual polygon. |
| Corner identity | yes | yes | yes | Not explicit. | Required | Add `IntersectionCornerRow` or equivalent mapping from from-leg/to-leg/side. |
| Curb return policy | yes | yes | partial | `IntersectionCurbReturnPolicyRow` exists. | Required | Insufficient for full workflow: add corner id, from/to leg refs, tangent/contact policy, and source approval status. |
| Curb return design vehicle rule | optional | optional | optional | `IntersectionArmPolicyRow.design_vehicle_ref` exists; curb row has radius only. | Optional | Link curb radius to design vehicle rule when present. |
| Arm policy | yes | yes | yes | `IntersectionArmPolicyRow` exists. | Required | Mostly sufficient; should be reviewed per leg before edge network preview. |
| Lane connection policy | yes | yes | yes | Not explicit. | Required | Add `IntersectionLaneConnectionPolicyRow`; do not infer lane continuity only from edge geometry. |
| Edge family policy | yes | yes | yes | `IntersectionEdgePolicyRow` exists with `edge_role`, side, offset, elevation rule. | Required | Insufficient: edge families for lane, shoulder, gutter, curb, sidewalk, ditch, median, side_slope should be generated from Assembly/Subassembly contracts and user-approved. |
| Assembly/Subassembly refs per leg | yes | yes | yes | Indirect via Region/Applied Sections. | Required | Add visible source refs or validation linking each leg/control area to Assembly/Subassembly context. |
| Vertical / grading policy | yes | yes | yes | `IntersectionGradingPolicyRow` exists. | Required | Insufficient: needs controlling profile, crown handling, tie-in rule, low-point strategy, and crossfall transition intent. |
| Superelevation interaction | optional | optional | optional | External source context exists. | Optional | Add validation to state whether ordinary Superelevation is overridden, blended, or preserved. |
| Drainage source intent | yes | yes | yes | `IntersectionDrainagePolicyRow` exists. | Required | Insufficient: low-point refs, gutter edge refs, inlet candidate policy, and flow-route handoff should be source-visible. |
| Structure interaction refs | optional | optional | optional | Not explicit in IntersectionModel. | Optional | Keep optional for now; Structures may reference Regions/intersection context later. |
| Preset source completeness status | yes | yes | yes | Not explicit. | Required | Add per-stage completeness status so starter presets are educational source examples, not opaque seed geometry. |

### Step 2 Findings

Sufficient source areas:

- intersection identity and kind
- participating Alignment refs
- basic leg rows and leg roles
- basic control-area rows
- basic arm, edge, curb-return, grading, and drainage policy row containers

Insufficient source areas:

- anchor method and approval status
- corner identity and from-leg/to-leg mapping
- lane connection policy
- edge-family policy derived from Assembly/Subassembly contracts
- control-area intent independent from Region rows
- vertical/grading source detail
- drainage source detail
- source-completeness status for presets and existing-alignment workflows

Source fields that may be auto-detected but must be user-approved:

- intersection anchor point and station refs
- control area station ranges
- leg approach/departure spans
- curb-return tangent/contact stations
- edge families inferred from Assembly/Subassembly rows
- low-point and inlet candidate hints

### Step 2 Conclusion

The current source model is a good first container, but the creation workflow is not yet source-complete.

The next design stage should add or promote explicit source-stage rows for anchor, corners, lane connections, edge families, vertical/grading, and drainage intent before adding more output geometry repair.

## 8. Step 3 - Evaluation Contract Audit

Status: Done

Goal:

- identify where hidden runtime geometry decisions are made during intersection evaluation.

Questions:

- Where are supplemental intersection stations generated?
- Are station rows derived from Centerline3DResult or from profile/alignment fallback geometry?
- Are control boundary frames generated consistently for all participating Alignments?
- Are curb return contact stations carried as result rows?
- Are diagnostics emitted when sampling is missing, sparse, or ambiguous?

Acceptance:

- implicit evaluation decisions are listed.
- required diagnostics are identified.
- fallback behavior is visible to the user.

### Step 3 Current Evaluation Chain

| Evaluation path | Current role | Source dependency | Audit status |
| --- | --- | --- | --- |
| `IntersectionEvaluationService.evaluate_topology()` | Resolves active intersection row, leg spans, and control-area rows. | Intersection rows, leg rows, control-area rows. | Good first result stage, but should report missing anchor and unapproved leg/control-area source status. |
| `evaluate_edge_network()` | Produces leg, daylight, curb-return, and related edge rows. | Topology, edge policies, curb-return policies, arm policies. | Good second result stage, but currently may create generic edges from default policies. |
| `evaluate_surface_zones()` | Produces central, main, side, curb-return, and slope-face responsibility zones. | Edge network, grading policy refs, control areas. | Good result contract; should distinguish accepted source-driven zones from inferred/default zones. |
| `evaluate_corridor_clipping()` | Produces corridor clip responsibility around control areas. | Topology and surface-zone rows. | Correct result boundary; should not define control-area source. |
| `evaluate_grading_context()` | Resolves grading/crossfall context from surface zones and grading policy. | Surface zones and grading policy rows. | Useful but too late if vertical/grading source detail is missing. |
| `evaluate_drainage_hints()` | Produces low-point or outlet handoff hints from surface zones. | Surface zones, drainage policy, grading context. | Useful as review hints; not a replacement for drainage source intent. |
| `evaluate_slope_face_loops()` | Produces loop-owned intersection Slope Face responsibilities. | Surface zones and edge network. | Aligned with source/result direction; keep separate from mesh repair. |
| Applied Sections intersection evaluation | Adds active control area and intersection supplemental context. | IntersectionModel plus Alignment/Profile/Centerline3D/Region context. | Needs explicit diagnostics when station frames use fallback or sparse source. |
| Build Corridor intersection review evaluation | Re-evaluates topology, edge network, zones, clips, drainage hints, and slope loops for review. | IntersectionModel and result contracts. | Useful review path, but should not be the first place missing source intent becomes visible. |

### Hidden Or Implicit Evaluation Decisions

| Decision | Current risk | Required diagnostic or redesign action |
| --- | --- | --- |
| Anchor detection from sampled Alignment paths | A detected XY intersection can look like accepted source. | Report `anchor_status=detected_unapproved` until user locks or accepts it. |
| Primary/secondary station refs | Stations can be derived from detection but not reviewed as source. | Store source status and tolerance; show station refs in the wizard. |
| Control area ranges from Region rows or preset control length | Region spans can become the de facto junction footprint. | Report whether control area is `intersection_owned`, `region_derived`, or `preset_default`. |
| Leg approach/departure spans | Spans may be derived from control length or Region defaults. | Report `leg_span_source` per leg. |
| Generic edge rows from default policy refs | Edge network can appear complete while edge families were not user-approved. | Report `edge_policy_source=default/preset/user`. |
| Curb-return contact stations | Contact/tangent station refs are evaluated but not yet source-owned enough. | Add diagnostics when contact station refs are inferred from radius only. |
| Surface-zone role assignment | Zones can be created from default edge families. | Report whether each zone has accepted source edge refs. |
| Grading context | `flatten_intersection` or normal superelevation may be applied without enough visible vertical intent. | Report missing controlling profile, crown strategy, tie-in strategy, and low-point strategy. |
| Drainage hints | Low-point/outlet suggestions can be mistaken for drainage design. | Keep hints as warnings until drainage source refs are authored. |
| Slope Face loop ownership | Good path, but loop readiness can hide missing edge-family source. | Loop diagnostics must include missing source edge family and open/self-crossing status. |
| Build Corridor fallback / patch paths | Output builder can still create review geometry from patch/preview logic. | Label legacy patch output and block it from becoming accepted source. |

### Required Evaluation Diagnostics

- `anchor_missing`
- `anchor_detected_unapproved`
- `centerline3d_ref_missing_for_leg`
- `profile_ref_missing_for_leg`
- `control_area_region_derived`
- `control_area_intent_missing`
- `leg_span_defaulted`
- `corner_rows_missing`
- `lane_connection_policy_missing`
- `edge_family_policy_defaulted`
- `curb_return_contact_inferred`
- `grading_vertical_policy_incomplete`
- `drainage_intent_incomplete`
- `surface_zone_source_edges_inferred`
- `build_corridor_legacy_patch_output`
- `intersection_result_fallback_used`

### Step 3 Conclusion

The evaluation layer is already structured in the right order.

The next issue is not the absence of evaluation services.

The issue is that several evaluation stages can proceed from default, derived, or inferred source values without a strong source-completeness gate.

The redesigned workflow should make those states visible before topology, edge network, surface zone, Applied Sections, or Build Corridor output is trusted.

## 9. Step 4 - Result Contract Audit

Status: Done

Goal:

- define the normalized intersection result contracts needed by downstream builders.

Required result families:

- intersection applied-section rows
- control boundary rows
- curb return rows
- lane connection rows
- edge tie-in rows
- junction grading rows
- drainage tie-in rows
- source lineage rows
- diagnostics

Acceptance:

- result rows can be consumed without re-reading generated preview geometry.
- each result row has source refs and diagnostic refs where relevant.

### Step 4 Existing Result Contracts

| Result contract | Current rows | Strong points | Gap |
| --- | --- | --- | --- |
| `IntersectionTopologyResult` | `IntersectionTopologyLegSpanRow`, `IntersectionTopologyControlAreaRow` | Captures leg spans, control areas, policy refs, statuses, diagnostics. | Needs row-level source state such as `source_status`, `anchor_ref`, and `control_area_intent_ref`. |
| `IntersectionEdgeNetworkResult` | `IntersectionEdgeNetworkRow` | Captures edge role, family, policy ref, leg/control refs, stations, contact refs, xyz endpoints. | Needs source approval state and edge-family source refs from Assembly/Subassembly-derived policy. |
| `IntersectionSurfaceZoneResult` | `IntersectionSurfaceZoneRow` | Captures zone role/family, edge refs, leg refs, alignment refs, control area refs, vertical policy, triangulation method, diagnostics. | Needs explicit lineage fields distinguishing accepted source edges from inferred/default edges. |
| `IntersectionCorridorClipResult` | `IntersectionCorridorClipRow` | Captures clip responsibility around control areas. | Must remain result-only; add diagnostics when control area source intent is derived from Region only. |
| `IntersectionGradingContextResult` | `IntersectionGradingContextRow` | Captures crossfall/grading context per zone. | Needs stronger source refs to vertical/grading source stage. |
| `IntersectionDrainageHintResult` | `IntersectionDrainageHintRow` | Captures drainage review hints and warning diagnostics. | Must remain hint-only unless drainage source refs exist. |
| `IntersectionSlopeFaceLoopResult` | `IntersectionSlopeFaceLoopRow` | Captures loop-owned Slope Face result, consumed Surface Zone refs, consumed Edge Network refs, source status, edge-network source status, and diagnostics. | Continue expanding downstream consumers so Build Corridor and output handoff surfaces display the same loop source lineage. |
| Patch/boundary/trim result contracts | patch boundary, boundary segment, slope face boundary, tie-in edge, trim boundary | Useful transition and output helpers. | Must be labeled legacy/transition/result-only where they depend on generated preview geometry. |

Core evaluated result rows now carry a `source_status` and `source_diagnostic_rows` contract. Output helper rows remain result/output contracts; they must report output path and diagnostics, but they must not become source-intent owners.

### Required Normalized Result Families

| Required result family | Purpose | Required lineage fields |
| --- | --- | --- |
| `intersection_anchor_result` | Accepted anchor station/point evaluation. | `anchor_ref`, `anchor_source_status`, `primary_station_ref`, `secondary_station_refs`, `diagnostic_refs`. |
| `intersection_topology_result` | Leg and control-area topology. | `intersection_ref`, `leg_refs`, `control_area_intent_ref`, `control_region_refs`, `source_status`. |
| `intersection_edge_network_result` | Edge rows before surfaces. | `edge_policy_ref`, `edge_family_policy_ref`, `assembly_ref`, `subassembly_refs`, `corner_ref`, `curb_return_policy_ref`, `source_status`. |
| `intersection_surface_zone_result` | Surface-zone responsibility before triangulation. | `source_edge_refs`, `accepted_edge_refs`, `inferred_edge_refs`, `vertical_policy_ref`, `control_area_intent_ref`. |
| `intersection_grading_context_result` | Vertical/crossfall/tie-in context. | `vertical_tie_policy_ref`, `profile_refs`, `superelevation_refs`, `grading_policy_ref`, `source_status`. |
| `intersection_drainage_context_result` | Drainage intent and hints. | `drainage_intent_ref`, `gutter_edge_refs`, `low_point_refs`, `flow_route_refs`, `hint_status`. |
| `intersection_applied_section_context` | Applied Section station context for each participating Alignment. | `alignment_ref`, `centerline3d_ref`, `station_kind`, `control_area_ref`, `source_trigger_ref`, `fallback_status`. |
| `intersection_output_review_result` | Output/review handoff rows. | `consumed_result_refs`, `legacy_patch_status`, `fallback_diagnostics`, `review_object_refs`. |

### Required Row Status Values

- `accepted_source`
- `derived_unapproved`
- `preset_default`
- `inferred_fallback`
- `legacy_output`
- `blocked_missing_source`
- `ready`
- `warning`
- `error`

### Result Contract Rules

- Result rows may contain evaluated geometry coordinates, but must also carry the source refs that produced them.
- Preview objects and generated TINs must not be read back to fill missing source refs.
- If an output builder uses inferred or legacy result rows, the row must report that status.
- Applied Sections and Build Corridor should consume result rows directly, not rediscover intersection meaning from mesh fragments.
- Drainage hints remain hints until a drainage source intent row accepts or references them.
- Watertight Solid handoff may list planned targets, but deep solid quality remains out of scope.

### Step 4 Conclusion

The existing result contracts are directionally correct.

The main improvement is row-level source lineage and status.

The next consumer audit should verify that Applied Sections, Build Corridor, review, drainage, and watertight handoff consume these contracts instead of generated geometry.

## 10. Step 5 - Consumer Audit

Status: Done

Goal:

- verify that consumers use accepted result contracts instead of inferred output geometry.

Consumers:

- Applied Sections
- Build Corridor
- SurfaceModel generation
- Drainage review
- Structure interaction
- Watertight Solids readiness handoff
- exchange/export packages

Acceptance:

- consumer gaps are listed.
- any reverse-read or hidden fallback behavior is identified.
- deferred solid geometry work remains out of scope unless explicitly requested.

### Step 5 Consumer Inventory

| Consumer | Current consumption | Gap | Required behavior |
| --- | --- | --- | --- |
| Applied Sections | Consumes `IntersectionModel` through `applied_section_service.py` and stores active intersection, leg, control area, control regions, and grading policy on AppliedSection rows. | It does not yet carry enough source-completeness status such as anchor approval, control-area intent source, edge-family approval, or fallback source. | Add or expose intersection context status fields and diagnostics on AppliedSection rows. |
| Cross Section Viewer | Reads AppliedSection active intersection context and re-evaluates topology/edge/surface-zone/drainage context for review. | It can show useful context but may not clearly distinguish missing source from inferred/default result rows. | Display source status, fallback status, and edit handoff target. |
| Build Corridor / Build Parametric | Re-evaluates topology, edge network, surface zones, corridor clips, drainage hints, slope-face loops, and creates intersection surfaces/review rows. | It still owns many patch, boundary, curb-return sample, triangulation, and legacy slope breakline helpers. | Keep output helpers, but label them `legacy_output`, `inferred_fallback`, or `contract_consumed`; do not let them define source intent. |
| SurfaceModel / TIN builders | Build intersection surface, ordinary Slope Face, and intersection Slope Face output geometry. | Generated surface footprints and patch boundaries can become tempting reverse-read geometry. | Generated TINs remain output only. Any boundary source must come from result contracts. |
| Drainage review | Uses drainage hints and surface-zone context. | Hints can be mistaken for source drainage design. | Hints stay warning/handoff rows until Drainage source elements accept or reference them. |
| Structure interaction | Mostly Region/context based at this stage. | Intersection-specific structure ownership is not explicit. | Keep optional; require source refs before structures consume intersection-specific geometry. |
| Watertight Solid handoff | Discovers intersection patch/body targets and may read refined patch preview boundaries for patch solids. | Patch solid path can read preview mesh/shape points, which is not source-driven enough for final Digital Twin output. | Keep shallow and diagnostic; final solids wait until source/result contracts are stable. Mark patch-body paths as transition/legacy output. |
| Exchange/export packages | Consume output and result metadata where available. | Intersection source lineage may be incomplete. | Export should prefer normalized result refs and report missing lineage. |

### Reverse-Read Or Hidden Fallback Risks

- `intersection_patch_body` solid path can use refined preview boundary points.
- Intersection patch surface generation can use generated boundary and triangulation quality data.
- Curb-return arc samples can appear as design geometry when they are only evaluated preview/output.
- Ordinary Slope Face suppression can depend on generated intersection surface footprints.
- Legacy Slope Face breakline helpers can fill output gaps without source-edge ownership.
- Cross Section Viewer may re-evaluate contracts for review instead of reading a persisted accepted result set.
- Build Corridor review rows may be the first place missing source intent becomes visible.

### Consumer Rules

- Consumers must prefer accepted source/result refs over preview geometry.
- If a consumer uses fallback or legacy output, it must expose that status.
- Output helpers may remain for visual QA, but must not update source rows.
- Watertight intersection patch solids remain transitional until source-owned surface-zone and boundary contracts are sufficient.
- Build Corridor should be a contract consumer and diagnostic presenter, not the primary intersection decision maker.

### Step 5 Conclusion

Applied Sections and review surfaces are close to the desired contract-consuming shape.

Build Corridor and Watertight handoff still contain the highest-risk reverse-read or output-repair paths.

The next UX/review audit should make source status, fallback usage, and edit handoff visible so the user knows which source stage to fix.

## 11. Step 6 - UX and Review Audit

Status: Done

Goal:

- ensure users can understand intersection source ownership and result status.

Review surfaces should show:

- intersection id
- participating Alignment refs
- Region refs
- control area status
- curb return status
- lane connection status
- grading status
- drainage tie-in status
- missing source fields
- fallback usage
- edit handoff target

Acceptance:

- review UI requirements are listed.
- the user can identify what source needs editing when a result is wrong.

### Step 6 Review UI Requirements

| Review surface | Must show | Edit handoff |
| --- | --- | --- |
| Intersections wizard summary | overall source completeness, missing required source stages, warning stages, preset/default stages | open the relevant wizard step |
| Topology preview | intersection id, kind, anchor status, leg roles, control-area intent status, Region validation status | Anchor / Legs / Control Area steps |
| Edge Network preview | edge family status, curb-return corner status, lane connection status, source policy refs, inferred/default edge rows | Corners / Curb Returns / Edge Families / Lane Connections steps |
| Surface Zone preview | zone role, edge refs, vertical policy ref, source status, inferred/default zone warnings | Edge Families / Vertical-Grading steps |
| Grading review | controlling profile, crown strategy, crossfall transition rule, tie-in rule, low-point strategy | Vertical / Grading step |
| Drainage review | drainage intent status, gutter refs, low-point hints, inlet candidates, flow-route handoff refs | Drainage Intent step |
| Applied Sections review | active intersection, control area, leg, station kind, Centerline3D/Profile source status, fallback status | Participants / Anchor / Control Area steps |
| Build Corridor guided review | consumed result refs, legacy output status, fallback diagnostics, intersection patch status, slope-face loop status | Source wizard step or Applied Sections rebuild |
| Cross Section Viewer | active intersection context, source refs, result refs, fallback status, source edit target | Intersections or Applied Sections depending on missing field |
| Watertight handoff review | planned target family, consumed result refs, transition/legacy patch warning, solid-readiness status | Output only; source fixes route back to Intersections/Build Corridor |

### Status Vocabulary For Review

- `source_complete`: accepted source is available.
- `source_missing`: required source is absent.
- `derived_unapproved`: value was detected or calculated but not accepted.
- `preset_default`: starter preset value exists but should be reviewed.
- `contract_ready`: result contract is ready for downstream consumers.
- `contract_warning`: result exists but has missing optional source or inferred values.
- `contract_blocked`: result should not be trusted until required source is fixed.
- `legacy_output`: output exists through an older patch/repair path.
- `fallback_used`: fallback or inferred geometry was used.

### Edit Handoff Rules

- Missing anchor, station, or participant refs route to the Intersections wizard source steps.
- Missing Profile or Centerline3D refs route to Participants, Profile, or 3D Centerline panels.
- Missing control-area intent routes to Control Area authoring, not Regions first.
- Region mismatch routes to Control Area authoring with a Region validation note.
- Missing edge-family or lane connection policy routes to Edge Families or Lane Connections.
- Missing grading/crossfall source routes to Vertical / Grading.
- Drainage hints route to Drainage Intent or the Drainage panel, not Build Corridor.
- Build Corridor and Watertight reviews must not offer direct mesh edits as the primary fix.

### Step 6 Conclusion

The review workflow should answer three questions for every intersection result:

- What source stage owns this decision?
- Was the consumed result accepted, inferred, defaulted, or legacy output?
- Where should the user go to fix it?

This keeps review surfaces useful without turning them into hidden source editors.

## 12. Step 7 - Preset and Sample Data Audit

Status: Done

Goal:

- ensure starter intersection examples are not just visual samples, but complete parametric source examples.

Preset examples to review:

- T intersection
- Cross intersection
- Y intersection
- skewed intersection
- urban curb return intersection
- drainage-sensitive sag intersection

Acceptance:

- each sample has sufficient source fields to regenerate intended result contracts.
- missing sample data is listed as implementation backlog.

### Step 7 Preset Inventory

| Preset / sample | Current status | Source completeness | Required follow-up |
| --- | --- | --- | --- |
| `T Intersection - Basic` | Active in `Intersection`. | Creates editable source objects, IntersectionModel, control Regions, first-slice policy rows, Superelevation handoff, and Drainage handoff. | Add explicit anchor status, corner rows, lane connection policy, edge-family approval status, and control-area intent status. |
| `Cross Intersection - Basic` | Active in `Intersection`. | Similar to T preset with four-leg context and low-point review drainage mode. | Add explicit per-corner curb-return source rows, lane connection policy, and edge-family approval status for all four approaches. |
| `Roundabout - Single Lane` | Active as first-slice preset source builder. | Creates roundabout-style edge families, source objects, drainage handoff, and dedicated manual QA. | Keep as first-slice source contract; advanced operation/capacity/roundabout production workflow remains outside this audit. |
| `Y Intersection` | Supported in manual QA and source kind direction, but not active in `Intersection` panel rows. | Partial. | Add preset source example with branch roles, diverging alignment geometry, corner policies, and edge-family status. |
| Skewed intersection | Not yet a complete starter preset. | Missing. | Add sample that proves anchor/contact station detection handles skew without patch repair. |
| Urban curb-return intersection | Not yet a complete starter preset. | Missing. | Add curb/gutter/sidewalk/ditch edge-family source example and drainage intent. |
| Drainage-sensitive sag intersection | Not yet a complete starter preset. | Missing. | Add low-point/gutter/inlet handoff source data and validation expectations. |

### Preset Source Completeness Gaps

- Presets create useful source rows, but do not yet expose per-stage `source_complete`, `preset_default`, or `derived_unapproved` status.
- Anchor detection is created from geometry sampling but not stored as an explicit anchor source row with approval state.
- Control area is still strongly tied to generated control Regions.
- Edge policies exist, but edge families from Assembly/Subassembly contracts are not yet user-approved source rows.
- Curb-return policies are radius-oriented and not corner-owned enough.
- Lane connection policies are missing.
- Grading and drainage policy rows exist, but vertical tie and drainage intent are still too coarse.

### Step 7 Conclusion

The active preset system is useful for onboarding and QA, especially for T, Cross, and Roundabout.

For the redesigned intersection workflow, presets must become complete source examples rather than compact starter generators.

Y, skewed, urban curb-return, and drainage-sensitive sag presets should be added only after the source-completeness schema is implemented.

## 13. Step 8 - Implementation Backlog

Status: Done

Goal:

- convert audit findings into implementation tasks.

Backlog format:

- task id
- status
- affected boundary
- source files
- expected behavior
- validation path
- manual QA path

Acceptance:

- implementation tasks are ordered so source contracts are stabilized before result/output consumers.

### Step 8 Ordered Implementation Backlog

| Task id | Status | Boundary | Source files | Expected behavior | Validation path | Manual QA path |
| --- | --- | --- | --- | --- | --- | --- |
| INT-SRC-001 | Started | source | `models/source/intersection_model.py`, object persistence | Add or promote `IntersectionAnchorRow` with detected/manual/locked status and station refs. First slice adds anchor source rows, object persistence, source-builder draft anchor rows, and source roundtrip tests. | Source roundtrip test for anchor rows. | Create starter T, lock anchor, reopen panel, confirm anchor remains fixed. |
| INT-SRC-002 | Started | source/evaluation | `intersection_model.py`, `intersection_evaluation_service.py` | Add leg source status fields or equivalent validation for Profile, Centerline3D, Region, span source, and approval. First slice emits topology row `source_status` and named diagnostics for missing Profile, 3D Centerline, Region, control Region refs, leg approval, and Region-derived span source. | Contract test for missing leg refs producing source diagnostics. | T/Cross/Y wizard shows missing leg refs before preview. |
| INT-SRC-003 | Started | source/evaluation | `intersection_model.py`, `intersection_evaluation_service.py`, region linkage helpers | Add intersection-owned control-area intent before Region linkage. First slice emits control-area source method, approval, intent status, source Region refs, and mismatch/default diagnostics into topology and station context. | Source validation test for `intersection_owned`, `region_derived`, `preset_default`. | Edit control area intent and confirm Region mismatch warning. |
| INT-SRC-004 | Started | source/evaluation | `intersection_model.py`, `intersection_evaluation_service.py`, object persistence | Add corner source rows and corner-based curb-return policy refs. First slice adds `IntersectionCornerRow`, stores corner rows on the FreeCAD object, links default curb-return policies to corner refs, and carries `source_corner_ref` into edge-network rows. | Curb-return source roundtrip and topology/edge result test. | Confirm curb return attaches to named corner, not only global radius. |
| INT-SRC-005 | Started | source/evaluation | `intersection_model.py`, `intersection_evaluation_service.py`, Assembly/Subassembly bridge | Add edge-family policy rows derived from Assembly/Subassembly contracts with approval status. First slice adds edge-family intent, source method, approval status, Assembly/Subassembly refs, Subassembly kind, and diagnostics to edge policy rows and edge-network source status. | Edge-family source test for lane, shoulder, gutter, curb, sidewalk, ditch, median, side_slope. | Edge Network preview shows approved/default edge families. |
| INT-SRC-006 | Started | source/evaluation | `intersection_model.py`, `intersection_evaluation_service.py`, object persistence | Add lane connection policy rows. First slice adds `IntersectionLaneConnectionRow`, stores lane movement rows on the FreeCAD object, creates starter default movement rows, and reports topology lane-connection source diagnostics. | Topology/edge test for through/turn/merge/terminate rows. | Cross intersection shows lane connection completeness before surface preview. |
| INT-SRC-007 | Started | source/evaluation | `intersection_model.py`, `intersection_evaluation_service.py`, grading context result | Expand vertical/grading source policy with controlling profile, crown, tie-in, crossfall transition, low-point strategy. First slice adds grading source fields and carries approval/default diagnostics into grading-context rows. | Grading context result includes vertical policy refs and warnings. | Surface-zone preview warns when vertical policy is incomplete. |
| INT-SRC-008 | Started | source/evaluation | `intersection_model.py`, `intersection_evaluation_service.py`, drainage source bridge | Expand drainage intent source and distinguish hints from accepted drainage design. First slice adds accepted drainage element refs, flow route refs, inlet candidate refs, low-point refs, source status, approval, and diagnostics to drainage policy rows and hint rows. | Drainage hint test reports hint-only vs accepted source. | Drainage-sensitive sample shows inlet/low-point handoff status. |
| INT-RES-001 | Started | result | intersection result dataclasses | Add row-level source status and lineage refs to topology, edge network, surface zone, grading, drainage, and slope loop rows. First slices cover topology anchor/leg/control-area/lane-connection rows, corridor clipping control-area lineage, grading-context vertical lineage, drainage accepted-vs-hint lineage, edge-network rows, surface-zone rows that consume warning edge sources, and Slope Face loops that preserve consumed edge-network source status. | Result contract tests check `source_status` and source refs. | Build Corridor review lists accepted/default/fallback status. |
| INT-EVAL-001 | Started | evaluation | `intersection_evaluation_service.py` | Emit diagnostics for anchor, control-area intent, edge-family, lane connection, vertical, and drainage source gaps. First slice covers missing leg refs, control Region refs, missing source policy row families, and unresolved edge policy refs. | Diagnostic contract tests for each missing source class. | Wizard and Build Corridor show the same missing-source reason. |
| INT-UI-001 | Started | presentation/source | `cmd_intersection_editor.py`, `cmd_intersection_presets.py` | Replace compact creation flow with staged source-completeness wizard. First slice adds source-completeness helper rows and an Intersection panel stage table for Participants, Anchor, Legs, Control Areas, Corners, Edge Families, Lane Connections, Grading, Drainage, and Preview. | UI smoke through command construction where feasible. | User can see incomplete stages before Apply. |
| INT-UI-002 | Started | presentation/result | Intersections panel, Build Corridor, Cross Section Viewer | Add result preview sequence: source validation, topology, edge network, surface zones, grading, drainage, slope loops. First slice adds actionable source-completeness summary counts, next-stage guidance, and preview/apply readiness text to the Intersections panel. | Preview command tests for status rows. | Confirm previews are read-only and source refs are visible. |
| INT-UI-003 | Started | presentation/source | Intersections panel, Build Corridor, Cross Section Viewer | Add same-context edit return. First slice adds stable source-stage ids, handoff targets, target display in the source-completeness table, and a panel focus helper. | Panel focus smoke test for stage targets. | Select a missing/warning source stage from a handoff target without editing output geometry. |
| INT-UI-004 | Started | presentation/source | Intersections panel and source/result rows | Add source approval states. First slice adds approval-state and source-method rollups to staged source-completeness rows, plus a dedicated Approval column in the panel table. | Panel and preset contract tests for draft/default/detected source rows. | Confirm preset defaults, detected rows, accepted rows, and locked rows are visually distinct. |
| INT-UI-005 | Started | presentation/result | Intersections panel and result contracts | Expand the read-only preview sequence. First slice adds preview rows for source validation, topology, edge network, surface zones, grading, drainage, and slope loops without creating or editing output geometry. | Preview sequence contract and panel smoke tests. | Confirm each preview stage names the consumed result contract. |
| INT-CONS-001 | Started | result/output | `applied_section_service.py`, `cmd_generate_applied_sections.py` | Applied Sections carry source status and fallback diagnostics for intersection context. First slice stores active intersection source status and named diagnostics on AppliedSection rows, persists them on the AppliedSectionSet object, and shows a Cross Section Viewer `source_status` context row. | AppliedSectionSet contract test for intersection context status. | Cross Section Viewer shows station/source/fallback status. |
| INT-CONS-004 | Started | result/presentation | `applied_section_service.py`, `obj_applied_section.py`, `cmd_view_sections.py` | Applied Sections carry source-stage status rows for anchor, control-area, and edge-family ownership. First slice stores source-stage rows on AppliedSection, persists them on the AppliedSectionSet object, and shows `source_stage` rows in Cross Section Viewer. | Applied Sections, object roundtrip, and Viewer context focused tests. | Cross Section Viewer shows which Intersection source stage owns a station warning. |
| INT-CONS-005 | Started | result/presentation | `applied_section.py`, `applied_section_service.py`, `obj_applied_section.py`, `cmd_view_sections.py` | Applied Section frames carry explicit source mode, status, and diagnostics. First slice persists frame source metadata and shows `frame_source` rows in Cross Section Viewer so fallback station frames are visible. | Applied Sections, object roundtrip, and Viewer context focused tests. | Cross Section Viewer distinguishes source-geometry Centerline3D frames from fallback frames. |
| INT-CONS-006 | Started | presentation/handoff | `cmd_view_sections.py`, `cross_section_viewer.py` | Intersection Context rows carry handoff owner and target metadata. First slice adds Viewer columns for routing rows back to Intersection source stages, Applied Sections frame review, or Build Parametric intersection review. | Viewer context and optional-row focused tests. | Cross Section Viewer shows the owning editor/review surface for each intersection context row. |
| INT-CONS-002 | Started | output/presentation | `cmd_build_corridor.py`, `intersection_surface_patch.py` | Label legacy patch and fallback output paths as `contract_consumed`, `legacy_output`, or `inferred_fallback`. First slices expose `source_status`, `source_diagnostics`, source warning counts, Output Path labels, consumed-contract metadata, normalized Intersection Surface Patch rows, and Intersection Slope Face Boundary metadata on strip output. | Guided Review and contract tests for source, output-path, consumed-contract, patch-result, and boundary-first labels. | Build Corridor does not silently hide missing source intent or present legacy/fallback output as accepted source intent. |
| INT-CONS-003 | Started | output | `cmd_watertight_solids.py`, `solid_target_discovery_service.py` | Keep intersection patch solids transitional and diagnostic until accepted contracts are sufficient. First slices mark `intersection_patch_body` targets as transitional and add accepted-zone pavement, subgrade, slope, and curb-return target metadata from edge-network and surface-zone contracts. | Handoff tests confirm patch transition status and accepted zone target lineage. | Watertight panel distinguishes transitional patch bodies from accepted zone candidates. |
| INT-PRESET-001 | Planned | source sample | `cmd_intersection_presets.py`, preset docs | Upgrade T and Cross presets with source-completeness status. | Preset source completeness tests. | T/Cross preset smoke QA. |
| INT-PRESET-002 | Planned | source sample | `cmd_intersection_presets.py` | Add Y and skewed starter examples after source schema is available. | Preset creation tests. | Y/skew visual source QA. |
| INT-PRESET-003 | Planned | source sample | preset source builders | Add urban curb/gutter and drainage-sensitive sag examples. | Preset drainage/edge family tests. | Urban and sag drainage manual QA. |

### Step 8 Implementation Order

1. Stabilize source schema: INT-SRC-001 through INT-SRC-008.
2. Add result lineage/status: INT-RES-001 and INT-EVAL-001.
3. Build staged UX and read-only previews: INT-UI-001 and INT-UI-002.
4. Clean consumers and fallback labels: INT-CONS-001 through INT-CONS-003.
5. Expand presets after schema is stable: INT-PRESET-001 through INT-PRESET-003.

### Step 8 Conclusion

Implementation should start with source contracts.

Output cleanup and preset expansion should wait until source status and result lineage are available.

## 14. Step 9 - Validation Plan

Status: Done

Goal:

- define focused automated tests and manual QA checks.

Validation should cover:

- source object roundtrip
- starter source completeness
- intersection supplemental Applied Section rows
- result source refs
- fallback diagnostics
- Build Corridor consumer traceability
- review status visibility

Acceptance:

- validation can run without depending on final watertight solid geometry quality.

### Step 9 Automated Validation Plan

| Validation id | Scope | What to verify | Expected result |
| --- | --- | --- | --- |
| INT-VAL-001 | source roundtrip | IntersectionModel persists anchor, leg status, control-area intent, corner, edge-family, grading, and drainage intent rows. | Reopened document restores source rows and status values. |
| INT-VAL-002 | source completeness | T/Cross/Y source completeness validator reports missing required stages. | Missing anchor, legs, control area, edge family, grading, and drainage source produce named diagnostics. |
| INT-VAL-003 | preset completeness | T and Cross upgraded presets create source-completeness status fields. | Preset rows are marked `preset_default` until accepted. |
| INT-VAL-004 | topology result | Topology result carries source refs and source status. | Leg span and control-area rows include lineage and diagnostics. |
| INT-VAL-005 | edge network result | Edge rows carry edge-family, corner, curb-return, lane connection, and source-status refs. | Default/inferred edge rows are visible as warning status. |
| INT-VAL-006 | surface zone result | Surface zones consume edge network rows without reading generated surface geometry. | Zone rows include accepted/inferred edge refs and vertical policy refs. |
| INT-VAL-007 | grading/drainage result | Grading context and drainage hints distinguish source intent from hints. | Hint-only drainage remains warning until accepted source exists. |
| INT-VAL-008 | Applied Sections consumer | AppliedSection rows carry intersection context and fallback status. | Section rows expose intersection id, control area, leg, source trigger, and fallback diagnostics. |
| INT-VAL-009 | Build Corridor consumer | Build Corridor review rows report `contract_consumed`, `inferred_fallback`, or `legacy_output`. | Missing source intent is shown as diagnostics, not silent patch output. |
| INT-VAL-010 | review visibility | Cross Section Viewer and Build Corridor show source refs, result refs, and edit handoff target. | User can identify the source stage to fix. |

### Step 9 Manual QA Plan

| QA id | Scenario | Checkpoints |
| --- | --- | --- |
| INT-QA-001 | T Intersection source workflow | Create source, approve anchor, review legs, control area, corners, edge families, grading, drainage, then preview topology and edge network. |
| INT-QA-002 | Cross Intersection source workflow | Confirm four legs, four corner policies, lane connection status, and control-area status before surface-zone preview. |
| INT-QA-003 | Y Intersection source workflow | Confirm branch roles, diverging geometry source, and warning diagnostics for any missing future fields. |
| INT-QA-004 | Skewed intersection sample | Confirm skew anchor/contact station evaluation and no reliance on perpendicular patch repair. |
| INT-QA-005 | Urban curb/gutter sample | Confirm curb, gutter, sidewalk, ditch, side-slope edge families are source-visible. |
| INT-QA-006 | Drainage-sensitive sag sample | Confirm low-point, gutter refs, inlet candidates, and flow-route handoff remain source/hint separated. |
| INT-QA-007 | Build Corridor review | Confirm output surfaces report contract source and label any fallback/legacy patch path. |
| INT-QA-008 | Cross Section Viewer | Confirm active intersection context and edit handoff target are visible for selected Applied Sections. |

### Step 9 Non-goals For Validation

- final watertight solid boolean/fuse robustness
- non-manifold geometry repair
- full hydraulic sizing
- production roundabout design
- direct editing of generated meshes

### Step 9 Conclusion

Validation should prove that the redesigned intersection workflow is source-driven and traceable.

It should not attempt to certify final Digital Twin solid quality in this stage.

## 15. Current Next Action

Next action:

- begin implementation with `INT-SRC-001` through `INT-SRC-003`.

Expected output:

- source schema changes for anchor, leg source status, and intersection-owned control-area intent.
