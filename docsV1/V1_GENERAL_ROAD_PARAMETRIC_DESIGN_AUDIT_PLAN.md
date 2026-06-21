# Parametric Road V1 General Road Parametric Design Audit Plan

Date: 2026-06-20
Status: Phase 3 implementation in progress
Depends on:

- [V1_MASTER_PLAN.md](./V1_MASTER_PLAN.md)
- [V1_ARCHITECTURE.md](./V1_ARCHITECTURE.md)
- [V1_ALIGNMENT_MODEL.md](./V1_ALIGNMENT_MODEL.md)
- [V1_PROFILE_MODEL.md](./V1_PROFILE_MODEL.md)
- [V1_ASSEMBLY_MODEL.md](./V1_ASSEMBLY_MODEL.md)
- [V1_SUBASSEMBLY_FULL_ADOPTION_PLAN.md](./V1_SUBASSEMBLY_FULL_ADOPTION_PLAN.md)
- [V1_APPLIED_SECTION_SUPPLEMENTAL_SAMPLING_REDESIGN_PLAN.md](./V1_APPLIED_SECTION_SUPPLEMENTAL_SAMPLING_REDESIGN_PLAN.md)
- [V1_3D_CENTERLINE_SOURCE_GEOMETRY_DISPLAY_PLAN.md](./V1_3D_CENTERLINE_SOURCE_GEOMETRY_DISPLAY_PLAN.md)
- [V1_WATERTIGHT_SOLID_PLAN.md](./V1_WATERTIGHT_SOLID_PLAN.md)

## 1. Purpose

This document audits the ordinary road design workflow against the Parametric Road design philosophy.

The goal is to find places where ordinary-road geometry may still be created from preview objects, sampling artifacts, fallback repairs, or downstream mesh cleanup instead of durable source data.

It also defines an improvement plan so ordinary roads can become a reliable source-driven foundation for later intersections, ramps, drainage, structures, and watertight Digital Twin outputs.

## Current Implementation Stage

Current stage:

- `Phase 6 - Watertight Solid readiness gate`

Current target:

- `Phase 7 Target 5 - Assembly/Subassembly physical-body contract UX`

Completed in this plan:

- `Target 1 - Build Corridor consumer disclosure`
- `Target 2 - Applied Sections diagnostic summary`
- `Target 3 - Section Preview consistency contract`
- `Target 4 - Watertight Solid readiness handoff`

In progress:

- expose physical-body material, thickness, shape-code, and solid-family contract readiness in the Assembly/Subassembly selected-row detail view.

Recently completed:

- Build Corridor exposes consumed result contracts, surface role contracts, Region context, and fallback warnings.
- Build Corridor is guarded against reverse-reading generated preview `Shape` geometry as source intent.
- Watertight Solid readiness distinguishes envelope, surface-like, and physical-body targets.
- Watertight Solid readiness reports station spans, Region refs, material refs, missing prerequisites, and blocked target rows.
- Digital Twin readiness summarizes overall readiness plus physical-body readiness.
- Physical-body targets require material contracts and continuous closed shape profiles across the target span.
- `Full Set Road` provides an ordinary-road full Assembly/Subassembly surface-review sample with lane, shoulder, gutter, sidewalk, ditch, and side-slope rows, without pavement_layer/subbase physical-body rows.
- Watertight Solids panel status summaries expose Simulation QA diagnostic counts and leading diagnostic ids.
- Deep physical solid geometry QA is intentionally deferred until intersection, ramp, drainage, and structure source/result workflows are more stable.
- Assembly/Subassembly selected-row detail now summarizes physical-body contract readiness without requiring users to inspect hidden columns.

## 2. Scope

This audit covers ordinary road design without dedicated intersection or ramp topology.

Included stages:

- Alignment
- Profile
- 3D Centerline
- Superelevation
- SubAssembly Designer
- Assembly / Subassembly
- Region
- Applied Sections
- Supplemental Applied Sections
- Terrain / daylight
- Build Corridor / Build Parametric
- Review objects
- Quantity and Watertight Solid readiness

Out of scope:

- dedicated intersection topology redesign
- ramp topology redesign
- advanced hydraulic pipe sizing
- final Digital Twin exchange package implementation

## 3. Core Rule

Ordinary road geometry must be generated from source-owned design intent through deterministic evaluation contracts.

Generated geometry must not become design intent.

Preview objects, review markers, B-spline display curves, clipped mesh fragments, and supplemental section markers are not source data.

If a result needs geometry that cannot be derived from source data, add or correct the source/evaluation contract before adding downstream repair logic.

## 4. Current Strengths

The ordinary-road workflow is already close to the intended source-driven model in several areas.

- Alignment and Profile are independent source stages.
- 3D Centerline is treated as an evaluated baseline for downstream consumers.
- SubAssembly Designer now owns reusable point, link, shape, and surface-role behavior.
- Assembly / Subassembly places reusable definitions with side, order, and overrides.
- Applied Sections evaluate placed Subassembly rows into station-based result rows.
- Supplemental Applied Sections have moved to the Applied Sections stage.
- Build Corridor increasingly consumes Applied Section rows instead of re-evaluating source intent.
- Watertight Solids are positioned after Build Corridor as downstream output, not as a corridor source.

These strengths should be preserved.

## 5. Parametric Gaps And Risks

### 5.1 3D Centerline display modes can be confused with source truth

Risk:

- `B-spline` and `Polyline` display modes can look like alternate design definitions.
- Downstream tools may accidentally consume a display curve rather than the source-geometry result.

Required rule:

- Alignment and Profile remain the source.
- `Centerline3DResult` is the evaluated result.
- `Source Geometry` is the preferred downstream baseline.
- `B-spline` and `Polyline` are review/display modes only unless explicitly marked as an output approximation.

Improvement:

- Add diagnostics to every downstream 3D Centerline consumer showing the consumed source mode.
- Block or warn when a downstream builder consumes a display-only fallback.
- Keep `PreviewSource=centerline3d_source_geometry` as the expected Build Corridor path.

### 5.2 Supplemental Applied Sections may look like editable station source

Risk:

- Supplemental sections improve curved surface fidelity.
- Users may interpret them as design stations or editable station rows.

Required rule:

- Supplemental Applied Sections are result-only sampling rows.
- Their density and spacing policy may be source/configuration data.
- The generated supplemental rows must not be edited as station source.

Improvement:

- Persist supplemental policy separately from generated supplemental rows.
- Display `station_kind=supplemental` clearly in review tables.
- Add summary counts for source stations, region/control stations, and supplemental stations.
- Ensure Build Corridor consumes supplemental Applied Sections but never creates hidden supplemental frames for ordinary roads.

### 5.3 Applied Section clipping can hide source errors

Risk:

- Clipping is useful to prevent crossing section lines and broken surfaces.
- If clipping changes the intended section shape without diagnostics, the result can become a silent design modification.

Required rule:

- Applied Section clipping is a result constraint, not a source edit.
- Clipped geometry must preserve traceability to the source Subassembly row.
- Any clipping should be visible in diagnostics.

Improvement:

- Add per-section clipping diagnostics with subassembly id, side, link role, and clipped distance.
- Separate "protected design body" clipping from "daylight/slope cleanup" clipping.
- Expose clipping counts in Applied Sections and Cross Section Viewer.
- Do not write clipped coordinates back to Assembly/Subassembly or SubAssembly Designer source rows.

### 5.4 Build Corridor may still contain fallback geometry behavior

Risk:

- Build Corridor has historically repaired or inferred surface geometry when input rows were incomplete.
- That can make surfaces appear acceptable even when source/evaluation data is missing.

Required rule:

- Build Corridor consumes accepted Applied Section and result contracts.
- Build Corridor must not infer missing design meaning from meshes, preview objects, or generated tree objects.

Improvement:

- Audit Build Corridor builders for direct reads of preview geometry, object `Shape`, or display-only tree objects.
- Replace source inference with explicit result contract reads.
- Convert legacy fallback geometry into warnings or compatibility-only paths.
- Add object properties reporting consumed result ids and fallback status.

### 5.5 Ditch and side-slope behavior needs stricter source contracts

Risk:

- Ditch geometry can be inferred from `top_width`, `bottom_width`, and `depth`.
- Side-slope daylight can fall back to fixed width when terrain is missing.
- These behaviors are practical, but can become hidden source assumptions.

Required rule:

- Ditch shape should be explicit source intent when possible.
- Terrain/daylight fallback must be diagnostic.
- Fixed-width fallback must not silently replace missing daylight source or terrain context.

Improvement:

- Normalize preset and UI data to include explicit `shape=trapezoid` for ditch rows.
- Add diagnostics when a ditch shape is inferred for compatibility.
- Add diagnostics when daylight uses fixed-width fallback because terrain is missing or intersection failed.
- Surface role outputs must remain tied to evaluated links, not hard-coded subassembly kind names.

### 5.6 Subassembly Ref guessing is useful but not authoritative

Risk:

- Guessing `Subassembly Ref` from `Subassembly ID` improves UX.
- If treated as automatic design truth, it can connect the wrong reusable definition.

Required rule:

- Guessing is a user-assisted source-edit action.
- Guessed refs must require review before Apply.

Improvement:

- Keep warning text near the guess action.
- Add confidence notes when practical.
- Add validation that reports unresolved or suspicious definition refs before Applied Sections.

### 5.7 Section Preview and Applied Sections must use one section evaluator

Risk:

- If Section Preview and Applied Sections evaluate section shapes differently, users cannot trust preview.

Required rule:

- Section Preview is review only, but it should use the same source interpretation rules as Applied Sections.
- Applied Sections remain the accepted result.

Improvement:

- Consolidate preview and Applied Section geometry through shared Subassembly evaluation helpers.
- Add contract tests comparing preview segment endpoints to Applied Section row endpoints for common lane, shoulder, ditch, sidewalk, and side-slope presets.
- Show stale-source warnings when preview was generated before the latest Apply.

### 5.8 Watertight Solid readiness is not yet a normal ordinary-road acceptance gate

Risk:

- Ordinary roads may produce surfaces that look valid but do not have closed, traceable solid bodies.
- This weakens the Digital Twin goal.

Required rule:

- Ordinary-road outputs should prepare solid-ready contracts where physical bodies exist.
- Surface-only outputs and solid-body outputs must remain distinct.

Improvement:

- Add ordinary-road Watertight Solid readiness diagnostics to Build Corridor or Cross Section Viewer.
- Report closed shape availability by Subassembly kind, material, station span, and Region.
- Keep terrain/surface bodies and physical Subassembly bodies as separate target families.

## 6. Target Ordinary-Road Contract

The ordinary-road pipeline should follow this contract:

```text
Alignment source
Profile source
Superelevation source
Subassembly definition source
Assembly placement source
Region source
Terrain source
    -> evaluation services
3D Centerline result
Applied Section result
Surface result
Quantity result
Watertight Solid target result
    -> output and review objects
```

No output stage should reverse-read a preview object as source.

No result stage should silently invent source intent.

## 7. Implementation Plan

### Phase 1 - Audit and diagnostics

Goal:

- find ordinary-road code paths that violate source/evaluation/result boundaries.

Tasks:

- audit Build Corridor for direct preview object or generated `Shape` reads
- audit Applied Sections for silent geometry fallback paths
- audit 3D Centerline consumers for display-mode ambiguity
- audit Section Preview against Applied Section evaluation behavior
- list all ordinary-road fallback diagnostics and missing diagnostics

Acceptance criteria:

- a source/consumer map exists for ordinary-road geometry generation
- each fallback path is classified as `valid compatibility`, `needs diagnostic`, or `must remove`
- no high-risk fallback remains undocumented

### Phase 2 - 3D Centerline and supplemental sampling hardening

Goal:

- ensure ordinary-road frames are derived from source-geometry centerline results.

Tasks:

- require downstream consumers to report consumed 3D Centerline result id and source mode
- warn when a display-only fallback is used
- keep supplemental section generation in Applied Sections only
- expose source station, supplemental station, and total consumed section counts consistently

Acceptance criteria:

- Build Corridor review shows expected `centerline3d_source_geometry`
- changing supplemental density changes Applied Sections before Build Corridor
- Build Corridor does not create hidden ordinary-road supplemental frames

### Phase 3 - Subassembly handoff consolidation

Goal:

- make Section Preview, Applied Sections, and Build Corridor consume the same Subassembly meaning.

Tasks:

- consolidate common Subassembly parameter normalization
- add tests for lane, shoulder, sidewalk, ditch, and side-slope preview-to-Applied-Section consistency
- require explicit shape source where possible
- keep compatibility inference diagnostic

Acceptance criteria:

- Section Preview and Applied Sections agree on connected endpoints for starter presets
- ditch and sidewalk examples evaluate through reusable definitions
- missing or inferred Subassembly data is visible before Build Corridor

### Phase 4 - Clipping and daylight transparency

Goal:

- keep clipping and daylight fallback from becoming hidden design changes.

Tasks:

- add Applied Section clipping diagnostic rows
- expose clipped subassembly/link ids in review
- add daylight fallback status to slope/daylight result rows
- distinguish terrain-intersection success from fixed-width fallback

Acceptance criteria:

- a clipped section can be traced to source row and clip reason
- terrain/daylight fallback is visible in Applied Sections and Build Corridor diagnostics
- no source row is modified by clipping

### Phase 5 - Build Corridor consumer cleanup

Goal:

- make Build Corridor a result consumer rather than a design interpreter.

Tasks:

- move remaining design interpretation into evaluation services
- replace mesh-derived source assumptions with result contract fields
- report consumed AppliedSectionSet id, Centerline3D id, Region refs, and Surface role counts
- report expected versus consumed surface-role contracts for each generated surface preview
- keep compatibility paths explicit and temporary

Acceptance criteria:

- Build Corridor can explain every generated surface from Applied Section/result input
- ordinary-road surface generation does not require preview objects
- fallback status is visible in review object properties

### Phase 6 - Watertight Solid readiness gate

Goal:

- connect ordinary-road generation to the Digital Twin output path.

Tasks:

- add ordinary-road solid-readiness diagnostics after Build Corridor
- report closed Subassembly shapes by family, material, Region, and station span
- distinguish terrain/surface targets from physical Subassembly body targets
- block or warn when Watertight Solid targets lack closed result contracts

Acceptance criteria:

- ordinary road can report whether it is ready for Watertight Solids
- generated solid targets are traceable to source Subassembly/Region/material context
- missing solid prerequisites point back to source or evaluation rows

## 8. Manual QA Checklist

Use this checklist after implementation phases.

- Build 3D Centerline in `Source Geometry` mode.
- Generate Applied Sections with supplemental sampling enabled.
- Confirm source station and supplemental station counts are reported separately.
- Load an Assembly/Subassembly preset with lane, shoulder, sidewalk, ditch, and side-slope rows.
- Load the `Full Set Road` Assembly/Subassembly preset and confirm it includes lane, shoulder, gutter, sidewalk, ditch, and side-slope rows.
- Confirm `pavement_layer` and `subbase` are intentionally excluded from the current full-set preset until physical-body authoring is reintroduced.
- Compare Section Preview endpoints with Applied Section geometry.
- Build Corridor.
- Confirm Build Corridor reports consumed Centerline3D source mode and AppliedSectionSet id.
- Confirm Build Corridor review rows report expected versus consumed surface-role contracts.
- Confirm Design, Subgrade, Drainage, and Slope Face surfaces show warning status when their expected Applied Section surface role is missing.
- Confirm Build Corridor preview objects report consumed Region refs and intersection-control Region refs.
- Confirm Build Corridor review rows show compact Region contract notes without opening raw object properties.
- Confirm ditch, shoulder, sidewalk, and side-slope surface roles are traceable to Subassembly refs.
- Confirm review/highlight behavior does not depend on copying generated preview object `Shape` geometry when result-contract boundary rows are missing.
- Force missing terrain and verify daylight fallback diagnostics appear.
- Force a tight curve and verify clipping diagnostics appear when section lines are clipped.
- Open Watertight Solids and confirm readiness diagnostics point to accepted result contracts.
- Confirm Build Corridor review rows show Watertight Solid readiness status and target class counts.
- Confirm readiness properties distinguish envelope, surface-like, and physical-body targets.
- Confirm envelope readiness and physical-body readiness are reviewed separately.
- Confirm Build Corridor Guided Review warns when envelope targets exist but no physical-body target contract exists.
- Confirm the physical-body readiness reason points to missing closed Subassembly shape/material contracts.
- Confirm `digital_twin_readiness` is blocked when physical-body readiness is blocked, even if envelope readiness is ready.
- Confirm `WatertightSolidDigitalTwinReadinessSummary` reports overall readiness, physical-body readiness, missing prerequisite count, and blocked target count.
- Confirm closed Subassembly shape profiles exist at every Applied Section station inside the target station span.
- Remove one closed shape profile from an intermediate station and confirm `subassembly_shape_target_missing_profile` identifies the missing station.
- Confirm readiness properties expose target station spans, Region refs, and material refs.
- Force missing Applied Sections or CorridorModel context and confirm missing prerequisite rows identify the blocked source/evaluation requirement.
- Confirm blocked or partial Watertight Solid readiness appears as warning in Build Corridor Guided Review rows.
- Build or load physical Watertight Solid outputs and confirm Simulation QA reports `solid_output_missing_target_family` when an output has no target-family contract.
- Confirm Simulation QA reports `solid_output_missing_source_refs` when an output has target families but no Subassembly, structure, flow route, or source refs.
- Confirm valid-looking solids cannot be accepted as Digital Twin-ready when target-family traceability is missing.
- Confirm Watertight Solids panel status text exposes Simulation QA diagnostic count, error count, warning count, and leading diagnostic ids.
- In Assembly/Subassembly, select pavement, subbase, lane, and shoulder rows and confirm Selected Subassembly Detail reports physical-body contract readiness.

## 8.1 Deferred Physical Solid Geometry QA

Deep physical solid geometry QA is out of scope for the current ordinary-road audit stage unless explicitly requested.

Current retained scope:

- target-family traceability
- source/result refs traceability
- material contract visibility
- closed-shape profile contract visibility
- readiness and status-summary diagnostics

Deferred scope:

- detailed watertight shell repair
- non-manifold topology diagnosis
- self-intersection detection
- boolean/fuse robustness tuning
- final simulation-grade solid reconstruction strategy

Reason:

- physical solid quality work depends on stable intersection, ramp, drainage, and structure source/result workflows.
- Deep geometry repair before those domains stabilize risks optimizing the wrong output contract.

## 9. Non-goals

- This plan does not redesign intersections.
- This plan does not replace Alignment/Profile source editors.
- This plan does not require every ordinary-road Subassembly to create a solid body.
- This plan does not make preview objects editable source.
- This plan does not remove compatibility fallback immediately; it makes fallback explicit and temporary.

## 10. Expected Architectural Effect

After this plan, ordinary-road generation should be easier to trust.

Every ordinary-road surface or solid should answer:

- which source rows defined it
- which evaluation result produced it
- which fallback or clipping rules affected it
- which review object displays it
- whether it is ready for Digital Twin-oriented Watertight Solid handoff
