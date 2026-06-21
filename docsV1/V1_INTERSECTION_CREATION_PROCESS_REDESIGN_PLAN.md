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
| 1. Process audit | In progress | architecture | identify gaps in current creation flow |
| 2. Source completeness schema | Pending | source | define missing source rows and required fields |
| 3. Intersection wizard UX | Pending | presentation/source | split creation into explicit source-authoring steps |
| 4. Anchor and leg authoring | Pending | source | make anchor, leg roles, spans, and refs user-owned |
| 5. Control area authoring | Pending | source | create intersection-owned control area intent before Region linkage |
| 6. Edge and curb-return authoring | Pending | source | make edge families and curb returns explicit policies |
| 7. Vertical/grading authoring | Pending | source/evaluation | make grading and profile tie-in decisions visible before surface output |
| 8. Drainage intent authoring | Pending | source/evaluation | make low-point and inlet handoff intent part of creation |
| 9. Result preview sequence | Pending | evaluation/result | topology -> edge network -> surface zones before output meshes |
| 10. Consumer cleanup | Pending | result/output | Build Corridor consumes contracts and stops guessing missing intent |
| 11. Preset redesign | Pending | source | starter T/Cross/Y become complete source examples |
| 12. Validation and manual QA | Pending | contracts/QA | verify the full process without relying on final solid geometry quality |

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

Status: In progress

Tasks:

- map current Intersections panel workflow.
- map starter source creation.
- map existing source rows.
- map evaluation contracts.
- map Build Corridor intersection consumers.
- list late patch/repair helpers that should not define source intent.

Acceptance:

- inventory table identifies source, evaluation, result, output, and presentation responsibilities.

### Phase 2 - Source completeness checklist

Status: Pending

Tasks:

- define required source fields for T, Cross, and Y intersections.
- mark each field as required, optional, derived, or future.
- define which fields can be auto-detected but must be user-approved.

Acceptance:

- a T intersection can be described without relying on preview geometry or Build Corridor patch repair.

### Phase 3 - Redesigned creation wizard

Status: Pending

Tasks:

- design the panel sequence.
- add per-step status.
- add source completeness summary.
- add `Preview Topology`, `Preview Edge Network`, and `Preview Surface Zones` as result previews, not source edits.

Acceptance:

- users can see which source stage is incomplete before Apply.

### Phase 4 - Anchor, legs, and control area source ownership

Status: Pending

Tasks:

- add or promote anchor rows.
- expose leg roles and approach spans.
- define control area intent before Region linkage.
- validate Regions against control area intent.

Acceptance:

- the source model explains the junction footprint and leg relationships without reading generated output geometry.

### Phase 5 - Edge, curb return, grading, and drainage intent

Status: Pending

Tasks:

- expose edge family policies.
- expose corner-based curb return policies.
- expose vertical/grading policy.
- expose drainage intent policy.

Acceptance:

- topology and surface-zone result rows can be generated from accepted source policy rows.

### Phase 6 - Consumer cleanup

Status: Pending

Tasks:

- identify Build Corridor intersection branches that infer missing source intent.
- turn those into diagnostics or result-contract consumers.
- keep preview/output generation but label fallback paths clearly.

Acceptance:

- Build Corridor does not silently turn missing intersection source intent into guessed geometry.

### Phase 7 - Preset redesign

Status: Pending

Tasks:

- rebuild T/Cross/Y starter data as full source examples.
- include anchor, legs, control area, Regions, curb returns, edge families, grading, and drainage intent.
- include one urban curb/gutter intersection example.

Acceptance:

- starter presets are educational parametric examples, not just visual seed geometry.

### Phase 8 - Validation plan

Status: Pending

Tasks:

- source object roundtrip tests.
- starter source completeness tests.
- topology/edge/surface-zone result tests.
- Build Corridor consumer diagnostics tests.
- manual QA for T/Cross/Y creation flow.

Acceptance:

- validation proves the process is source-driven without depending on deep watertight solid geometry QA.

## 11. Immediate Next Action

Next action:

- complete Phase 1 inventory.

Expected output:

- a table of current intersection source, evaluation, result, output, and presentation artifacts.
- a list of late geometry repair or preview paths that should not be treated as source intent.

## 12. Non-goals

- final watertight solid quality work
- non-manifold or self-intersection repair
- hydraulic pipe sizing
- automatic interchange generation
- roundabout production workflow
- direct editing of generated meshes

