# V1 Intersection Remaining Work Plan

Date: 2026-06-24  
Status: Active tracking plan  
Scope: remaining Intersection work after the first source-status, Applied Sections, Build Parametric, and Watertight Solids diagnostic slices

## Purpose

This document tracks the remaining Intersection work in execution order.

The goal is to move Intersection from a first-slice source/review workflow into a source-complete, result-traceable, Digital Twin-ready road junction workflow.

The core rule remains:

- Intersection source intent must be authored in `IntersectionModel` and related source rows.
- Evaluation services must produce deterministic topology, edge, grading, drainage, and surface-zone result contracts.
- Applied Sections, Build Parametric, Cross Section Viewer, Watertight Solids, and Exchange must consume those contracts.
- Generated preview meshes, patch surfaces, or watertight patch solids must not become source truth.

## Current Baseline

The current implementation already includes these first slices:

| Area | Status | Current behavior |
| --- | --- | --- |
| User command | Done | User-facing command is `Intersection`; older workbench-exposed `Intersections` command has been removed from the active workflow. |
| Preset source creation | Done | T, Cross, Y, Skewed, Urban Curb/Gutter, Drainage-Sensitive Sag, and Roundabout starter workflows create editable source objects and link them into an Intersection model with review lineage. |
| Multi-alignment handoff | Done | Intersection starter sources create Region rows per participating Alignment and Applied Sections include intersection supplemental stations. |
| Topology source diagnostics | Done | Topology rows report missing Profile, 3D Centerline, Region, control Region, and policy source context with row-level source status. |
| Edge Network source diagnostics | Done | Edge rows report unresolved policy refs, incomplete curb-return policy context, and Assembly/Subassembly edge-family lineage breaks. |
| Surface Zone source diagnostics | Done | Surface-zone rows carry source status and diagnostics from consumed edge rows. |
| Applied Sections context | Done | AppliedSection rows store active intersection source status, named source diagnostics, source-stage rows, frame-source status counts, and Viewer handoff context. |
| Cross Section Viewer | Done | Intersection Context includes source status, handoff owner/target, lineage, and derived handoff summary rows for station-level review. |
| Build Parametric review | Done | `Intersections` table exposes `Source Status`, `Source Diagnostics`, source-warning summary counts, normalized Surface Patch rows, accepted zone-surface candidates, and replacement-readiness gates. |
| Watertight Solids handoff | Done | `intersection_patch_body` targets are marked transitional with `digital_twin_handoff=review_required`, accepted zone targets are discoverable, and transitional-only packages are blocked from final Digital Twin handoff. |

## Status Legend

| Status | Meaning |
| --- | --- |
| Done | Implemented and covered by focused tests or manual QA record. |
| Started | First slice exists, but the full source/result contract is not complete. |
| Planned | Not implemented or only represented in design direction. |
| Blocked | Should not proceed until an earlier source/result dependency is complete. |

## Phase 1 - Source Completeness

Goal:

- make all source intent explicit before deeper surface or solid output work.

| Task id | Status | Work item | Primary files | Acceptance criteria |
| --- | --- | --- | --- | --- |
| INT-REM-SRC-001 | Done | Add or promote `IntersectionAnchorRow` with detected/manual/locked status, station refs, tolerance, and source method. Completed slices add source row persistence, source builder draft anchor rows, roundtrip tests, explicit diagnostics for unknown anchor source method or approval status, and row-level error status for missing primary Alignment refs. | `models/source/intersection_model.py`, `objects/obj_intersection.py` | Anchor persists through document roundtrip and the panel can distinguish detected, manual, locked, defaulted, invalid, and source-blocking anchor states. |
| INT-REM-SRC-002 | Done | Complete leg source status for Profile, 3D Centerline, Region, span source, approval, and role completeness. Completed slices add leg `source_method`, `approval_status`, `span_source`, diagnostic rows, station-context handoff, explicit diagnostics for unknown leg source method/approval/span source, and row-level error status for missing Alignment refs. | `intersection_model.py`, `intersection_evaluation_service.py` | Missing, defaulted, invalid, or source-blocking leg context appears before edge preview and is preserved in topology diagnostics. |
| INT-REM-SRC-003 | Done | Add intersection-owned control-area intent separate from Region-derived ranges. Completed slices add control-area `source_method`, `approval_status`, `intent_status`, source Region refs, topology/station-context diagnostics, explicit diagnostics for unknown control-area source method/approval/intent status, and row-level error status for missing Alignment or station ranges. | `intersection_model.py`, Region linkage helpers | Control areas can be `intersection_owned`, `region_derived`, or `preset_default`; missing, mismatched, invalid, or source-blocking control-area source states are diagnostic. |
| INT-REM-SRC-004 | Done | Add corner source rows and corner-based curb-return policy refs. Completed slices add `IntersectionCornerRow`, FreeCAD object persistence, starter default corner rows, curb-return `corner_refs`, edge-network `source_corner_ref` diagnostics, explicit diagnostics for unknown corner source method/approval status, and row-level error status for missing control-area, leg, side/quadrant, or curb-return policy context. | `intersection_model.py`, `intersection_evaluation_service.py` | Curb returns attach to named corners, from-leg/to-leg refs, side refs, source state, and policy lineage instead of only a global radius, and source-blocking corner context is not accepted as warning-only geometry. |
| INT-REM-SRC-005 | Done | Add edge-family source policy derived from Assembly/Subassembly contracts with approval status. Completed slices add edge-family intent, source method, approval status, Assembly/Subassembly refs, Subassembly kind, diagnostic rows, explicit diagnostics for unknown edge-family intent/source method/approval status, and row-level error status for missing source policy refs or Subassembly kind mismatch. | `intersection_model.py`, `cmd_intersection_presets.py`, Assembly/Subassembly bridge | Lane, shoulder, gutter, curb, sidewalk, ditch, median, and side-slope edge families have approved/default/missing/invalid/source-blocking status before edge-network and lane-connection handoff. |
| INT-REM-SRC-006 | Done | Add lane connection policy rows. Completed slices add `IntersectionLaneConnectionRow`, FreeCAD object persistence, starter default movement rows, topology `lane_connection_rows`, explicit diagnostics for unknown movement type/source method/approval status, and row-level error status for missing/unresolved leg or edge-policy refs. | `intersection_model.py`, topology/edge evaluation | Through, turn, merge, diverge, and terminate lane relationships are source rows with valid, invalid, or source-blocking state and edge-policy lineage, not inferred only from generated edges. |
| INT-REM-SRC-007 | Done | Expand vertical/grading policy. Completed slices add controlling Profile refs, crown behavior, tie-in rule, crossfall transition, low-point strategy, source method, approval status, diagnostics, explicit validation for unknown grading values, and row-level error status for blocked vertical handoff when intersection override grading lacks a controlling Profile. | `intersection_model.py`, `intersection_evaluation_service.py` | Controlling profile, crown behavior, tie-in rule, crossfall transition, low-point strategy, source state, invalid fallback labels, and source-blocking vertical handoff are visible in grading-context result rows. |
| INT-REM-SRC-008 | Done | Expand drainage intent source. Completed slices add accepted drainage element refs, flow route refs, inlet candidate refs, low-point refs, intent status, source method, approval status, diagnostics, explicit validation for unknown drainage values, and row-level error status for accepted/source-owned drainage intent missing accepted elements or flow routes. | `intersection_model.py`, drainage source bridge | Drainage hints are separated from accepted drainage source elements, flow routes, inlet candidates, gutter edges, invalid mesh-derived drainage labels, and source-blocking accepted drainage gaps. |

## Phase 2 - Result Contract Completion

Goal:

- make every evaluated Intersection result row traceable to source ownership and fallback status.

| Task id | Status | Work item | Primary files | Acceptance criteria |
| --- | --- | --- | --- | --- |
| INT-REM-RES-001 | Done | Complete row-level source status and lineage across topology, edge network, surface zones, grading context, drainage hints, and slope-face loops. Completed result-lineage audit slices add Slope Face loop source status, source diagnostics, source surface-zone status, source edge-network status, and lineage status from consumed surface-zone and edge-network rows. | `models/result/intersection_*.py` | Each result row has enough source refs and diagnostics to explain accepted, warning, defaulted, error, or fallback status. |
| INT-REM-RES-002 | Done | Add anchor result contract. Completed slices add topology anchor result rows, source status, tolerance, point, station mapping diagnostics, station lineage status, and same-context source-stage handoff target. | `models/result/intersection_topology.py`, `services/evaluation/intersection_evaluation_service.py` | Anchor result records accepted station/point, source status, tolerance, diagnostic refs, station lineage status, and edit handoff target. |
| INT-REM-RES-003 | Done | Add control-area intent result contract. Completed slices add topology control-area result/source refs, Region lineage status, clipping boundary refs, corridor clipping source diagnostics, Region handoff status, clipping handoff status, and same-context source-stage handoff target. | `intersection_topology.py`, evaluation service | Region-derived control areas are labeled and never silently treated as accepted source intent; clipping and Region handoff state remain reviewable. |
| INT-REM-RES-004 | Done | Add lane-connection result contract. Completed slices add source lane-connection refs, movement lineage status, leg source status rollups, edge-family source status, leg handoff status, edge handoff status, source-stage handoff target, and topology review aggregation. | `intersection_topology.py`, evaluation service | Lane continuity, turn, merge, diverge, and terminate rows are reviewable before surface generation with leg and edge handoff state. |
| INT-REM-RES-005 | Done | Add grading-context source lineage. Completed slices add source grading policy refs, Profile lineage status, Profile handoff status, Superelevation source status, Superelevation handoff status, vertical handoff status, fallback/default status, and grading review handoff target. | `intersection_grading_context.py` | Vertical policy refs, profile refs, superelevation refs, fallback grading decisions, and review handoff states are visible. |
| INT-REM-RES-006 | Done | Add drainage accepted-vs-hint status. Completed slices add source drainage policy refs, accepted handoff status, review status, accepted drainage refs, source-lineage status, source-stage handoff targets, and Build Parametric source diagnostics. | `intersection_drainage_hint.py` | Drainage rows distinguish source-owned drainage elements from low-point review hints and can route back to the owning Drainage source stage. |

## Phase 3 - Intersection Panel Workflow

Goal:

- replace compressed creation with staged source-completeness review.

| Task id | Status | Work item | Primary files | Acceptance criteria |
| --- | --- | --- | --- | --- |
| INT-REM-UI-001 | Done | Convert `Intersection` panel into staged source workflow. Completed slices add a source-completeness table and helper rows for Participants, Anchor, Legs, Control Areas, Corners, Edge Families, Lane Connections, Grading, Drainage, and Preview. | `cmd_intersection_editor.py`, `cmd_intersection_presets.py` | User can review Participants, Anchor, Legs, Control Area, Corners, Edge Families, Grading, Drainage, and Preview before Apply. |
| INT-REM-UI-002 | Done | Add source completeness summary. Completed slices add accepted/warning/missing/error counts, next-stage guidance, and preview/apply readiness text to the staged panel workflow. | Intersection panel | Missing required stages and warning/default stages are visible before preview. |
| INT-REM-UI-003 | Done | Add same-context edit return. Completed slices add stable source-stage ids, handoff targets, target display in the source-completeness table, and a panel focus helper. | Intersection panel, Cross Section Viewer handoff | Opening a missing-source item from Viewer or Build Parametric returns to the relevant stage and source row. |
| INT-REM-UI-004 | Done | Add source approval states. Completed slices add approval-state and source-method rollups to the staged source-completeness rows and panel table. | Intersection panel and source rows | Preset defaults, detected rows, and user-approved rows are visually distinct. |
| INT-REM-UI-005 | Done | Expand read-only preview sequence. Completed slices add result-contract preview rows for source validation, topology, edge network, surface zones, grading, drainage, and slope loops. | Intersection panel | Source validation, topology, edge network, surface zones, grading, drainage, and slope loops are reviewable without editing output geometry. |

## Phase 4 - Applied Sections And Cross Section Viewer

Goal:

- keep station-level intersection context traceable from source through Applied Sections review.

| Task id | Status | Work item | Primary files | Acceptance criteria |
| --- | --- | --- | --- | --- |
| INT-REM-APP-001 | Done | Carry active intersection source status on AppliedSection rows. Completed slices preserve source status, diagnostics, source-stage rows, and durable object summary counts for active Intersection context. | `applied_section.py`, `applied_section_service.py`, `obj_applied_section.py` | Active station rows preserve source status, named diagnostics, warning counts, and summary metadata through object roundtrip. |
| INT-REM-APP-002 | Done | Add anchor/control-area/edge-family source status to Applied Sections. Completed slices store station source-stage rows, expose them in Cross Section Viewer context rows, and show explicit lineage status beside handoff owner/target fields. | `applied_section_service.py`, `cmd_view_sections.py`, `cross_section_viewer.py` | Cross Section Viewer can show which source stage owns the selected station warning. |
| INT-REM-APP-003 | Done | Add fallback status for sparse station frames. Completed slices add explicit frame source mode/status/diagnostics, show `frame_source` context rows in Cross Section Viewer, and preserve `CenterlineSourceStatusCounts` on Applied Section result objects. | Applied Section service and supplemental sampling | Viewer distinguishes source-geometry 3D Centerline frames from fallback or interpolated frames. |
| INT-REM-APP-004 | Done | Add edit handoff targets to Intersection Context rows. Completed slices add handoff owner, target, lineage, and handoff-summary rows for Intersection, Applied Sections, and Build Parametric routing. | `cmd_view_sections.py`, `cross_section_viewer.py` | Viewer rows can route users to Intersection, Applied Sections, or Build Parametric depending on the missing contract. |

## Phase 5 - Build Parametric Output Cleanup

Goal:

- keep Build Parametric as a consumer and review/output builder, not an intersection source repair stage.

| Task id | Status | Work item | Primary files | Acceptance criteria |
| --- | --- | --- | --- | --- |
| INT-REM-BLD-001 | Done | Expose source status in Build Parametric Intersection rows. Completed slices add source status, source diagnostics, source-warning counts, source-status summary distribution, Slope Face Loop source-lineage warning propagation, and consumed Edge Network status notes to contract review rows. | `cmd_build_corridor.py` | `Source Status`, `Source Diagnostics`, source-warning counts, Slope Face Loop lineage warnings, and consumed Edge Network status notes are shown in the panel and tests. |
| INT-REM-BLD-002 | Done | Label legacy patch and fallback output helpers. Completed slices add output-path labels to Guided Review, Output Review, Intersection Contracts, missing-source rows, and replacement readiness rows. | `cmd_build_corridor.py` | Review rows identify `contract_consumed`, `inferred_fallback`, `legacy_output`, `review_gate`, or `missing_source` path where applicable. |
| INT-REM-BLD-003 | Done | Replace late surface repair with accepted result contracts. Completed slices record consumed topology, edge, surface-zone, grading, drainage, and slope-loop result ids, row-level diagnostics, Slope Face review notes, and contract-first output-path labels. | Build Parametric intersection helpers | Intersection Surface and Slope Face output consume topology, edge, surface-zone, grading, drainage, and slope-loop contracts instead of reverse-reading preview mesh, and preserve consumed row source diagnostics. |
| INT-REM-BLD-004 | Done | Add dedicated `Intersection Surface Patch` result contract. Completed slices add boundary, triangulation, quality, footprint, accepted Surface Zone output, review lineage, replacement gate, and downstream handoff metadata. | new result/output model, Build Parametric | Patch footprint, boundary loops, curb-return bands, tie-in edges, triangulation quality, accepted zone output rows, and replacement review status are normalized result/output rows. |
| INT-REM-BLD-005 | Done | Complete slope-face boundary-first rule. Completed slices now record `Intersection Slope Face Boundary` result metadata without creating visible boundary or strip output. | Build Parametric slope-face helpers | `Intersection Slope Face Boundary` is metadata-only until a production-safe display is approved. |

## Phase 6 - Watertight Solids And Digital Twin Handoff

Goal:

- move from transitional patch prism to source-traceable intersection solid bodies.

| Task id | Status | Work item | Primary files | Acceptance criteria |
| --- | --- | --- | --- | --- |
| INT-REM-WS-001 | Done | Mark `intersection_patch_body` as transitional. Completed slices add transitional diagnostics, review-required Digital Twin handoff status, legacy patch-prism reason, accepted zone-solid replacement families, replacement guidance, and panel labels. | `solid_target_discovery_service.py`, `cmd_watertight_solids.py` | Target has `intersection_patch_body_transitional`, `quality_status=transitional`, `digital_twin_handoff=review_required`, and visible accepted-zone replacement guidance. |
| INT-REM-WS-002 | Done | Add accepted intersection zone solid targets. Completed slices add accepted surface-zone/edge contract lineage, Digital Twin handoff labels, pending-builder state, and panel labels to pavement, subgrade, slope, and curb-return zone targets. | Watertight target discovery, surface-zone results | Pavement, subgrade, slope, and curb-return intersection targets consume accepted surface-zone/edge contracts. |
| INT-REM-WS-003 | Done | Block final Digital Twin handoff on transitional-only patch solids. Completed slices add final-quality handoff status, shared replacement blocker metadata, Simulation QA/Package blockers, ExchangePackage source-context rows, JSON/IFC export summaries, and preview-summary visibility. | Simulation QA, package export, ExchangePackage export | Transitional-only patch packages are blocked from final Digital Twin handoff, and the replacement blocker is traceable from Build Parametric preview through Watertight, Simulation Package, ExchangePackage, JSON, IFC, and preview summaries. |
| INT-REM-WS-004 | Done | Add intersection trim/fuse handoff status to Simulation QA and downstream package/export consumers. Completed slices persist trim pair counts, max gap, fuse status, accepted/fallback handoff status, QA diagnostics, Simulation Package handoff status, JSON export fields, and panel status text. | Watertight simulation QA service, Simulation Package export | QA, Package, JSON export, and panel status text report patch-to-road body connection, gap, trim candidate, and accepted/fallback status. |
| INT-REM-WS-005 | Done | Preserve source lineage in solid output and exchange rows. Completed slices preserve row-level source/material/notes through Watertight output roundtrip, Simulation Package rows, package JSON export, Exchange source-context rows, JSON/IFC summaries, and preview summaries. | Watertight output mapper, exchange package | Solid rows and exchange rows include intersection, leg, control area, surface zone, edge family, material, station span, notes, and diagnostic refs where available. |

## Phase 7 - Presets And Examples

Goal:

- expand presets only after source schema and result lineage are strong enough.

| Task id | Status | Work item | Primary files | Acceptance criteria |
| --- | --- | --- | --- | --- |
| INT-REM-PRESET-001 | Done | Upgrade T and Cross presets with source-completeness status. Completed slices add preset source-completeness refs, row-level source-completeness notes, review-required diagnostics, and T/Cross coverage for draft/default source rows. | `cmd_intersection_presets.py` | Presets populate anchor, control area, corner, edge-family, grading, drainage, and approval/default status rows. |
| INT-REM-PRESET-002 | Done | Add Y Intersection starter example. Completed slices add a `Y Intersection - Basic` preset, primary/left/right branch starter Alignments and Regions, branch secondary refs, Y corner policies, branch review refs, and review-required diagnostics. | preset builders and docs | Y preset creates branch roles, diverging alignment geometry refs, corner policies, and warning diagnostics for incomplete future fields. |
| INT-REM-PRESET-003 | Done | Add skewed intersection starter example. Completed slices add a `Skewed Intersection - Basic` preset, non-orthogonal primary/secondary starter Alignments, skew-aware corner policy rows, skew review refs, and review-required skew diagnostics. | preset builders and docs | Skewed source geometry remains source-driven and edge network preview does not require mesh repair. |
| INT-REM-PRESET-004 | Done | Add urban curb/gutter example. Completed slices add an `Urban Curb/Gutter - Basic` preset with curb, gutter, sidewalk edge-family rows, inlet/low-point drainage handoff refs, urban review refs, and review-required diagnostics. | preset builders, drainage/edge policies | Curb, gutter, sidewalk, inlet, and low-point review context are source-visible. |
| INT-REM-PRESET-005 | Done | Add drainage-sensitive sag example. Completed slices add a `Drainage-Sensitive Sag - Basic` preset with sag Profile controls, low-point refs, inlet candidate refs, flow-route refs, sag review refs, and review diagnostics. | preset builders, drainage source bridge | Drainage policy, inlet candidates, and flow-route handoff are represented as source/hint rows. |

## Phase 8 - Validation And QA

Goal:

- keep each stage testable without relying only on visual inspection.

| Task id | Status | Work item | Acceptance criteria |
| --- | --- | --- | --- |
| INT-REM-VAL-001 | Done | Keep contract tests for topology, edge, surface-zone, Applied Sections, Build Parametric, Viewer, and Watertight handoff. Completed slices add source-status/source-diagnostic coverage and final Digital Twin handoff package coverage for transitional-only patch vs accepted zone candidates. | Tests cover source status, diagnostics, transitional blockers, and accepted-zone candidate handoff paths. |
| INT-REM-VAL-002 | Done | Add source object roundtrip tests for anchor, corner, lane connection, edge-family approval, grading, drainage intent rows, and result-ref traceability. Completed slices add `.FCStd` save/reopen coverage for source intent rows, approval/default diagnostics, and topology/drainage/surface-zone result refs. | Reopened document restores source rows, approval/default status, and source-owned result refs. |
| INT-REM-VAL-003 | Done | Add panel smoke tests for staged source completeness. Completed slices verify preset-created warning stages, source-stage focus, and row-level handoff/source-lineage metadata without applying output geometry. | Panel can construct stages, report missing source, and expose source handoff targets without applying output geometry. |
| INT-REM-VAL-004 | Done | Add manual QA records for T, Cross, Y, skewed, urban, drainage-sensitive, and roundabout intersections. Completed slices add preset QA record tables, detailed Skewed/Urban/Sag/Roundabout procedures, and source handoff/source-lineage expected-result fields. Actual execution remains a manual FreeCAD document activity. | Each workflow has expected source status, source handoff targets, preview lineage, Build Parametric status, and Watertight handoff status. |
| INT-REM-VAL-005 | Done | Add regression QA for the original stitched Lane/Shoulder/Side Slope problem. Completed slices add manual regression steps for Lane, Shoulder, Side Slope, ordinary Slope Face, Intersection Slope Face review separation, and Build Parametric source-lineage notes. Actual execution remains a manual FreeCAD document activity. | Intersection preset-created roads do not stitch unrelated alignment scopes in Build Parametric review, and warning lineage stays visible in review notes. |

## Recommended Execution Order

1. Finish source schema gaps: anchor, control-area intent, corners, edge-family approval, lane connections.
2. Extend result lineage for the new source rows.
3. Convert `Intersection` panel into staged source-completeness workflow.
4. Add Viewer and Build Parametric edit handoff targets.
5. Replace transitional Build Parametric patch paths with accepted result/output contracts.
6. Promote Watertight Solids from transitional patch body to accepted intersection zone body targets.
7. Expand presets and manual examples after schema stabilization.

## Current Next Best Task

The current validation checklist now has first-slice coverage through `INT-REM-VAL-005`, and preset review lineage is closed through `INT-REM-PRESET-005`.

The next best implementation task is manual QA execution against `docsV1/V1_INTERSECTION_MANUAL_QA.md`.

The automated implementation plan is closed. The remaining work is to execute the manual QA record in a real FreeCAD document, capture results for T, Cross, Y, Skewed, Urban Curb/Gutter, Drainage-Sensitive Sag, and Roundabout presets, and record any real-scene issues that are not reproducible through FreeCADCmd contract tests.

The completed `INT-REM-RES-002` slice added first-pass anchor topology result rows with:

- accepted anchor station and point result rows
- anchor source status and diagnostic refs
- tolerance and station mapping fields
- primary and secondary Alignment station refs where available
- topology/result lineage back to `IntersectionAnchorRow`

The completed `INT-REM-RES-003` slice tightened control-area result lineage with:

- explicit control-area intent result refs
- source vs result Region lineage
- approval/default diagnostics suitable for UI review
- stable handoff fields for clipping and surface-zone consumers

The completed `INT-REM-RES-004` slice tightened lane-connection result lineage with:

- source lane-connection refs on topology rows
- from/to leg and edge-family source status rollup
- movement type diagnostics for through, turn, merge, terminate, and default rows
- stable handoff fields for future edge-network and surface-zone consumers

The completed `INT-REM-RES-005` slice tightened grading-context source lineage with:

- explicit grading policy source refs
- controlling Profile and Superelevation source refs where available
- vertical fallback/default diagnostics
- stable handoff fields for surface-zone and drainage consumers

The completed `INT-REM-RES-006` slice tightened drainage accepted-vs-hint result status with:

- drainage policy source refs on hint rows
- accepted drainage element vs hint-only row status
- inlet/low-point handoff status for future DrainageModel consumers
- row-level source-lineage status for accepted source, incomplete source, hint-only, and source-warning cases
- drainage source-stage handoff targets for same-context edit return
- warning/default diagnostics suitable for Build Parametric and Viewer review

The completed `INT-REM-APP-001` slice tightened Applied Section active Intersection source status with:

- durable object counts for Applied Sections with active Intersection source context
- warning counts for Applied Sections whose Intersection source status still needs review
- row-level diagnostic and warning-stage counts summarized on the `V1AppliedSectionSet` object
- object contract coverage showing the summary metadata survives update and roundtrip reconstruction

The completed `INT-REM-BLD-001` slice tightened Build Parametric Intersection source-status review with:

- Slope Face Loop contract rows now consume row-level source status instead of assuming accepted source
- Slope Face Loop source diagnostics now appear in Build Parametric Intersection Contracts review
- source-lineage and consumed surface-zone warning status now appear in row notes
- focused contract coverage for Slope Face Loop source warnings and summary source-warning counts

The completed `INT-REM-WS-001` slice tightened transitional Watertight patch-body review with:

- explicit `legacy_patch_prism` transitional reason in target notes and diagnostics
- accepted zone-solid replacement family hints on `intersection_patch_body` targets
- `source_contract_required=accepted_surface_zone` review metadata
- user-facing `Intersection Patch (Transitional)` panel labels
- focused coverage for discovery, panel display, patch-body build, and accepted zone target handoff separation

The completed `INT-REM-VAL-001` slice tightened the Intersection contract-test matrix with:

- package-level validation that transitional-only `intersection_patch_body` handoff blocks final simulation readiness
- package-level validation that accepted intersection zone targets allow `accepted_zone_candidate` handoff
- source refs and material refs preserved in the accepted zone package path
- explicit guard against regressing accepted zone candidates back into transitional patch-only blockers

The completed `INT-REM-UI-001` slice started the staged source workflow with:

- a source-completeness summary for Participants, Anchor, Legs, Control Areas, Corners, Edge Families, Lane Connections, Grading, and Drainage
- visible default/draft/accepted status before preview
- no output geometry becoming editable source
- reuse of existing result diagnostics instead of new UI-only rules

The completed `INT-REM-UI-002` slice made source completeness actionable with:

- compact accepted/warning/missing counts
- stage-specific notes in the status text
- preview/apply blocking guidance for missing required stages
- smoke coverage for draft/default source stages after starter source creation

The completed `INT-REM-UI-003` slice added same-context edit return foundations with:

- stable stage ids or targets for source-completeness rows
- focus helpers that select the relevant stage row
- handoff targets that Viewer and Build Parametric can use later
- tests for opening/focusing a missing or warning source stage without editing output geometry

The completed `INT-REM-UI-004` slice added source approval states with:

- visible draft/default/accepted/locked state labels
- row-level approval summaries for preset defaults and detected rows
- source method rollups in source-completeness rows
- panel coverage that keeps status, approval, count, handoff target, and diagnostics separate

The completed `INT-REM-UI-005` slice expanded the read-only preview sequence with:

- source validation preview rows
- topology, edge network, and surface-zone preview stages
- grading, drainage, and slope-loop preview stages
- tests that preview stages consume result contracts without editing output geometry

The completed `INT-REM-APP-002` slice added Applied Sections source-stage context with:

- anchor, control-area, and edge-family source status on station rows
- named source-stage diagnostics suitable for Cross Section Viewer display
- handoff targets from station context back to the `Intersection` staged source table

The latest `INT-REM-APP-002` slice tightened Cross Section Viewer source-stage lineage by:

- adding a `Lineage` column to Intersection Context rows
- deriving `source_warning`, `source_blocked`, `accepted_source`, or `fallback` lineage from each context row status
- keeping Handoff Owner and Handoff Target column positions stable for same-context edit return
- adding focused FreeCADCmd coverage for source-stage, frame-source, and accepted surface-zone lineage rows

The latest `INT-REM-APP-003` slice tightened frame source fallback review by:

- adding `CenterlineSourceStatusCounts` to the durable `V1AppliedSectionSet` object
- preserving source-geometry and fallback frame status counts separately from frame source modes
- keeping `FrameSourceModes`, `FrameSourceStatuses`, and `FrameSourceDiagnosticRows` as the row-level contract
- adding focused FreeCADCmd coverage for source-geometry and fallback frame status summaries

The latest `INT-REM-APP-004` slice tightened Cross Section Viewer handoff routing by:

- deriving handoff summary rows from Intersection Context owner/target fields
- preserving source-stage, frame-source, and Build Parametric targets in the same station handoff table
- carrying lineage status into each derived handoff row context
- adding focused FreeCADCmd coverage for Intersection, Applied Sections, and Build Parametric handoff targets

The latest `INT-REM-UI-001..005` audit slice closed the staged Intersection panel phase by:

- rerunning source-completeness row coverage for staged source workflow
- rerunning read-only preview sequence coverage for result-contract preview rows
- rerunning panel smoke coverage for source tables, approval states, handoff targets, and focus helpers
- confirming the staged panel still exposes warning/default rows without applying output geometry

The latest `INT-REM-SRC-001..008` and `INT-REM-RES-001..006` audit slice closed the source/result contract phases by:

- rerunning the core result-row source status contract test
- rerunning topology source-completeness and source-blocking coverage
- rerunning edge-family, lane-connection, grading, drainage, and slope-loop lineage coverage
- confirming source diagnostics and source-lineage metadata remain available before downstream preview, build, and handoff

The latest `INT-REM-VAL-001..005` audit slice closed the automated validation phase by:

- rerunning transitional-only Intersection package blocker coverage
- rerunning source object roundtrip and `.FCStd` reopen coverage
- rerunning staged panel smoke coverage
- rerunning Lane/Shoulder/Side Slope no-stitch regression coverage
- confirming manual QA records exist for preset execution and original stitching regression, with real FreeCAD document execution still tracked separately

The completed `INT-REM-APP-003` slice added sparse station frame fallback status with:

- explicit frame source mode on Applied Section station rows
- fallback or interpolation diagnostics when source-geometry 3D Centerline frames are unavailable
- Cross Section Viewer display rows that distinguish source-geometry frames from fallback frames

The completed `INT-REM-APP-004` slice added edit handoff targets to Intersection Context rows with:

- stable target ids for Intersection source stages, Applied Sections, and Build Parametric review rows
- Viewer rows that can route the user to the owning review/editor surface
- tests that missing-source rows expose the intended handoff target without editing generated geometry

The completed `INT-REM-BLD-002` first slice labeled Build Parametric output helper paths with:

- explicit `contract_consumed`, `inferred_fallback`, or `legacy_output` path labels
- Output Path columns in Guided Review, Output Review, and Intersection Contracts
- `legacy_output` on the current Intersection Surface patch path
- `contract_consumed` counts on Intersection Contracts rows and summaries
- focused tests that patch and fallback output review does not present generated geometry as accepted source intent

The latest `INT-REM-BLD-002` slice tightened missing-source output-path labels by:

- changing missing Intersection Contract rows from `contract_consumed` to `missing_source`
- adding `output paths=missing_source=1` to the missing contract summary
- preserving `contract_consumed` summaries for evaluated Intersection Contract rows
- adding focused FreeCADCmd coverage for missing-source and normal contract output-path labels

The completed `INT-REM-BLD-003` first slice moved Build Parametric output toward accepted result contracts with:

- consumed topology, edge-network, surface-zone, grading-context, drainage-hint, and slope-loop result ids on Intersection Surface previews
- consumed slope-loop result ids on Intersection Slope Face Surface previews
- a `ConsumedIntersectionContractSummary` review note for Build Parametric output rows
- focused tests showing Intersection Surface and Slope Face output previews preserve consumed result contract refs

The completed `INT-REM-BLD-004` first slice added a dedicated `Intersection Surface Patch` result contract with:

- `IntersectionSurfacePatchResult`
- normalized boundary, triangulation, and quality rows
- preview metadata for result id, status, output path, row counts, consumed refs, diagnostics, and summary
- review notes that expose the patch result contract without treating the legacy patch mesh as source intent
- row-level Surface Patch boundary, triangulation, and quality result refs/statuses on the preview object
- row-level Surface Patch diagnostics preserved separately from legacy patch quality properties
- focused FreeCADCmd coverage for row-level Surface Patch result metadata

The completed `INT-REM-BLD-005` first slice tightened the slope-face boundary-first rule with:

- boundary result id, status, counts, refs, diagnostics, and summary on `Intersection Slope Face Boundary` previews
- boundary result metadata on generated Slope Face strip TIN quality rows
- Build Parametric review notes that expose the consumed slope-face boundary result
- focused tests for boundary-result metadata on generated Slope Face strips

The completed `INT-REM-WS-002` first slice added accepted intersection zone target handoff metadata with:

- pavement, subgrade, slope, and curb-return intersection zone target rows
- source refs for consumed edge-network and surface-zone result contracts
- `contract_status=accepted_surface_zone`
- `quality_status=accepted_contract_pending_builder`
- `digital_twin_handoff=accepted_zone_candidate`
- focused Watertight target discovery coverage for accepted zone lineage

The latest `INT-REM-WS-002` slice made accepted zone target builder state explicit by:

- adding `builder_state=pending_accepted_zone_solid_builder` to accepted zone target notes
- keeping `build_backend=planned_edge_network_zone_solid` as the planned backend label
- preserving accepted Surface Zone / Edge Network lineage beside the pending-builder state
- adding focused FreeCADCmd coverage for accepted zone builder-state metadata

The completed `INT-REM-WS-003` first slice blocked final Digital Twin handoff on transitional-only patch solids with:

- detecting when an intersection package has only `intersection_patch_body` transitional targets
- keeping review/package export explicit about `review_required`
- persisted `SimulationPackageOutput` fields for intersection handoff readiness, final-quality status, handoff status, and target counts
- package-level `intersection_final_handoff_blocked` diagnostics when QA is otherwise ready but Intersection handoff is transitional-only
- allowing accepted zone targets to satisfy the final-quality path when available

The completed `INT-REM-WS-004` first slice added intersection trim/fuse handoff status to Simulation QA with:

- summarizing trim-boundary pair readiness in the Simulation QA report
- exposing patch-to-road body gap, trim candidate, and fuse candidate status in QA diagnostics
- distinguishing accepted trim/fuse handoff from transitional or fallback geometry
- persisted `V1SimulationQaOutput` fields for trim status, fuse status, handoff status, ready/blocked pair counts, and maximum XY gap
- focused trim/fuse contract coverage for QA object roundtrip

The completed `INT-REM-WS-005` first slice preserved source lineage in solid output and exchange rows with:

- row-level `source_refs`, `material_ref`, and notes persisted on `V1WatertightSolidOutput`
- row-level source/material refs propagated into `SimulationPackageOutput`
- package JSON `solid_rows` exporting source and material refs
- Exchange source-context rows carrying station span, material, source refs, and structured Intersection refs for intersection, surface zone, edge network, and surface-zone result lineage
- focused roundtrip, package export, and exchange mapper coverage

The completed `INT-REM-PRESET-001` first slice upgraded T and Cross presets with source-completeness status by:

- ensuring starter sources populate source status for anchor, control area, edge family, lane connection, grading, and drainage rows
- keeping default/draft rows explicit instead of silently accepted
- adding preset-focused contract coverage for source-completeness review
- preserving `IntersectionModel.source_refs` through the FreeCAD source object roundtrip
- marking preset default/draft rows with review-required diagnostics for Anchor, Control Areas, Corners, Edge Families, Lane Connections, Grading, and Drainage

The latest `INT-REM-PRESET-001` slice tightened preset source-completeness lineage by:

- adding `source_completeness_ref=intersection-preset:<kind>:source-completeness` to preset-authored row notes
- preserving that ref on T Intersection and Cross Intersection default/draft rows
- keeping row-level review-required diagnostics tied back to the preset source-completeness audit ref
- adding focused FreeCADCmd coverage for T/Cross source-completeness note lineage

The completed `INT-REM-PRESET-002` first slice added a source-driven Y Intersection starter by:

- exposing `Y Intersection - Basic` in the Intersection preset panel
- creating primary approach, left branch, and right branch starter Alignment and Region sources
- preserving both branch Alignment refs on the Intersection source row
- creating Y-specific branch corner and diverge/merge lane-connection defaults
- adding review-required diagnostics for branch geometry and diverge/merge movement review

The latest `INT-REM-PRESET-002` slice tightened Y branch review lineage by:

- adding `branch_review_ref=intersection-preset:y_intersection:branch-review` to Y preset branch notes
- preserving the branch review ref on the Intersection row, branch corner rows, and diverge/merge lane-connection rows
- keeping `source_completeness_ref=intersection-preset:y_intersection:source-completeness` visible beside the branch review ref
- adding focused FreeCADCmd coverage for Y branch review note lineage

The completed `INT-REM-PRESET-003` first slice added a source-driven skewed intersection starter by:

- exposing `Skewed Intersection - Basic` in the Intersection preset panel
- adding `skewed_intersection` as a supported source kind
- creating non-orthogonal primary and secondary starter Alignment sources
- preserving skew corner and edge-family defaults as review-required source diagnostics
- proving the skewed starter remains source/result driven without downstream mesh repair

The latest `INT-REM-PRESET-003` slice tightened skew review lineage by:

- adding `skew_review_ref=intersection-preset:skewed_intersection:skew-review` to skew preset review notes
- preserving the skew review ref on the Intersection row, skew corner rows, and skew edge-family rows
- keeping `source_completeness_ref=intersection-preset:skewed_intersection:source-completeness` visible beside the skew review ref
- adding focused FreeCADCmd coverage for skew review note lineage

The completed `INT-REM-PRESET-004` first slice added a source-driven urban curb/gutter starter by:

- exposing `Urban Curb/Gutter - Basic` in the Intersection preset panel
- adding `urban_curb_gutter_intersection` as a supported source kind
- creating urban main/side street starter Alignment and Region sources
- adding curb, gutter, and sidewalk `IntersectionEdgePolicyRow` source defaults
- adding gutter edge refs, inlet candidate refs, low-point refs, and inlet candidate Drainage rows
- preserving edge-family and drainage diagnostics until real drainage design replaces the starter hints

The latest `INT-REM-PRESET-004` slice tightened urban curb/gutter review lineage by:

- adding `urban_review_ref=intersection-preset:urban_curb_gutter_intersection:urban-curb-gutter-review` to urban preset review notes
- preserving the urban review ref on the Intersection row, curb/gutter/sidewalk edge rows, and drainage policy row
- keeping `source_completeness_ref=intersection-preset:urban_curb_gutter_intersection:source-completeness` visible beside the urban review ref
- adding focused FreeCADCmd coverage for urban review note lineage

The completed `INT-REM-PRESET-005` first slice added a source-driven drainage-sensitive sag starter by:

- exposing `Drainage-Sensitive Sag - Basic` in the Intersection preset panel
- adding `drainage_sag_intersection` as a supported source kind
- creating sag main/side road starter Alignment, Profile, Stationing, and Region sources
- setting starter Profile middle controls to `sag_low_point`
- adding low-point refs, inlet candidate refs, flow-route refs, and critical DrainageModel handoff rows
- preserving review diagnostics for inlet placement, hydraulic sizing, and outlet replacement

The latest `INT-REM-PRESET-005` slice tightened sag drainage review lineage by:

- adding `sag_review_ref=intersection-preset:drainage_sag_intersection:sag-drainage-review` to sag preset review notes
- preserving the sag review ref on the Intersection row, grading policy row, and drainage policy row
- keeping `source_completeness_ref=intersection-preset:drainage_sag_intersection:source-completeness` visible beside the sag review ref
- adding focused FreeCADCmd coverage for sag review note lineage

The completed `INT-REM-VAL-002` first slice strengthened source object persistence coverage by:

- adding `.FCStd` save/reopen coverage for `V1IntersectionModel`
- verifying anchor approval/status and station mapping survive reload
- verifying corner, lane-connection, edge-family, grading, and drainage diagnostics survive reload
- verifying sag/urban-style drainage refs, inlet spacing, low-point refs, and flow-route refs survive reload
- verifying topology, drainage-hint, and surface-zone result refs survive object roundtrip and document reload

The completed `INT-REM-VAL-003` first slice strengthened panel smoke coverage by:

- checking staged source completeness construction for preset-created warning rows
- verifying warning/draft stage rows for Anchor, Corners, Edge Families, Lane Connections, Grading, and Drainage
- verifying source-stage focus for the Drainage handoff target
- confirming no `IntersectionModel` output/source object is applied during the panel smoke test
- verifying row-level Anchor, Lane Connection, Drainage, Grading, and Slope Loop handoff/source-lineage metadata remains visible in read-only panel stages

The completed `INT-REM-VAL-004` first slice added manual QA records by:

- documenting expected source, preview, Build Parametric, and Watertight status for T, Cross, Skewed, Urban, Sag, Y, and Roundabout presets
- adding a pending manual execution record table for all seven presets
- adding detailed Skewed, Urban Curb/Gutter, and Drainage-Sensitive Sag manual QA procedures
- keeping known warning/default diagnostics visible in the QA notes
- adding source handoff target and preview lineage fields to the manual execution record
- documenting row-level Anchor, Lane Connection, Drainage, Grading, and Slope Loop handoff/source-lineage checks

The completed `INT-REM-VAL-005` first slice added regression QA for the original stitched Lane/Shoulder/Side Slope problem by:

- recording a repeatable source-driven preset workflow that used to stitch unrelated alignment scopes
- checking ordinary and intersection Slope Face output families separately
- confirming Lane, Shoulder, and Side Slope review geometry remains scoped by source Alignment and control Region
- requiring Build Parametric `source_status`, source diagnostics, `source_lineage=...`, and `surface_zone_status=...` notes to remain visible for regression review
- extending the regression record table with lineage results and Build Parametric notes checked columns

The latest `INT-REM-SRC-001` slice tightened Anchor source validation by:

- defining accepted Anchor source methods and approval statuses in topology evaluation
- warning on unknown source methods such as generated mesh repair labels
- warning on unknown approval statuses instead of treating them as accepted source intent
- adding contract coverage for invalid Anchor source method and approval status diagnostics
- preserving missing primary Alignment refs as row-level `error` source/status, not only topology-level diagnostics

The latest `INT-REM-SRC-002` slice tightened Leg source validation by:

- defining accepted Leg source methods, approval statuses, and span sources in topology evaluation
- warning on unknown source methods such as generated mesh repair labels
- warning on unknown approval statuses instead of treating them as accepted source intent
- warning on unknown span sources instead of treating mesh extents as accepted leg source spans
- adding contract coverage for invalid Leg source method, approval status, and span-source diagnostics
- preserving missing Leg Alignment refs as row-level `error` source/status, not only topology-level diagnostics

The latest `INT-REM-SRC-003` slice tightened Control Area source validation by:

- defining accepted Control Area source methods, approval statuses, and intent statuses in topology evaluation
- warning on unknown source methods such as generated mesh repair labels
- warning on unknown approval statuses instead of treating them as accepted source intent
- warning on unknown intent statuses with stable `source_control_area_intent_unknown` diagnostics
- adding contract coverage for invalid Control Area source method, approval status, and intent-status diagnostics
- preserving missing Control Area Alignment refs and station ranges as row-level `error` source/status, not only topology-level diagnostics

The latest `INT-REM-SRC-004` slice tightened Corner source validation by:

- defining accepted Corner source methods and approval statuses in edge-network evaluation
- warning on unknown source methods such as generated mesh repair labels
- warning on unknown approval statuses instead of treating them as accepted curb-return intent
- warning when named corners lack control-area refs, side/quadrant refs, or matching curb-return policy refs
- adding contract coverage that curb-return edge rows preserve corner source diagnostics
- preserving missing Corner control-area, leg, side/quadrant, and curb-return policy context as row-level `error` source/status and edge-network `error` diagnostics

The latest `INT-REM-SRC-005` slice tightened Edge Family source validation by:

- defining accepted Edge Family source methods, approval statuses, and family intents in edge-network and lane-connection lineage evaluation
- warning on unknown edge-family intents instead of accepting mesh patch labels as source intent
- warning on unknown source methods and approval statuses
- warning when Subassembly-derived edge policies lack source policy refs or have mismatched Subassembly kind and edge-family intent
- adding contract coverage for both edge-network rows and lane-connection edge-family lineage diagnostics
- preserving Subassembly lineage breaks as row-level `error` source/status and edge-network `error` diagnostics
- propagating Edge Family `error` status into Lane Connection edge handoff as `incomplete`

The latest `INT-REM-SRC-006` slice tightened Lane Connection source validation by:

- defining accepted movement types, source methods, and approval statuses in topology evaluation
- warning on unknown movement types instead of accepting mesh patch labels as source movement intent
- warning on unknown source methods and approval statuses
- warning when from/to edge-policy refs are missing or unresolved
- adding contract coverage for invalid Lane Connection source method, approval status, movement type, and edge-policy refs
- preserving missing/unresolved Lane Connection leg refs and edge-policy refs as row-level `error` source/status and topology `error` diagnostics
- propagating upstream Edge Family `error` status into Lane Connection source/status and edge handoff

The latest `INT-REM-SRC-007` slice tightened Grading Policy source validation by:

- defining accepted grading modes, source methods, approval statuses, crown behaviors, tie-in rules, crossfall transitions, and low-point strategies
- warning on unknown grading modes instead of accepting mesh patch labels as source grading intent
- warning on unknown source methods and approval statuses
- warning on unknown crown, tie-in, crossfall, and low-point strategy values
- adding contract coverage for invalid Grading Policy values in grading-context result rows
- preserving missing controlling Profile refs for intersection-override grading as row-level `error` source/status with blocked profile and vertical handoff status

The latest `INT-REM-SRC-008` slice tightened Drainage Policy source validation by:

- defining accepted capture modes, intent statuses, source methods, and approval statuses
- warning on unknown capture modes instead of accepting mesh gutter labels as source drainage intent
- warning on unknown intent statuses, source methods, and approval statuses
- preserving review-required handoff status for invalid drainage policy labels
- adding contract coverage for invalid Drainage Policy values in drainage-hint result rows
- preserving accepted/source-owned Drainage intent that lacks drainage element refs or flow route refs as row-level `error` source/status with `accepted_source_incomplete` handoff

The latest `INT-REM-RES-001` slice tightened row-level result lineage by:

- adding source status, source diagnostics, source surface-zone status, and source lineage status to Slope Face loop result rows
- carrying consumed surface-zone source diagnostics into Slope Face loop rows without mixing them into loop geometry diagnostics
- making Slope Face loop row readiness warn when source lineage is warning or missing
- adding contract coverage that preset-created Slope Face loops preserve surface-zone and edge-network source refs
- adding source edge-network status to Slope Face loop result rows
- carrying consumed Edge Network row source diagnostics into Slope Face loop source diagnostics
- preserving consumed Edge Network source errors as Slope Face loop `source_error` lineage and row-level `error` status
- adding focused contract coverage for Edge Network source-error propagation into Slope Face loops

The latest `INT-REM-RES-002` slice tightened Anchor result lineage by:

- adding station lineage status to Anchor topology result rows
- adding same-context source-stage handoff targets to Anchor topology result rows
- preserving accepted vs warning station mapping status for primary and secondary Alignment refs
- allowing existing `subassembly_derived` edge-family source lineage while keeping stricter `subassembly_bridge` source-policy-ref diagnostics
- adding contract coverage for accepted and warning Anchor result handoff fields

The latest `INT-REM-RES-003` slice tightened Control Area result lineage by:

- adding Region handoff status to Control Area topology result rows
- adding clipping handoff status to Control Area topology result rows
- adding same-context source-stage handoff targets to Control Area topology result rows
- preserving Region lineage and clipping boundary readiness separately from source diagnostics
- adding contract coverage for warning and topology sample Control Area result handoff fields

The latest `INT-REM-RES-004` slice tightened Lane Connection result lineage by:

- adding leg handoff status to Lane Connection topology result rows
- adding edge handoff status to Lane Connection topology result rows
- adding same-context source-stage handoff targets to Lane Connection topology result rows
- preserving movement lineage, leg source status, and edge-family status as separate review fields
- adding contract coverage for incomplete and warning Lane Connection result handoff fields

The latest `INT-REM-RES-005` slice tightened Grading Context result lineage by:

- adding Profile handoff status to Grading Context result rows
- adding Superelevation handoff status to Grading Context result rows
- adding grading review handoff targets to Grading Context result rows
- preserving profile lineage, superelevation source status, vertical handoff, and fallback status as separate review fields
- adding contract coverage for accepted and warning Grading Context result handoff fields

The latest `INT-REM-RES-006` slice tightened Drainage Hint result lineage by:

- adding source-lineage status to Drainage Hint result rows
- adding drainage source-stage handoff targets to Drainage Hint result rows
- preserving accepted source-owned drainage rows separately from hint-only and source-warning rows
- adding contract coverage for accepted, hint-only, invalid source-policy, and roundabout outlet handoff rows

The latest `INT-REM-APP-001` slice tightened Applied Section active Intersection source status by:

- adding `IntersectionSourceSectionCount`, `IntersectionSourceWarningCount`, `IntersectionSourceDiagnosticCount`, `IntersectionSourceStatusCounts`, and `IntersectionSourceSummary` to `V1AppliedSectionSet`
- keeping the summary as durable review metadata derived from result rows, not editable source intent
- adding object contract coverage for warning Intersection source rows and source-stage diagnostics

The latest `INT-REM-BLD-001` slice tightened Build Parametric Intersection source-status review by:

- carrying `IntersectionSlopeFaceLoopRow.source_status` into Intersection Contracts rows
- carrying Slope Face Loop source diagnostics into the `Source Diagnostics` column
- showing source lineage and consumed surface-zone warning status in Build Parametric row notes
- adding focused FreeCADCmd coverage for source-warning Slope Face Loop rows

The latest `INT-REM-WS-001` slice tightened transitional Watertight patch-body review by:

- adding `transitional_reason=legacy_patch_prism` to `intersection_patch_body` target notes and diagnostics
- adding accepted intersection zone replacement target families to the transitional patch-body notes
- adding `source_contract_required=accepted_surface_zone` to make the required source/result handoff explicit
- adding `replacement_guidance=accepted_zone_solids_required` to the transitional target notes and diagnostics
- labeling the target as `Intersection Patch (Transitional)` in the Watertight Solids panel
- adding focused FreeCADCmd coverage for transitional patch-body discovery and build target guidance

The latest `INT-REM-VAL-001` slice tightened the Intersection contract-test matrix by:

- adding final handoff package coverage for blocked transitional-only patch solids
- adding final handoff package coverage for allowed accepted intersection zone candidates
- verifying accepted zone package source refs and material refs remain visible

The latest `INT-REM-VAL-002` slice tightened source object result-ref persistence by:

- adding `IntersectionModel.result_refs` to the durable source contract
- restoring `ResultRefs` from `V1IntersectionModel` objects back into `IntersectionModel`
- verifying topology, drainage-hint, and surface-zone result refs survive direct object roundtrip
- verifying the same result refs survive `.FCStd` save/reopen

The latest `INT-REM-VAL-003` slice tightened panel staged source metadata by:

- adding row-level `handoff_target` diagnostics to result-backed source stages
- adding `source_lineage_status` diagnostics where result rows expose lineage state
- exposing Grading, Drainage, and Slope Loop handoff/source-lineage metadata in read-only preview stages
- extending the panel smoke test to verify the metadata without applying output geometry

The latest `INT-REM-VAL-004` slice tightened manual QA records by:

- adding source handoff target and preview lineage columns to the preset execution table
- adding a dedicated Source Handoff And Lineage Checks table
- requiring staged source handoff target checks before Build Sections or Build Parametric review
- requiring Drainage, Grading, and Slope Loop lineage checks in detailed preset procedures

The latest `INT-REM-VAL-005` slice tightened stitching regression QA by:

- adding Build Parametric source-status and source-diagnostics checks to the Lane/Shoulder/Side Slope regression setup
- requiring Lane, Shoulder, and Side Slope rows to record source Alignment, control Region, source status, diagnostics, and responsibility
- requiring warning `slope_face_loop` rows to preserve `source_lineage=...` and `surface_zone_status=...` notes
- extending the regression record table with lineage result and Build Parametric notes columns

The latest `INT-REM-SRC-001` slice tightened Anchor source blocking status by:

- deriving Anchor row source/status severity from source diagnostics
- preserving missing primary Alignment refs as row-level `error`
- keeping unknown Anchor source methods and approval statuses as `warning`
- adding focused contract coverage for the row-level missing-primary error path

The latest `INT-REM-SRC-002` slice tightened Leg source blocking status by:

- deriving Leg row source/status severity from source diagnostics
- preserving missing Alignment refs as row-level `error`
- keeping unknown Leg source methods, approval statuses, and span sources as `warning`
- adding focused contract coverage for the row-level missing-Alignment error path

The latest `INT-REM-SRC-003` slice tightened Control Area source blocking status by:

- deriving Control Area row source/status severity from source diagnostics
- preserving missing Alignment refs and missing station ranges as row-level `error`
- keeping unknown Control Area source methods, approval statuses, and intent statuses as `warning`
- adding focused contract coverage for the row-level missing Alignment/station range error path

The latest `INT-REM-SRC-004` slice tightened Corner source blocking status by:

- deriving curb-return edge row source/status severity from Corner source diagnostics
- preserving missing Corner control-area, leg, side/quadrant, and curb-return policy context as row-level `error`
- keeping unknown Corner source methods and approval statuses as `warning`
- adding focused contract coverage for the row-level Corner blocking error path

The latest `INT-REM-SRC-005` slice tightened Edge Family source blocking status by:

- deriving Edge Family row source/status severity from source diagnostics
- preserving missing Subassembly source policy refs, missing Subassembly kind, and Subassembly kind mismatches as row-level `error`
- propagating Edge Family `error` status into Lane Connection edge handoff as `incomplete`
- keeping unknown edge-family intent, source method, and approval status as `warning`
- adding focused contract coverage for edge-network and Lane Connection lineage error paths

The latest `INT-REM-SRC-006` slice tightened Lane Connection source blocking status by:

- deriving Lane Connection row source/status severity from source diagnostics
- preserving missing or unresolved from/to leg refs and edge-policy refs as row-level `error`
- propagating upstream Leg or Edge Family `error` status into Lane Connection source/status and handoff fields
- keeping unknown movement types, source methods, and approval statuses as `warning`
- adding focused contract coverage for edge-family and missing-edge-policy source-blocking paths

The latest `INT-REM-SRC-007` slice tightened Grading Policy source blocking status by:

- deriving Grading Context row source/status severity from vertical handoff state
- preserving missing controlling Profile refs for intersection-override grading as row-level `error`
- marking profile and vertical handoff as `blocked` when override grading has no controlling Profile
- keeping unknown grading values, source methods, and approval statuses as `warning`
- adding focused contract coverage for the missing controlling Profile error path

The latest `INT-REM-SRC-008` slice tightened Drainage Policy source blocking status by:

- deriving Drainage Hint row source/status severity from Drainage handoff state
- preserving accepted/source-owned intent without drainage element refs or flow route refs as row-level `error`
- marking incomplete accepted drainage source as `accepted_source_incomplete` with `source_incomplete` lineage
- keeping unknown drainage capture, intent, source method, and approval labels as `warning`
- adding focused contract coverage for accepted drainage source missing accepted refs

The latest `INT-REM-RES-001` slice tightened Slope Face Loop edge-network lineage by:

- adding `source_edge_network_status` to Slope Face loop result rows
- deriving loop source lineage from both consumed Surface Zone rows and consumed Edge Network rows
- carrying Edge Network source diagnostics into loop source diagnostics with the consumed edge ref
- preserving consumed Edge Network source errors as Slope Face loop `source_error` lineage and row-level `error` status
- adding focused FreeCADCmd coverage for edge-network source-error propagation into Slope Face loops

The latest `INT-REM-RES-001` audit slice locked the core result-row source contract by:

- adding focused contract coverage that topology, edge-network, surface-zone, corridor-clip, grading-context, drainage-hint, and slope-face-loop rows all expose `source_status`
- adding focused contract coverage that the same core result rows all expose `source_diagnostic_rows`
- keeping patch boundary, tie-in edge, surface patch, slope-face boundary, and trim helper contracts documented as output/result-only helpers rather than source-intent rows

The latest planning audit advanced the current next task from `INT-REM-RES-001` to `INT-REM-BLD-004` because:

- core Intersection result rows now expose source status and diagnostics through contract tests
- Slope Face Loop lineage is preserved through result rows, Build Parametric review rows, and output preview metadata
- Applied Section frame source status, Viewer `frame_source` rows, and Intersection Context handoff targets are already implemented and covered
- the remaining higher-impact gap is replacing legacy Intersection Surface Patch output metadata with accepted result/output contracts

The latest `INT-REM-BLD-004` slice tightened Surface Patch result metadata by:

- exposing boundary, triangulation, and quality row refs on `V1CorridorIntersectionSurfacePreview`
- exposing boundary, triangulation, and quality row statuses on `V1CorridorIntersectionSurfacePreview`
- preserving row-level Surface Patch diagnostics on `IntersectionSurfacePatchRowDiagnostics`
- adding focused FreeCADCmd coverage for normalized Surface Patch row metadata

The latest `INT-REM-BLD-004` slice shifted Build Parametric review notes toward normalized Surface Patch rows by:

- adding `surface_patch_rows=boundary=..., triangulation=..., quality=...` review notes
- adding `surface_patch_row_diagnostics=...` review notes
- removing duplicate legacy patch detail counts from Intersection Surface review notes where normalized row metadata now carries the same review intent
- keeping detailed legacy patch properties available on the preview object for focused diagnostics
- adding focused FreeCADCmd coverage for normalized Surface Patch review notes

The latest `INT-REM-BLD-004` cleanup removed the obsolete `IntersectionPatchQualitySummary` preview property because:

- `IntersectionSurfacePatchSummary` now carries normalized boundary, triangulation, and quality result-row summaries
- Surface Patch row refs, statuses, and diagnostics are stored as dedicated preview metadata
- no runtime consumer needed the legacy combined quality summary

The latest `INT-REM-BLD-004` cleanup refocused Guided Review and Build Parametric notes by:

- showing normalized `IntersectionSurfacePatchSummary` and `surface_patch_rows=...` before legacy patch metrics
- counting `IntersectionSurfacePatchRowDiagnostics` as the primary Surface Patch warning signal
- removing duplicate structured strip, curb-return surface edge, arc sample, arc segment, and edge blend face counts from general review notes
- keeping fallback triangulation, elongated boundary, low triangle quality, skinny triangle, and long-edge warnings as focused diagnostics

The latest `INT-REM-BLD-004` slice made the Surface Patch output contract handoff state explicit by:

- adding `output_contract_status=transitional_normalized` to `IntersectionSurfacePatchResult`
- adding `digital_twin_handoff=review_required` and `transitional_reason=legacy_patch_surface_output`
- exposing `IntersectionSurfacePatchOutputContractStatus`, `IntersectionSurfacePatchDigitalTwinHandoff`, `IntersectionSurfacePatchTransitionalReason`, and `IntersectionSurfacePatchReplacementPath` on the preview object
- showing the transitional handoff state in Build Parametric review notes and Guided Review

The latest `INT-REM-BLD-004` slice added the first accepted Intersection Surface Zone output row family by:

- adding `IntersectionSurfaceZoneOutput` and `IntersectionSurfaceZoneOutputRow` to normalized surface output contracts
- consuming `IntersectionSurfaceZoneResult` and `IntersectionEdgeNetworkResult` directly
- exposing output row refs, row statuses, row diagnostics, contract status, and Digital Twin handoff status on `V1CorridorIntersectionSurfacePreview`
- marking the rows `contract_status=accepted_surface_zone` and `digital_twin_handoff=accepted_zone_candidate`
- keeping the build backend explicit as `planned_edge_network_zone_surface` until real accepted zone-surface geometry replaces the transitional patch surface

The latest `INT-REM-BLD-004` slice added the first non-patch accepted Surface Zone output preview by:

- creating `V1CorridorIntersectionSurfaceZoneOutputPreview` from accepted Surface Zone output rows
- drawing the Edge Network linework referenced by those output rows instead of reading the transitional patch mesh
- marking the preview `PreviewSource=accepted_surface_zone_output`
- linking the preview from `V1CorridorIntersectionSurfacePreview` through `IntersectionSurfaceZoneOutputPreviewRef`
- adding focused FreeCADCmd coverage for the accepted Surface Zone output preview

The latest `INT-REM-BLD-004` slice expanded accepted Surface Zone output into a first zone-surface builder path by:

- initially building `V1CorridorIntersectionSurfaceZoneSurfacePreview` as a TIN surface from accepted Surface Zone output rows
- using Edge Network start/end points referenced by each output row instead of the transitional patch mesh
- storing `IntersectionSurfaceZoneSurfacePreviewRef` on `V1CorridorIntersectionSurfacePreview`
- preserving surface id, vertex count, triangle count, and output-row refs on the accepted zone-surface preview
- adding focused FreeCADCmd coverage for the accepted zone-surface preview

Follow-up manual QA removed the visible `V1CorridorIntersectionSurfaceZoneSurfacePreview` object from Build Parametric output.

The removed preview could fan-triangulate edge strips away from the actual intersection control area.

Follow-up manual QA also removed the visible `V1CorridorIntersectionSurfaceZoneOutputPreview` linework object from Build Parametric output.

The linework preview could expose accepted Surface Zone edge rows away from the actual intersection control area.

The normalized `IntersectionSurfaceZoneOutput` contract remains active on the main Intersection preview; the misleading linework and TIN presentation artifacts are suppressed.

The latest `INT-REM-BLD-004` slice tightened accepted Surface Zone output row lineage by:

- preserving `inner_edge_refs`, `outer_edge_refs`, and `tie_edge_refs` from `IntersectionSurfaceZoneResult`
- preserving `leg_refs`, `alignment_refs`, `control_area_refs`, and `vertical_policy_ref`
- exposing `IntersectionSurfaceZoneOutputRowLineage` on the main Intersection preview, accepted zone output preview, and accepted zone-surface preview
- adding leg, alignment, and control-area lineage counts to `IntersectionSurfaceZoneOutputSummary`
- adding focused FreeCADCmd coverage for accepted Surface Zone output lineage metadata

The latest `INT-REM-BLD-004` slice moved accepted Surface Zone lineage into Build Parametric review by:

- consuming `IntersectionSurfaceZoneOutputRowLineage` from the accepted zone output preview
- exposing accepted Surface Zone lineage through the main Intersection and output-preview metadata
- keeping review-panel lineage tied to the normalized accepted Surface Zone output row contract instead of legacy patch preview properties
- adding focused FreeCADCmd coverage for accepted Surface Zone review lineage notes

The final `INT-REM-BLD-004` slice closed the Surface Patch footprint acceptance gap by:

- exposing `IntersectionSurfacePatchFootprintSummary` from normalized boundary and triangulation rows
- summarizing boundary point/ring/area/bbox metadata as the patch footprint
- summarizing curb-return edges/arcs/samples and pavement/stem tie-in edge counts from the triangulation row
- adding the footprint summary to `IntersectionReviewSummary`
- adding focused FreeCADCmd coverage for the normalized footprint summary

The latest `INT-REM-BLD-004` slice added the replacement review gate between transitional patch output and accepted zone-surface output by:

- storing `IntersectionSurfaceReplacementGateStatus=blocked` while the accepted zone-surface TIN preview is suppressed
- storing patch triangle count, zero visible zone-surface triangle/vertex counts, output-row count, triangle delta, and triangle ratio
- preserving `IntersectionSurfaceReplacementDiagnostics` that state the patch is transitional and the zone output is an accepted candidate
- exposing `surface_replacement=...` and `surface_replacement_gate=blocked` in Build Parametric review notes and Guided Review
- adding focused FreeCADCmd coverage for the replacement gate metadata

The latest `INT-REM-BLD-004` slice separated transitional and accepted intersection outputs in Build Parametric review by:

- keeping accepted Surface Zone output metadata available without creating a separate `intersection_zone_surface` TIN review row
- leaving `Intersection Surface` as the transitional `legacy_output` patch row
- returning no visibility target for `intersection_zone_surface`
- adding focused FreeCADCmd coverage that the misleading zone-surface TIN object is absent

The latest `INT-REM-BLD-004` slice promoted the accepted zone-surface path as the preferred intersection review target by:

- keeping ordinary Build Parametric default focus on Design Surface
- keeping `preferred_corridor_build_review_row_index(..., preferred_role="intersection")` from selecting the suppressed zone-surface TIN row
- making Guided Review `intersections` focus return `V1CorridorIntersectionSurfacePreview`
- keeping the transitional patch row visible as fallback review context
- adding focused FreeCADCmd coverage for the preferred intersection review target

The latest `INT-REM-BLD-004` slice added an explicit replacement-readiness review row by:

- adding a dynamic `intersection_replacement_readiness` output review row when `IntersectionSurfaceReplacementGateStatus` exists
- showing `Intersection Replacement Readiness` as `output_path=review_gate`
- reporting whether the accepted zone-surface path is still `review_only`, `ready_to_replace`, or `blocked`
- carrying patch triangles, zone-surface triangles, triangle delta, ratio, recommendation, and diagnostic count in review notes
- adding focused FreeCADCmd coverage for the replacement-readiness review row

The latest `INT-REM-BLD-004` slice wired replacement-readiness into downstream handoff labels by:

- copying replacement gate status and readiness from the transitional patch preview to accepted zone output previews
- marking the transitional patch handoff as `fallback_review_required` while the gate remains review-only
- marking the accepted zone-surface handoff as `preferred_candidate_review_only`
- exposing readiness, gate, handoff preference, and recommendation in the accepted zone-surface Build Parametric review row
- adding focused FreeCADCmd coverage for the replacement handoff metadata

The latest `INT-REM-BLD-004` slice added the first readiness-driven downstream handoff selection rule by:

- selecting the transitional patch preview as `transitional_patch_fallback` while readiness is `review_only` or `blocked`
- keeping accepted zone output previews unselected while the gate remains review-only
- preparing the same metadata to select `accepted_zone_surface` once readiness becomes `ready_to_replace`
- exposing selected ref, selected role, selected flag, and selection reason on both patch and accepted zone previews
- adding selected handoff notes to the accepted zone-surface Build Parametric review row
- adding focused FreeCADCmd coverage for the downstream handoff selection metadata

The latest `INT-REM-BLD-004` slice extracted replacement readiness into a reusable output decision contract by:

- adding `IntersectionSurfaceReplacementDecision` to the surface output contract layer
- adding pure helpers for replacement readiness, handoff preference, and downstream handoff selection
- exporting those helpers through `models/output/__init__.py`
- replacing command-local readiness and preference logic with the output contract helper
- adding focused FreeCADCmd coverage for `review_required`, `ready_to_replace`, and `blocked` decisions without requiring FreeCAD document objects

The latest `INT-REM-BLD-004` slice added explicit replacement acceptance diagnostics by:

- storing `IntersectionSurfaceReplacementAcceptanceDiagnostics` on the transitional patch preview
- recording that accepted zone-surface review, boundary lineage verification, and triangle-delta review are required before replacement
- adding `acceptance_evidence=...` to the replacement summary and replacement-readiness review row
- adding focused FreeCADCmd coverage for the acceptance evidence diagnostics

The latest `INT-REM-BLD-004` cleanup hid duplicate legacy patch-only review details behind normalized Surface Patch metadata by:

- preserving existing `Patch*` preview properties for compatibility and focused diagnostics
- adding `legacy_patch_review=metadata_only` when normalized `IntersectionSurfacePatch*` rows are available
- removing duplicate legacy patch boundary, triangulation, boundary-role, and quality metrics from user-facing Intersection review notes
- keeping normalized `IntersectionSurfacePatchSummary`, row statuses, row diagnostics, replacement gate, and accepted zone-surface handoff notes visible
- adding focused FreeCADCmd coverage for the metadata-only review visibility behavior

The latest `INT-REM-BLD-004` cleanup added a legacy patch compatibility audit by:

- reporting compatibility `Patch*` properties as `property_only` when normalized Surface Patch rows are available
- mapping representative legacy properties to their normalized replacements, such as `PatchTriangulationMode -> IntersectionSurfacePatchSummary`
- storing `IntersectionLegacyPatchCompatibilityAudit`, count, visibility, and summary metadata on the patch preview
- exposing only the concise `legacy_patch_audit=...` summary in Build Parametric review notes
- adding focused FreeCADCmd coverage for the audit metadata

The latest `INT-REM-BLD-004` / Watertight handoff slice propagated replacement-gate and compatibility-audit metadata downstream by:

- adding replacement gate, replacement readiness, handoff preference, selected downstream role, and legacy patch audit fields to `IntersectionWatertightHandoffSummary`
- appending those fields to transitional `intersection_patch_body` target handoff notes
- preserving the same fields in `SimulationPackageOutput`
- writing and reading the fields through the durable `V1SimulationPackageOutput` object
- exporting the fields in the simulation package JSON `intersection_handoff` block
- adding focused FreeCADCmd coverage for Watertight target annotation, package output preservation, object round-trip, and JSON export

The latest `INT-REM-WS-003` slice made Simulation Package blockers replacement-readiness specific by:

- keeping `intersection_final_handoff_blocked` as the broad transitional-only blocker
- adding `intersection_replacement_gate_review_required` when replacement readiness is `review_only`
- adding `intersection_replacement_gate_blocked` when replacement readiness is `blocked`
- adding `intersection_replacement_ready_patch_fallback` when the gate is ready but the package still depends on the patch fallback
- adding focused FreeCADCmd coverage for the package diagnostic kinds

The latest `INT-REM-WS-003` slice exposed the readiness-specific package blocker as persisted and exported handoff metadata by:

- adding `intersection_handoff_replacement_blocker_kind` to `SimulationPackageOutput`
- writing the value to `V1SimulationPackageOutput.IntersectionHandoffReplacementBlockerKind`
- preserving the value through `to_simulation_package_output`
- exporting the value as `intersection_handoff.replacement_blocker_kind` in Simulation Package JSON
- documenting the readiness-to-blocker mapping table
- adding focused FreeCADCmd coverage for service, persisted object, round-trip, and JSON export behavior

The latest `INT-REM-WS-003` slice exposed the same replacement blocker before package build in Simulation QA by:

- adding Intersection final-quality, Digital Twin handoff, replacement readiness, and replacement blocker fields to `SimulationQaOutput`
- writing those fields to `V1SimulationQaOutput`
- preserving the fields through `to_simulation_qa_output`
- adding a `SimulationQaDiagnosticRow` with the readiness-specific blocker kind when the intersection patch fallback blocks final handoff
- forcing `simulation_ready=False` while that blocker is active
- adding focused FreeCADCmd coverage for the pre-package Simulation QA blocker path

The latest `INT-REM-WS-003` slice exposed the pre-package replacement blocker in the Watertight Solids panel status text by:

- adding Intersection final-quality status to the Simulation QA status lines
- adding Intersection Digital Twin handoff status
- adding replacement readiness
- adding the readiness-specific replacement blocker kind
- adding focused FreeCADCmd coverage for the panel/status text path

The latest `INT-REM-WS-003` slice made the broad Simulation QA final-handoff blocker easier to filter by:

- adding an `intersection_final_handoff_blocked` diagnostic row before package build
- preserving `V1CorridorIntersectionSurfacePreview` as the diagnostic source ref
- including the readiness-specific `blocker_kind` in the broad diagnostic notes
- including replacement readiness and replacement gate in the broad diagnostic notes
- keeping the readiness-specific diagnostic row alongside the broad blocker
- adding focused FreeCADCmd coverage for the broad blocker notes

The latest `INT-REM-WS-003` slice made package export summaries expose the same Intersection blocker fields by:

- adding Intersection final-quality status to the export command return info
- adding Intersection Digital Twin handoff status
- adding replacement readiness
- adding replacement blocker kind
- keeping the existing JSON payload fields unchanged
- adding focused FreeCADCmd coverage for the intersection package export-info path

The latest `INT-REM-BLD-005` follow-up suppresses visible Slope Face boundary strip generation by:

- storing `intersection_slope_face_boundary_strip_generation_mode=suppressed` in generated TIN quality rows
- storing `intersection_slope_face_boundary_strip_output_path=metadata_only`
- preserving a strip diagnostic that says visible strip generation is suppressed
- exposing zero strip triangles in Build Parametric review notes

The latest `INT-REM-BLD-005` slice moved Guided Review toward the boundary-first contract by:

- detecting `slope_face_boundary=...` notes from Build Parametric review rows
- adding `boundary_review=intersection_slope_face_boundary_result` to the `slope_issues` Guided Review step
- keeping boundary review metadata-only instead of focusing a visible `Intersection Slope Face Boundary` object
- adding focused FreeCADCmd coverage for the Guided Review boundary suffix helper

The latest `INT-REM-BLD-001` slice exposed Slope Face Loop edge-network lineage in Build Parametric by:

- adding `edge_network_status=...` notes to `slope_face_loop` Intersection Contracts rows
- preserving consumed Edge Network warning/error status alongside existing `source_lineage=...` and `surface_zone_status=...` notes
- adding focused FreeCADCmd coverage for Build Parametric contract review rows

The latest `INT-REM-BLD-001` slice made source-status summary visibility explicit by:

- adding `source status=...` distribution notes to Intersection Contract summaries
- reporting `source status=missing=1` for missing IntersectionModel contract rows
- preserving `source status=accepted=...` for evaluated accepted rows
- keeping warning/error source status counts visible alongside existing `source warnings=...`
- adding focused FreeCADCmd coverage for missing, accepted, and warning source-status summaries

The latest `INT-REM-BLD-003` slice preserved consumed contract row diagnostics in output preview metadata by:

- adding row-level source diagnostics to `ConsumedIntersectionContractDiagnostics`
- preserving Slope Face Loop `source_status`, `source_lineage`, consumed Surface Zone status, and consumed Edge Network status on Slope Face Surface previews
- keeping skipped warning/error Slope Face loops visible in output handoff metadata even when only ready loops generate triangles
- adding focused FreeCADCmd coverage for Slope Face Surface consumed-loop diagnostics metadata
- adding focused FreeCADCmd coverage that multi-contract output metadata preserves row source diagnostics from Edge Network, Surface Zone, Grading Context, Drainage Hint, and Slope Face Loop rows

The latest `INT-REM-BLD-003` slice moved Slope Face review rows closer to consumed result contracts by:

- exposing `ConsumedIntersectionContractSummary` in the `intersection_slope` Build Parametric review row notes
- exposing `ConsumedIntersectionContractDiagnosticCount` in the same review row
- keeping Slope Face review tied to `IntersectionSlopeFaceLoopResult` metadata instead of only ready/skipped loop counts
- adding focused FreeCADCmd coverage for the Slope Face review consumed-contract notes

The latest `INT-REM-BLD-003` slice tightened Slope Face output-path labeling by:

- checking `ConsumedIntersectionContractRefs` before ready-loop geometry counts for `intersection_slope`
- keeping `output_path=contract_consumed` when a Slope Face Loop contract was consumed even if rows are warning-only or generate no ready loop geometry
- preserving `inferred_fallback` only for review paths without consumed contract refs
- adding focused FreeCADCmd coverage for contract-ref precedence in Slope Face output-path labels

The latest `INT-REM-WS-003` slice propagated Simulation Package replacement blockers into broader ExchangePackage source-context rows by:

- recognizing `SimulationPackageOutput` as a stable exchange output id source
- adding a `simulation_package_intersection_handoff` source-context row when Intersection handoff metadata is present
- preserving `intersection_ref`, final-quality status, Digital Twin handoff status, replacement readiness, replacement gate, downstream selected role, legacy patch review visibility, and replacement blocker kind
- keeping the row discoverable through `source_context_count`
- adding focused FreeCADCmd coverage for the ExchangePackage source-context path

The latest `INT-REM-WS-003` slice added compact ExchangePackage payload metadata for the same Simulation Package handoff by:

- exposing `simulation_intersection_handoff_context_count`
- exposing the first `simulation_intersection_replacement_blocker_kind`
- exposing all unique `simulation_intersection_replacement_blocker_kinds`
- keeping the detailed source-context row as the authoritative trace row
- adding focused FreeCADCmd coverage for the metadata summary

The latest `INT-REM-WS-003` slice carried the same ExchangePackage Intersection metadata through JSON export by:

- preserving the compact metadata fields in exported `payload_metadata`
- preserving the detailed `simulation_package_intersection_handoff` source-context row in exported `source_context_rows`
- returning `simulation_intersection_handoff_context_count` from `export_exchange_package_to_json`
- returning the first and unique replacement blocker kinds from `export_exchange_package_to_json`
- adding focused FreeCADCmd coverage for the JSON export path

The latest `INT-REM-WS-003` slice exposed the same blocker through IFC/export-preview summaries by:

- returning Simulation Package Intersection handoff count and blocker kinds from `export_exchange_package_to_ifc`
- writing a project-level `CorridorRoadExchangePackage` IFC property set when Simulation Package Intersection blocker metadata is present
- adding the Simulation Package Intersection count and blocker to the Structure Output source-context preview summary
- adding focused FreeCADCmd coverage for the IFC and preview-summary paths

The latest `INT-REM-WS-003` slice removed a remaining legacy-preview bypass by:

- adding `intersection_surface_replacement_blocker_kind` as the shared output-contract helper
- writing `IntersectionSurfaceReplacementBlockerKind` on the transitional patch preview and accepted zone preview objects during downstream handoff selection
- adding the replacement blocker to `IntersectionSurfaceDownstreamHandoffSummary`
- making Watertight Simulation QA and Simulation Package blocker assignment use the same helper
- keeping `ready_to_replace` blocker output specific to cases where downstream selection still packages the transitional patch fallback
- adding focused FreeCADCmd coverage for the helper contract, preview metadata, Simulation QA, and Simulation Package blocker paths

The latest `INT-REM-WS-003` slice aligned schema documentation by:

- adding shared Intersection replacement handoff metadata to `V1_SURFACE_OUTPUT_SCHEMA.md`
- documenting `IntersectionSurfaceReplacementBlockerKind` as surface output-contract metadata
- documenting the three recommended replacement blocker kinds
- clarifying that `intersection_replacement_ready_patch_fallback` only applies when patch fallback remains selected
- adding Simulation Package Intersection handoff count and blocker metadata fields to `V1_EXCHANGE_OUTPUT_SCHEMA.md`

The final `INT-REM-WS-003` verification slice passed the focused Intersection/Watertight/Exchange regression set by covering:

- Build Parametric downstream handoff decision and preview blocker metadata
- transitional-only Simulation Package blocking
- readiness-specific Simulation Package blocker kinds
- pre-package Simulation QA blocker diagnostics
- ExchangePackage source-context and payload metadata propagation
- JSON export, IFC export, and Structure Output preview-summary blocker visibility

`INT-REM-WS-003` is now functionally complete.

The latest `INT-REM-WS-005` slice expanded Watertight Solid Exchange source-context lineage by:

- preserving row-level `diagnostic_refs`
- preserving row-level `notes`
- exposing `intersection_leg_ref`
- exposing `intersection_control_area_ref`
- exposing `intersection_edge_family_ref`
- keeping the existing Intersection, Surface Zone, Edge Network, Surface Zone Result, material, station span, and target metadata
- adding focused FreeCADCmd coverage for accepted-zone Watertight Solid Exchange lineage

The latest `INT-REM-WS-005` slice added compact Watertight Intersection Exchange export metadata by:

- exposing `watertight_intersection_source_context_count`
- exposing `watertight_intersection_surface_zone_context_count`
- exposing `watertight_intersection_diagnostic_ref_count`
- preserving those fields through JSON export return info and exported `payload_metadata`
- returning the same fields from IFC export
- writing project-level IFC properties for the same Watertight Intersection lineage counts
- adding focused FreeCADCmd coverage for JSON and IFC export lineage metadata

The latest `INT-REM-WS-005` slice exposed Watertight Intersection lineage in the shared Exchange preview summary by:

- adding Watertight Intersection source-context count
- adding accepted Surface Zone context count
- adding row-level diagnostic ref count
- keeping the existing side-slope, bench, Simulation Intersection, and blocker summary values
- adding focused FreeCADCmd coverage for the preview-summary text

The final `INT-REM-WS-005` verification slice passed the focused Watertight/Exchange source-lineage regression set across:

- Watertight Solid Exchange mapper source-context rows
- compact ExchangePackage metadata counts
- JSON export return info and payload metadata
- IFC export return info and project-level metadata
- shared Exchange preview summary text

`INT-REM-WS-005` is now functionally complete for current output/export consumers.

The latest `INT-REM-WS-004` slice aligned trim/fuse accepted-vs-fallback handoff status by:

- promoting the QA trim handoff decision helper to a shared builder helper
- adding `intersection_trim_handoff_status` to `SimulationPackageOutput`
- persisting `IntersectionTrimHandoffStatus` on `V1SimulationPackageOutput`
- exporting `intersection_trim.handoff_status` in Simulation Package JSON
- returning `intersection_trim_handoff_status` from Simulation Package JSON export
- adding focused FreeCADCmd coverage through the trim preview, QA, package object, package output, JSON payload, and export-info path

The latest `INT-REM-WS-004` slice exposed package-level trim handoff status in panel/export text by:

- adding `trim_handoff` and `trim_fuse` to the Simulation Package build status line
- adding trim handoff and fuse status to the Simulation Package JSON export completion text
- extracting the package status-line formatter for focused testing
- adding focused FreeCADCmd coverage for the status-line formatter and trim export path

The final `INT-REM-WS-004` verification slice passed the focused trim/fuse regression set across:

- Simulation QA trim handoff status
- Simulation Package object roundtrip
- Simulation Package output conversion
- JSON payload and export-info fields
- package build/export panel status text formatter

`INT-REM-WS-004` is now functionally complete for current QA, Package, JSON export, and panel consumers.

The next slice should move back to the remaining non-complete Intersection tasks outside the Watertight phase, starting with the highest-risk source/result items that still show `Started` in Phase 1 and Phase 2.
