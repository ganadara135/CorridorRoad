# V1 Intersection Creation Process Redesign Plan

Date: 2026-06-21
Status: In progress

Depends on:

- [V1_MASTER_PLAN.md](./V1_MASTER_PLAN.md)
- [V1_INTERSECTION_MODEL.md](./V1_INTERSECTION_MODEL.md)
- [V1_INTERSECTION_REDESIGN_PLAN.md](./V1_INTERSECTION_REDESIGN_PLAN.md)
- [V1_INTERSECTION_SOURCE_RESULT_AUDIT_PLAN.md](./V1_INTERSECTION_SOURCE_RESULT_AUDIT_PLAN.md)
- [V1_REGION_MODEL.md](./V1_REGION_MODEL.md)
- [V1_DRAINAGE_MODEL.md](./V1_DRAINAGE_MODEL.md)
- [V1_STRUCTURE_MODEL.md](./V1_STRUCTURE_MODEL.md)

## 1. Purpose

This document reviews the current v1 intersection creation process against the Parametric Road design philosophy.

It also defines a redesigned intersection creation process when the current flow is not parametric enough.

The conclusion of this audit is:

- the current IntersectionModel and several result contracts are directionally correct.
- the current user-facing creation process is still too dependent on starter generation, derived Regions, preview overlays, and later Build Corridor repair/review paths.
- a redesigned creation process is needed so users author enough durable intersection intent before downstream geometry is generated.

## 2. Core Product Rule

An intersection must be created from durable source intent.

The process must not depend on:

- manually selecting generated preview geometry as design truth
- interpreting ordinary corridor fragments after the fact
- relying on patch repair or mesh cleanup as the primary junction method
- treating starter examples as complete engineering source contracts

The correct flow is:

```text

Intersection source intent
  -> source validation
  -> topology result
  -> edge network result
  -> vertical/grading context result
  -> surface zone result
  -> Applied Section / Build Corridor consumers
  -> review and output geometry

```

## 3. Current Implemented Process

Current observed process:

1. User opens `Intersections`.
2. User chooses `Use Existing Alignments` or `Create Starter Sources`.
3. Existing Alignment mode requires primary and secondary Alignment refs.
4. Starter mode creates or fills Alignment, Profile, Stationing, Region, and review context.
5. The panel detects an XY intersection from sampled Alignment paths.
6. Control Regions are selected from Region rows tagged with an `intersection_ref`.
7. `build_intersection_model_from_sources()` creates a first-slice `IntersectionModel`.
8. The model stores one `IntersectionRow`, control areas, leg rows, default arm policies, default edge policies, a curb-return policy, grading policy, and drainage policy.
9. Review overlay and edge-network preview objects can be generated.
10. Evaluation services produce topology, edge-network, surface-zone, corridor-clip, grading, drainage-hint, and slope-face-loop contracts.
11. Build Corridor and Watertight Solids consume parts of those contracts.

This is better than a purely visual workflow, but it is not yet a complete parametric intersection creation workflow.

## 4. Parametric Philosophy Gaps

### 4.1 Source creation is still too compressed

Current issue:

- one panel action can infer many source rows from Alignment and Region choices.
- many policies are default-generated rather than user-authored or criteria-derived.

Why this matters:

- the generated source looks structured, but the user did not explicitly approve enough engineering intent.
- later results may appear parametric while still being based on generic assumptions.

Required improvement:

- split intersection creation into staged source authoring.
- force visible review of leg identity, control area, curb returns, edge policies, grading, and drainage intent before Apply.

### 4.2 Control area is Region-driven, not intersection-driven

Current issue:

- control areas are mostly derived from Region rows that already carry an `intersection_ref`.
- Region remains the station-span owner, but the intersection itself should own why the control area exists and which leg/edge responsibilities it creates.

Why this matters:

- a Region span can describe where an Assembly applies, but it does not fully describe a junction footprint.
- intersection geometry needs leg relationships, corner relationships, conflict areas, and edge ownership.

Required improvement:

- Intersection source should own `control_area_intent` first.
- Region refs should be linked/validated against that intent, not treated as the main source of the junction footprint.

### 4.3 Intersection point detection is not enough source intent

Current issue:

- the process detects an XY intersection and station values from sampled alignments.
- this gives a useful seed, but it is not enough to define a real intersection.

Why this matters:

- a road junction needs leg roles, skew, control area size, corner policy, and vertical tie-in behavior.
- a single detected point cannot define curb return limits, conflict zone, or pavement edge ownership.

Required improvement:

- store an `IntersectionAnchor` or equivalent source row with:
  - anchor point method
  - detected/locked/manual state
  - primary and secondary station refs
  - elevation source
  - tolerance and validation status

### 4.4 Leg identity is present but not yet user-owned enough

Current issue:

- leg rows exist, but many are generated from default role presets or control Region choices.
- the user does not yet author the full leg relationship as a first-class design step.

Why this matters:

- T, Cross, Y, skew, and future roundabout cases depend on stable leg roles.
- edge policies, drainage hints, grading, and curb returns should attach to leg roles, not just alignment refs.

Required improvement:

- introduce a dedicated `Legs` step before policy steps.
- require leg role, Alignment/Profile/Region refs, approach spans, and priority to be visible and editable.

### 4.5 Edge policy is too generic for actual intersection creation

Current issue:

- default edge policy rows can be generated for pavement and daylight edges.
- this is enough for first-slice topology, but not enough for real intersection surface creation.

Why this matters:

- lane edge, shoulder edge, gutter, curb, sidewalk, ditch, median, island, and daylight hinge need distinct ownership.
- downstream surface zones become fragile if these edges are implicit.

Required improvement:

- make edge families explicit source rows.
- define default edge families from Assembly/Subassembly contracts, then let the user accept or edit them.

### 4.6 Curb return is previewable before it is fully source-owned

Current issue:

- curb return preview geometry can be created from point, radius, and alignments.
- it is useful, but it can feel like geometry itself is the design.

Why this matters:

- curb return must be a policy plus evaluated edge-network result.
- preview geometry must never become the durable curb return source.

Required improvement:

- make curb return creation a source-policy stage:
  - corner id
  - from leg / to leg
  - radius or design vehicle rule
  - side
  - tangent/contact policy
  - sampling policy
  - status

### 4.7 Grading and vertical intent are too late

Current issue:

- grading context exists in evaluation, but the creation process does not yet make vertical control central enough.

Why this matters:

- many visible intersection failures come from mismatched profile, crossfall, and control area assumptions.
- if vertical policy is not source-owned early, surface-zone results can only report or patch symptoms.

Required improvement:

- add a `Vertical / Grading` authoring step before result preview.
- require mode, controlling profile, crossfall behavior, low-point strategy, and transition rule.

### 4.8 Drainage intent exists as hints, not creation-stage ownership

Current issue:

- drainage hints can be generated from surface zones.
- source drainage policies exist but are not yet a strong part of intersection creation.

Why this matters:

- intersections often fail practically because low points, gutters, and inlet locations are not decided early.

Required improvement:

- add a `Drainage Intent` creation step:
  - low-point review mode
  - gutter edge refs
  - proposed inlet candidate policy
  - flow-route handoff refs
  - outlet/structure refs where known

### 4.9 Build Corridor still carries too much intersection repair responsibility

Current issue:

- Build Corridor has many intersection patch, boundary, slope-face, trim, and review helpers.
- much of this is result/output work and some is necessary, but it makes the process feel like the intersection is fixed late.

Why this matters:

- Parametric Road should create complete enough source/result contracts before output geometry.
- Build Corridor should consume accepted contracts, not become the place where missing intersection design intent is guessed.

Required improvement:

- move missing source decisions upstream into the Intersections creation workflow.
- keep Build Corridor as consumer and reviewer.
- require diagnostics when contracts are missing instead of silently building guessed patches.

## 5. Redesign Decision

The intersection creation process should be redesigned.

This is not a full replacement of all existing code.

It is a staged migration:

- keep current source/result contracts that already match the direction.
- freeze or downgrade late patch/repair behavior where it hides missing source intent.
- rebuild the user-facing creation workflow around source completeness and staged result preview.

## 6. Redesigned User Workflow

Target workflow:

1. `Create Intersection`
2. Choose intersection kind.
3. Select participating Alignments.
4. Detect or manually set the intersection anchor.
5. Define legs and roles.
6. Define control area intent.
7. Link or create control Regions.
8. Define curb return policies.
9. Define edge families from Assembly/Subassembly context.
10. Define vertical/grading policy.
11. Define drainage intent.
12. Validate source completeness.
13. Preview topology.
14. Preview edge network.
15. Preview surface zones.
16. Apply source model.
17. Build Applied Sections and Build Corridor from accepted source/result contracts.

## 7. Redesigned Stage Model

| Stage | Status | Source/Result boundary | Purpose |
| --- | --- | --- | --- |
| 1. Process audit | Done | architecture | identify gaps in current creation flow |
| 2. Source completeness schema | Done | source | define missing source rows and required fields |
| 3. Intersection wizard UX | Done | presentation/source | split creation into explicit source-authoring steps |
| 4. Anchor and leg authoring | Done | source | make anchor, leg roles, spans, and refs user-owned |
| 5. Control area authoring | Done | source | create intersection-owned control area intent before Region linkage |
| 6. Edge and curb-return authoring | Done | source | make edge families and curb returns explicit policies |
| 7. Vertical/grading authoring | Done | source/evaluation | make grading and profile tie-in decisions visible before surface output |
| 8. Drainage intent authoring | Done | source/evaluation | make low-point and inlet handoff intent part of creation |
| 9. Result preview sequence | Done | evaluation/result | topology -> edge network -> surface zones before output meshes |
| 10. Consumer cleanup | Done | result/output | Build Corridor consumes contracts and stops guessing missing intent |
| 11. Preset redesign | Done | source | starter T/Cross/Y become complete source examples |
| 12. Validation and manual QA | Done | contracts/QA | verify the full process without relying on final solid geometry quality |

Status meanings:

- `Pending`: not started.
- `In progress`: active analysis or implementation.
- `Blocked`: waiting on another source/result dependency.
- `Done`: accepted for this redesign stage.

## 8. Required Source Additions Or Promotions

Candidate source additions:

- `IntersectionAnchorRow`
- `IntersectionCornerRow`
- `IntersectionControlAreaIntentRow`
- `IntersectionLegConnectionRow`
- `IntersectionLaneConnectionPolicyRow`
- `IntersectionEdgeFamilyPolicyRow`
- `IntersectionCurbReturnCornerPolicyRow`
- `IntersectionVerticalTiePolicyRow`
- `IntersectionDrainageIntentRow`

Some of these may map onto existing rows instead of becoming new dataclasses.

The key requirement is that the user-facing process must expose the intent explicitly.

## 9. Required Result Contracts

Existing useful contracts:

- `IntersectionTopologyResult`
- `IntersectionEdgeNetworkResult`
- `IntersectionSurfaceZoneResult`
- `IntersectionCorridorClipResult`
- `IntersectionGradingContextResult`
- `IntersectionDrainageHintResult`
- `IntersectionSlopeFaceLoopResult`

Required improvements:

- result rows should identify which source-stage requirement produced them.
- diagnostics should report missing source authoring stages, not only missing geometry.
- Build Corridor review rows should distinguish:
  - accepted contract
  - inferred fallback
  - legacy patch output
  - blocked due to missing source intent

## 10. Implementation Plan

### Phase 1 - Current process inventory

Status: Done

Tasks:

- map current Intersections panel workflow.
- map starter source creation.
- map existing source rows.
- map evaluation contracts.
- map Build Corridor intersection consumers.
- list late patch/repair helpers that should not define source intent.

Acceptance:

- inventory table identifies source, evaluation, result, output, and presentation responsibilities.

Inventory result:

| Area | Boundary | Current implementation | Redesign implication |
| --- | --- | --- | --- |
| Intersections panel | presentation/source | `cmd_intersection_editor.py` edits an IntersectionModel and can show review previews. | Keep as source editor, but split creation into visible source-completeness steps. |
| Intersection panel | presentation/source starter | `cmd_intersection_presets.py` creates starter sources or links existing Alignments, Regions, and IntersectionModel data. | Convert presets from one-click seed geometry into staged source examples. |
| Source model | source | `IntersectionModel` owns legs, control areas, arm policies, edge policies, curb returns, grading policies, and drainage policies. | Promote anchor, corner, lane connection, edge-family, vertical, and drainage intent where currently implicit. |
| Topology evaluation | evaluation/result | `IntersectionEvaluationService.evaluate_topology()` produces topology contracts. | Keep as first result preview after source completeness validation. |
| Edge network evaluation | evaluation/result | `evaluate_edge_network()` produces leg, daylight, and curb-return edge rows. | Make source edge-family policy visible before this result is accepted. |
| Surface zone evaluation | evaluation/result | `evaluate_surface_zones()` produces pavement and slope-face responsibility zones. | Treat zones as result contracts, not generated surface edits. |
| Slope Face loop evaluation | evaluation/result | `evaluate_slope_face_loops()` creates loop-owned intersection Slope Face contracts. | Preserve this direction; avoid returning to nearest-mesh repair. |
| Applied Sections | result builder | Applied Sections carry intersection control-area context and supplemental station rows. | Keep downstream from source/evaluation; expose fallback diagnostics. |
| Build Corridor / Build Parametric | output/presentation | Creates intersection surfaces, intersection slope-face surfaces, review rows, highlights, and diagnostics. | Move missing source decisions upstream; leave Build Corridor as contract consumer/reviewer. |
| Cross Section Viewer | presentation | Displays active intersection control area and result context. | Expand as review surface, not editor. |
| Watertight Solids handoff | output | Discovers intersection solid targets and trim closure outputs. | Keep shallow until intersection source/result workflow is stable. |

Late repair and preview paths that should not define source intent:

- one-patch `Intersection Surface` mesh generation
- generated curb-return arc preview samples
- patch/refined boundary preview properties
- output trim closure helpers
- ordinary Slope Face suppression based on generated footprint checks
- nearest TIN or generated mesh point selection used during output construction
- review highlight objects and manually hidden/shown preview families

Phase 1 conclusion:

- the project already has a useful edge-network-first result layer.
- the next redesign work should focus on source completeness, not more output patch repair.
- Build Corridor should be treated as a consumer of accepted intersection contracts.

### Phase 2 - Source completeness checklist

Status: Done

Tasks:

- define required source fields for T, Cross, and Y intersections.
- mark each field as required, optional, derived, or future.
- define which fields can be auto-detected but must be user-approved.

Acceptance:

- a T intersection can be described without relying on preview geometry or Build Corridor patch repair.

Source completeness result:

| Source stage | Required source data | Current state | Redesign action |
| --- | --- | --- | --- |
| Identity | intersection id, kind, source mode | Exists on `IntersectionRow`. | Keep. |
| Participants | primary/secondary Alignment refs, per-leg Profile and Centerline3D refs | Alignment refs exist; Profile and Centerline3D refs are often empty. | Require validation and user-visible missing-source status. |
| Anchor | anchor point, station refs, method, tolerance, lock/manual/detected state | Point and station refs exist, but method/status are missing. | Add/promote an anchor source stage. |
| Legs | leg id, role, priority, approach/departure station spans, Region refs | Basic rows exist. | Require visible user approval of roles/spans before result preview. |
| Control area | boundary intent, station/influence ranges, control Region refs, boundary method | Rows exist but are mostly Region-driven. | Add intersection-owned control-area intent before Region linkage. |
| Corners | corner id, from-leg, to-leg, side, active/disabled state | Missing. | Add corner source stage before curb-return policy. |
| Curb returns | corner ref, from/to leg refs, radius or design vehicle rule, tangent/contact policy, sampling policy | Basic radius policy exists. | Promote to corner-based curb-return source policy. |
| Lane connections | source lane refs, from/to leg refs, merge/continue/terminate rules | Missing. | Add lane connection policy rows. |
| Edge families | lane, shoulder, gutter, curb, sidewalk, ditch, median, side-slope edge policies from Assembly/Subassembly context | Generic edge rows exist. | Generate candidate edge families from Assembly/Subassembly contracts, then require user approval. |
| Vertical/grading | controlling profile, crown behavior, crossfall transition, tie-in rule, low-point strategy | Basic grading policy row exists. | Expand vertical/grading source stage. |
| Drainage intent | low-point mode, gutter refs, inlet policy, flow-route handoff refs | Basic drainage policy row exists. | Expand drainage intent stage. |
| Preset completeness | per-stage source-completeness status | Missing. | Add staged completeness summary for starter and existing-alignment workflows. |

T, Cross, and Y minimum source checklist:

| Field group | T | Cross | Y | Status |
| --- | --- | --- | --- | --- |
| Intersection identity and kind | required | required | required | currently sufficient |
| Primary and secondary Alignments | required | required | required | currently sufficient |
| Profile and Centerline3D refs per leg | required | required | required | needs validation |
| Anchor method/status | required | required | required | missing |
| Leg roles and spans | required | required | required | partially sufficient |
| Intersection-owned control area | required | required | required | insufficient |
| Corner rows | required | required | required | missing |
| Curb-return corner policies | required | required | partial/conditional | insufficient |
| Lane connection policies | required | required | required | missing |
| Edge-family policies from Assembly/Subassembly | required | required | required | insufficient |
| Vertical/grading policy detail | required | required | required | insufficient |
| Drainage intent detail | required | required | required | insufficient |

Source values that may be auto-detected but must be approved:

- anchor point and station refs
- leg approach/departure spans
- control area ranges
- curb-return contact stations
- Assembly/Subassembly-derived edge families
- preliminary low-point and inlet candidate hints

Phase 2 conclusion:

- existing dataclasses are a good base, but source authoring is not complete enough.
- the next UI design should expose staged source-completeness before allowing users to trust topology, edge network, surface-zone, or Build Corridor outputs.

### Phase 3 - Redesigned creation wizard

Status: Done

Tasks:

- design the panel sequence.
- add per-step status.
- add source completeness summary.
- add source/result diagnostics for Topology, Edge Network, and Surface Zones without creating editable preview geometry.

Acceptance:

- users can see which source stage is incomplete before Apply.

Redesigned wizard outline:

| Wizard step | Boundary | User action | Status output | Preview / apply behavior |
| --- | --- | --- | --- | --- |
| 1. Intersection Kind | source | Choose T, Cross, Y, or future type. | `complete`, `unsupported`, or `missing`. | No geometry preview. |
| 2. Participating Roads | source | Select primary and secondary Alignments, Profiles, 3D Centerlines, and Regions. | Per-leg missing refs. | Can run reference validation only. |
| 3. Anchor | source/derived | Detect anchor or manually enter point/station refs, then accept/lock it. | `detected_unapproved`, `manual`, `locked`, or `missing`. | Show anchor marker only; not accepted as geometry source until approved. |
| 4. Legs | source | Review leg roles, priority, approach/departure spans, Region refs. | Per-leg completeness. | `Preview Topology` enabled only when legs are complete. |
| 5. Control Area | source | Define intersection-owned control area intent and validate linked Regions. | `intersection_owned`, `region_derived`, `preset_default`, or `missing`. | Topology preview can show control area, but Apply warns on derived-only control areas. |
| 6. Corners and Curb Returns | source | Define corners, from-leg/to-leg pairs, radius/design vehicle rule, tangent/contact policy. | Per-corner completeness. | Edge-network result diagnostics remain warning/blocked until required corners are complete for the selected kind. |
| 7. Lane Connections | source | Define lane continuation, merge, terminate, or turn relationships. | Missing or complete by leg pair. | Surface-zone preview warns if lane connections are inferred. |
| 8. Edge Families | source | Accept Assembly/Subassembly-derived edge families for lane, shoulder, gutter, curb, sidewalk, ditch, median, side slope. | `derived_unapproved`, `approved`, or `missing`. | Edge network preview reports defaulted edge families separately. |
| 9. Vertical / Grading | source/evaluation | Choose controlling profile, crown behavior, crossfall transition, tie-in rule, low-point strategy. | `complete`, `incomplete`, or `uses_normal_superelevation`. | Surface-zone preview warns when vertical policy is incomplete. |
| 10. Drainage Intent | source/evaluation | Review gutter refs, low-point mode, inlet candidate policy, flow-route handoff refs. | `hint_only`, `source_complete`, or `missing`. | Drainage hints remain warnings until accepted source refs exist. |
| 11. Source Completeness Summary | presentation/source | Review all required source stages. | Overall `ready`, `warning`, or `blocked`. | `Apply Source Model` is blocked only for missing required source; warnings require explicit acknowledgement. |
| 12. Result Preview | evaluation/result | Preview topology, edge network, surface zones, grading context, drainage hints, and slope-face loops. | Result status and diagnostics. | Previews are read-only and never become source. |

Apply gating:

- `Apply Source Model` is blocked when identity, participants, anchor, legs, or control area are missing.
- `Preview Topology` requires identity, participants, anchor, legs, and control area.
- Edge-network result acceptance requires topology plus corner, curb-return, and edge-family source status.
- `Preview Surface Zones` requires edge network plus vertical/grading policy.
- Drainage preview may run with hint-only status, but must show that hints are not source design.
- Build Corridor should not be the first place where missing source intent is discovered.

Wizard status vocabulary:

- `missing`: required source data does not exist.
- `derived_unapproved`: data was detected or inferred and must be accepted.
- `preset_default`: data came from starter defaults and should be reviewed.
- `warning`: usable for preview, but not fully source-complete.
- `complete`: source is explicit enough for the current stage.
- `blocked`: result preview or Apply cannot continue.

Phase 3 conclusion:

- the redesigned UX should be a source-completeness wizard, not another geometry preview panel.
- previews are staged result views and should never be editable source geometry.
- Apply should write accepted source intent; Build Corridor should consume contracts after this stage.

### Phase 4 - Anchor, legs, and control area source ownership

Status: Done

Tasks:

- add or promote anchor rows.
- expose leg roles and approach spans.
- define control area intent before Region linkage.
- validate Regions against control area intent.

Acceptance:

- the source model explains the junction footprint and leg relationships without reading generated output geometry.

Anchor, leg, and control-area source ownership design:

| Source concept | Proposed source row or promotion | Required fields | Notes |
| --- | --- | --- | --- |
| Anchor | Add `IntersectionAnchorRow` or promote anchor fields from `IntersectionRow`. | `anchor_id`, `intersection_id`, `method`, `status`, `x`, `y`, `z`, `primary_alignment_ref`, `primary_station`, `secondary_station_refs`, `tolerance`, `locked`, `diagnostic_refs`. | Keeps detected/manual/locked anchor state source-visible. |
| Leg approval | Promote `IntersectionLegRow` with source-completeness fields. | existing leg fields plus `source_status`, `span_source`, `profile_ref`, `centerline3d_ref`, `approved`, `diagnostic_refs`. | Leg rows already exist; they need approval/status, not a full replacement. |
| Leg station span | Promote `approach_station_start/end`. | `span_source`, `station_start`, `station_end`, `control_area_ref`, `region_ref`. | Derived spans may be previewed but must be accepted. |
| Control area intent | Add `IntersectionControlAreaIntentRow` or extend `IntersectionControlArea`. | `intent_id`, `intersection_id`, `method`, `anchor_ref`, `leg_refs`, `boundary_rule`, `station_ranges`, `influence_ranges`, `offset_envelope`, `source_status`, `approved`. | Control area should be intersection-owned before Region linkage. |
| Region linkage | Keep Region refs as linked source context. | `control_region_refs`, `validation_status`, `mismatch_diagnostics`. | Regions validate station spans; they should not be the only footprint source. |
| Source completeness summary | Add non-geometric source status summary. | per-stage status, missing required fields, warning fields, source refs. | Can be stored as object properties or computed by validation service. |

Recommended dataclass direction:

```text
IntersectionModel
  intersection_rows
  anchor_rows
  leg_rows or promoted IntersectionRow.leg_rows
  control_area_intent_rows
  control_area_rows
  arm_policy_rows
  curb_return_policy_rows
  edge_policy_rows
  grading_policy_rows
  drainage_policy_rows
```

Anchor rules:

- detected anchors start as `derived_unapproved`.
- manual anchors start as `complete` after validation.
- locked anchors cannot be silently moved by later detection.
- changing participating Alignments invalidates detected anchors until revalidated.

Leg rules:

- each T intersection requires three accepted leg roles.
- each Cross intersection requires four accepted leg roles.
- each Y intersection requires three accepted branch/approach roles.
- each active leg must have Alignment, Profile, Centerline3D, and Region refs or explicit diagnostics.
- leg spans may be derived from control length or Regions, but must expose `span_source`.

Control-area rules:

- control area intent belongs to the Intersection source.
- Region refs are validation/linkage context, not the only owner of the footprint.
- station ranges derived from Region rows must be marked `region_derived`.
- station ranges created by presets must be marked `preset_default`.
- manually edited station ranges may be marked `accepted_source`.
- topology preview is blocked when control-area intent is missing.

Phase 4 conclusion:

- existing source rows should be promoted, not discarded.
- the main additions are anchor status, leg approval/source status, and intersection-owned control-area intent.
- this gives evaluation services enough source context to emit meaningful diagnostics before output geometry is built.

### Phase 5 - Edge, curb return, grading, and drainage intent

Status: Done

Tasks:

- expose edge family policies.
- expose corner-based curb return policies.
- expose vertical/grading policy.
- expose drainage intent policy.

Acceptance:

- topology and surface-zone result rows can be generated from accepted source policy rows.

Edge, curb-return, grading, and drainage source intent design:

| Source concept | Proposed row or promotion | Required fields | Consumer result |
| --- | --- | --- | --- |
| Edge family policy | Extend `IntersectionEdgePolicyRow` or add `IntersectionEdgeFamilyPolicyRow`. | `policy_id`, `intersection_id`, `leg_ref`, `edge_family`, `edge_role`, `source_subassembly_ref`, `source_link_role`, `side`, `offset_rule`, `elevation_rule`, `source_status`, `approved`. | `IntersectionEdgeNetworkRow` with accepted edge-family source refs. |
| Lane connection policy | Add `IntersectionLaneConnectionPolicyRow`. | `connection_id`, `from_leg_ref`, `to_leg_ref`, `from_lane_ref`, `to_lane_ref`, `rule`, `priority`, `source_status`. | Edge network and surface-zone rows can distinguish through lanes, turn lanes, merges, and terminations. |
| Corner row | Add `IntersectionCornerRow`. | `corner_id`, `intersection_id`, `from_leg_ref`, `to_leg_ref`, `side`, `corner_role`, `status`. | Curb-return policy rows attach to stable corners. |
| Curb-return corner policy | Promote `IntersectionCurbReturnPolicyRow`. | existing radius fields plus `corner_ref`, `from_leg_ref`, `to_leg_ref`, `design_vehicle_ref`, `contact_policy`, `sampling_policy`, `source_status`, `approved`. | Curb-return edge rows carry contact station refs with policy lineage. |
| Vertical tie policy | Add `IntersectionVerticalTiePolicyRow` or expand grading policy. | `policy_id`, `intersection_id`, `control_area_ref`, `controlling_profile_ref`, `crown_strategy`, `crossfall_transition_rule`, `tie_in_rule`, `low_point_strategy`, `source_status`. | Grading context rows report explicit source policy instead of default flattening. |
| Drainage intent | Add `IntersectionDrainageIntentRow` or expand drainage policy. | `intent_id`, `intersection_id`, `low_point_mode`, `gutter_edge_refs`, `inlet_candidate_policy`, `flow_route_refs`, `outlet_refs`, `source_status`. | Drainage hints become traceable suggestions or accepted drainage handoff rows. |

Control area authoring result:

- control area intent must be created before Region linkage.
- Region refs validate station spans and Assembly context.
- `region_derived` control areas are allowed for preview but should require acknowledgement before Apply.
- `accepted_source` control areas can drive topology and Applied Sections without Build Corridor repair.

Edge family rules:

- Candidate edge families should be derived from Assembly/Subassembly contracts.
- The user must be able to accept, disable, or override each family.
- At minimum, the workflow should recognize lane, shoulder, gutter, curb, sidewalk, ditch, median, and side_slope edge families.
- Edge-family defaults from presets must be marked `preset_default` until accepted.

Curb-return rules:

- Curb returns attach to corner rows, not just a global radius.
- A radius-only curb return is allowed as `preset_default`.
- Tangent/contact station refs are evaluation results and should not be hand-entered as output geometry.
- Design vehicle refs may drive radius later, but direct radius remains acceptable for the first redesign slice.

Vertical/grading rules:

- The user should decide whether the intersection uses normal superelevation, flattened control area, blended primary/side profiles, or manual vertical tie policy.
- Missing vertical source detail should block trusted surface-zone preview or mark it warning.
- Surface zones should report the vertical policy that produced their elevations.

Drainage rules:

- Drainage hints are not drainage source.
- Low-point and inlet candidates can be derived, but must be accepted by Drainage source before becoming design intent.
- Gutter and flow-route refs should be source-visible when available.

Phase 5 conclusion:

- edge, curb-return, grading, and drainage are source-authoring stages, not Build Corridor repair stages.
- the result preview sequence can now be specified as contract previews from accepted source rows.

### Phase 9 - Result preview sequence

Status: Done

Tasks:

- define preview order.
- define source gates for each preview.
- define result status vocabulary.
- define how previews remain read-only result views.

Acceptance:

- topology, edge network, surface zones, grading, drainage, and Slope Face loops can be previewed in a stable order before output meshes.

Result preview sequence:

| Preview stage | Required source gate | Produces | Block / warning behavior |
| --- | --- | --- | --- |
| 1. Validate Sources | identity, participants, anchor, legs, control area | source completeness summary | Blocks all result previews if required source is missing. |
| 2. Preview Topology | accepted or acknowledged anchor, leg roles, control-area intent | `IntersectionTopologyResult` | Warns when control area is `region_derived` or `preset_default`. |
| 3. Review Edge Network Contracts | topology ready, corners, curb-return policy, edge-family policy, lane connection status | `IntersectionEdgeNetworkResult` | Warns for default edge families or inferred curb-return contacts. |
| 4. Preview Surface Zones | edge network ready, vertical/grading policy at least warning-complete | `IntersectionSurfaceZoneResult` | Blocks trusted surface-zone status when required edge refs are inferred only. |
| 5. Preview Grading Context | surface zones ready, vertical/grading source policy | `IntersectionGradingContextResult` | Warns when normal superelevation is used through an intersection zone without explicit approval. |
| 6. Preview Drainage Hints | surface zones ready, drainage intent at least hint mode | `IntersectionDrainageHintResult` | Keeps hints as warnings until drainage source accepts them. |
| 7. Preview Slope Face Loops | surface zones and edge network ready | `IntersectionSlopeFaceLoopResult` | Blocks loop-owned slope surface when loops are open, self-crossing, or missing edge-family source. |
| 8. Apply Source Model | source completeness ready or warnings acknowledged | persisted `IntersectionModel` | Does not persist preview geometry as source. |
| 9. Build Applied Sections | applied source model, Alignment/Profile/Centerline3D/Region refs | intersection-aware AppliedSectionSet | Reports fallback if station frames or context are incomplete. |
| 10. Build Corridor | Applied Sections and accepted result contracts | output surfaces and review objects | Legacy patch output must be labeled and should not hide missing source. |

Preview rules:

- previews are read-only.
- preview geometry is not selectable as source intent.
- every preview row must expose source refs and result refs.
- preview diagnostics should name the source stage to fix.
- `Preview Surface Zones` should happen before any intersection surface mesh is generated.
- `Preview Slope Face Loops` should happen before intersection-owned Slope Face surface generation.

Phase 9 conclusion:

- the result preview flow is contract-first.
- Build Corridor comes after source validation, result previews, and Applied Sections.
- this prevents output mesh repair from becoming the first meaningful intersection design step.

### Phase 10 - Consumer cleanup

Status: Done

Tasks:

- identify Build Corridor intersection branches that infer missing source intent.
- turn those into diagnostics or result-contract consumers.
- keep preview/output generation but label fallback paths clearly.

Acceptance:

- Build Corridor does not silently turn missing intersection source intent into guessed geometry.

Consumer cleanup design:

| Consumer path | Current risk | Cleanup action |
| --- | --- | --- |
| Applied Sections intersection context | Stores active intersection context but not full source-completeness status. | Add context diagnostics for anchor, control-area intent, leg refs, Profile/Centerline3D refs, and fallback frame status. |
| Cross Section Viewer intersection context | Re-evaluates result context for review. | Display source status and edit handoff instead of only result rows. |
| Build Corridor topology/edge/surface review | Re-evaluates contracts and creates review rows. | Keep, but show `contract_consumed`, `inferred_fallback`, or `legacy_output` for each family. |
| Intersection Surface patch path | Output surface can depend on patch boundary/triangulation helpers. | Label as legacy/transition output unless backed by accepted surface-zone contracts. |
| Ordinary Slope Face suppression | Can depend on generated intersection footprints. | Prefer intersection Slope Face loop contracts; report fallback if footprint-based suppression is used. |
| Intersection Slope Face loops | Contract-oriented path is good. | Keep as preferred Slope Face handoff; report missing edge-family source in loop diagnostics. |
| Drainage hints | Hints can look like drainage design. | Keep warnings until Drainage source accepts low-point/inlet/flow-route intent. |
| Watertight intersection patch bodies | May read refined preview boundary points. | Keep shallow and label as transitional; do not use as final Digital Twin solid basis yet. |

Consumer cleanup rules:

- Output builders consume accepted result contracts first.
- Fallback output must report source stage to fix.
- Patch/preview geometry can remain for visual QA but cannot update source.
- Build Corridor should not create hidden intersection source decisions.
- Watertight handoff remains diagnostic until intersection source/result contracts are stable.

Phase 10 conclusion:

- Applied Sections and Cross Section Viewer mainly need richer status display.
- Build Corridor needs the clearest cleanup labels because it owns most visible output.
- Watertight intersection patch output should stay transitional until the intersection contract path is complete.

### Phase 11 - Preset redesign

Status: Done

Tasks:

- rebuild T/Cross/Y starter data as full source examples.
- include anchor, legs, control area, Regions, curb returns, edge families, grading, and drainage intent.
- include one urban curb/gutter intersection example.

Acceptance:

- starter presets are educational parametric examples, not just visual seed geometry.

Preset redesign requirements:

| Preset | Required source content | Purpose | Notes |
| --- | --- | --- | --- |
| T Intersection - Basic | anchor, three accepted legs, control-area intent, Region links, three corner rows, curb-return policies, edge-family policies, lane connections, vertical/grading policy, drainage intent | Minimal source-complete T example. | Existing preset is active; upgrade source-completeness status first. |
| Cross Intersection - Basic | anchor, four accepted legs, control-area intent, four corner rows, edge families, lane connections, grading policy, drainage intent | Four-approach conflict and clipping example. | Existing preset is active; add per-corner and lane connection source. |
| Y Intersection - Basic | anchor, three branch/approach legs, diverging geometry, corner policies, edge-family policies, grading and drainage intent | Branching/skew-like source example. | Add after anchor/control-area/edge-family schema exists. |
| Skewed Intersection - Basic | non-orthogonal anchor/contact stations, skew-aware control area, corner policies, edge-family policies | Proves station/contact evaluation does not rely on perpendicular assumptions. | Add after contact station diagnostics exist. |
| Urban Curb/Gutter Intersection | curb, gutter, sidewalk, ditch, lane/shoulder edge families, curb-return corner policy, inlet handoff intent | Urban source example with multiple edge families. | Should reuse Assembly/Subassembly edge-family derivation. |
| Drainage-Sensitive Sag Intersection | low-point strategy, gutter refs, inlet candidate policy, flow-route handoff refs, vertical tie policy | Demonstrates drainage source intent before Build Corridor output. | Keep hydraulic sizing out of scope. |
| Roundabout - Single Lane | circulatory edge families, splitter/entry/exit zones, drainage handoff, grading source status | First-slice roundabout source contract. | Keep as first-slice; do not expand into full roundabout production workflow here. |

Preset source-completeness fields:

- `preset_source_status`
- `anchor_status`
- `leg_status_summary`
- `control_area_status`
- `corner_status_summary`
- `edge_family_status_summary`
- `lane_connection_status`
- `vertical_grading_status`
- `drainage_intent_status`
- `result_preview_readiness`

Preset behavior rules:

- preset load creates editable source objects only.
- preset preview creates read-only result previews only.
- preset defaults are marked `preset_default` until accepted.
- generated Alignments, Profiles, Regions, Superelevation, Drainage, and IntersectionModel rows remain editable sources.
- no final corridor mesh is created by preset load.
- Build Corridor runs only after accepted source/result contracts and Applied Sections.

Phase 11 conclusion:

- T and Cross should be upgraded first because they already exist.
- Y, skewed, urban curb/gutter, and drainage-sensitive sag should be added after the source-completeness schema.
- Roundabout remains first-slice and should not pull the project into full roundabout design before ordinary intersections stabilize.

### Phase 12 - Validation plan

Status: Done

Tasks:

- source object roundtrip tests.
- starter source completeness tests.
- topology/edge/surface-zone result tests.
- Build Corridor consumer diagnostics tests.
- manual QA for T/Cross/Y creation flow.

Acceptance:

- validation proves the process is source-driven without depending on deep watertight solid geometry QA.

Validation strategy:

| Validation group | Required checks | Notes |
| --- | --- | --- |
| Source contract tests | anchor rows, leg source status, control-area intent, corners, edge families, lane connections, vertical/grading intent, drainage intent | These tests come before output geometry work. |
| Preset source tests | T and Cross source-completeness status; later Y, skewed, urban, drainage-sensitive samples | Presets must create editable source examples, not final meshes. |
| Result contract tests | topology, edge network, surface zones, grading context, drainage hints, slope-face loops | Rows must carry source refs and status. |
| Consumer traceability tests | Applied Sections, Build Corridor, Cross Section Viewer, Watertight handoff | Consumers must show contract/fallback/legacy status. |
| Diagnostic tests | missing anchor, missing control area, missing edge family, incomplete grading, hint-only drainage, legacy patch output | Diagnostics should name the source stage to fix. |

Manual QA sequence:

1. Create or load a T Intersection source example.
2. Confirm source-completeness summary shows anchor, legs, control area, corners, edge families, grading, and drainage.
3. Preview topology and confirm no output mesh is created.
4. Preview edge network and confirm edge-family and curb-return status.
5. Preview surface zones and confirm source edge refs.
6. Preview grading and drainage context.
7. Build Applied Sections and confirm intersection context rows.
8. Build Corridor and confirm consumed contracts and fallback labels.
9. Open Cross Section Viewer and confirm source/result context and edit handoff target.
10. Repeat the same source/result checks for Cross and Y examples when available.

Validation non-goals:

- final watertight solid quality
- geometry boolean robustness
- non-manifold repair
- hydraulic pipe sizing
- production roundabout workflow
- direct mesh editing

Phase 12 conclusion:

- validation is focused on source ownership, result lineage, consumer traceability, diagnostics, and review visibility.
- final solid quality remains intentionally shallow until ordinary intersections and related structures are stable.

## 11. Immediate Next Action

Next action:

- begin implementation with source schema changes for anchor, leg status, and control-area intent.

Expected output:

- initial source model changes matching `INT-SRC-001`, `INT-SRC-002`, and `INT-SRC-003`.

## 12. Non-goals

- final watertight solid quality work
- non-manifold or self-intersection repair
- hydraulic pipe sizing
- automatic interchange generation
- roundabout production workflow
- direct editing of generated meshes
