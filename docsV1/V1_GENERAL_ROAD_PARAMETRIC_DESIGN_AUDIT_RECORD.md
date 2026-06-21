# Parametric Road V1 General Road Parametric Design Audit Record

Date: 2026-06-20
Status: Phase 1 audit record
Plan:

- [V1_GENERAL_ROAD_PARAMETRIC_DESIGN_AUDIT_PLAN.md](./V1_GENERAL_ROAD_PARAMETRIC_DESIGN_AUDIT_PLAN.md)

## 1. Purpose

This record captures the first ordinary-road parametric design audit snapshot.

It identifies which parts of the ordinary-road pipeline already follow the source -> evaluation -> result -> output -> presentation rule and which parts need additional diagnostics or cleanup.

This document is a working implementation record, not a replacement for the plan.

## 2. Audit Rule

Ordinary-road geometry is acceptable only when it can be traced to source-owned design intent through deterministic result contracts.

The audit classifies code paths as:

- `aligned`: follows the parametric source/result contract
- `needs diagnostic`: acceptable as a compatibility or fallback path, but must be visible
- `needs cleanup`: likely mixes generated geometry, preview state, or fallback behavior with design meaning
- `defer`: outside ordinary-road scope or dependent on a later subsystem redesign

## 3. Source / Consumer Map

| Stage | Owns Source Intent | Consumes | Produces | Audit Status |
| --- | --- | --- | --- | --- |
| Alignment | horizontal geometry, curve rows, station geometry | project context | alignment evaluation and curve preview | aligned |
| Profile | PVI rows, vertical curves, elevations | Alignment station context | profile elevation evaluation and preview | aligned |
| 3D Centerline | none; Alignment/Profile remain source | Alignment and Profile results | `Centerline3DResult`, display geometry | aligned with diagnostic follow-up |
| Superelevation | crossfall controls and transition intent | Alignment station context | effective crossfall result | aligned |
| SubAssembly Designer | reusable point/link/shape/parameter definitions | optional Assembly row context | draft preview and saved definitions | aligned |
| Assembly / Subassembly | placement, side, order, overrides, definition refs | Subassembly definitions | source model and review preview | aligned with preview consistency follow-up |
| Region | station spans and base Assembly refs | Alignment/Stationing context | region context for Applied Sections | aligned |
| Applied Sections | none; generated result | all ordinary-road source/evaluation context | station-based section result rows | aligned with clipping/fallback diagnostics follow-up |
| Supplemental Applied Sections | none; generated result only | Centerline3D and Applied Section policy | supplemental section rows | aligned |
| Build Corridor | no design intent source | Applied Sections and result contracts | preview surfaces and diagnostics | needs diagnostic |
| Review Objects | no design intent source | source/result/output contracts | display and diagnostics | aligned if read-only |
| Watertight Solids | output configuration only | accepted result contracts | closed solids and Digital Twin handoff artifacts | aligned with readiness gate follow-up |

## 4. Current Aligned Behaviors

### 4.1 3D Centerline source mode is already traceable

Evidence:

- Applied Sections can record `source=centerline3d_source_geometry`.
- Build Corridor centerline preview has a preferred `centerline3d_source_geometry` path.
- Fallback paths are named, not silent.

Status:

- `aligned`

Follow-up:

- expose consumed centerline source mode consistently in Build Corridor review and downstream output objects.

### 4.2 Supplemental Applied Sections are generated in Applied Sections

Evidence:

- Supplemental section diagnostics exist.
- Supplemental density is no longer a hidden Build Parametric-only operation.
- Tests already check source mode counts and fallback counts.

Status:

- `aligned`

Follow-up:

- keep generated supplemental rows visibly result-only in all review tables.

### 4.3 Applied Section overlap clipping has diagnostics

Evidence:

- `applied_section_overlap_clip` diagnostics are produced.
- Tests already check regular and supplemental clipping diagnostics.

Status:

- `aligned with follow-up`

Follow-up:

- expose clipping counts and source row context in review UI, not only in raw diagnostics.

### 4.4 Ditch shape compatibility inference is diagnosed

Evidence:

- ditch shape diagnostics exist in Applied Sections.
- reusable ditch definitions can evaluate from explicit trapezoid parameters.

Status:

- `aligned with follow-up`

Follow-up:

- prefer explicit `shape=trapezoid` in source/preset data.
- keep inference as compatibility-only and diagnostic.

## 5. Fallback And Risk Classification

| Area | Current Behavior | Risk | Classification | Required Action |
| --- | --- | --- | --- | --- |
| 3D Centerline fallback | falls back from source geometry to older centerline result path when needed | downstream may trust approximate display geometry | needs diagnostic | report consumed source mode and fallback count in Build Corridor outputs |
| Alignment/Profile fallback frames | Applied Sections can use alignment/profile fallback when Centerline3D is unavailable | ordinary road can build without reviewed 3D Centerline | needs diagnostic | warn clearly and recommend rebuilding 3D Centerline |
| Supplemental sampling | result-only supplemental rows are generated for curved spans | users may treat rows as editable stations | aligned | keep station kind and count visible |
| Section overlap clipping | clips crossing section extents in result geometry | clipping can hide source/spacing issues | needs diagnostic | expose clipping summary in Applied Sections and Cross Section Viewer |
| Ditch shape inference | infers trapezoid from width/depth parameters | source shape may be implicit | needs diagnostic | normalize presets and flag inferred shapes |
| Daylight fixed-width fallback | side-slope/daylight can continue without terrain intersection | terrain intent can be silently replaced | needs diagnostic | report daylight source mode and fallback reason |
| Build Corridor compatibility fallback | may consume older result paths for compatibility | output can look valid while source/result prerequisites are stale | needs cleanup | convert to explicit warning and temporary compatibility path |
| Section Preview evaluation | preview and Applied Sections have separate review/result paths | mismatch can undermine user trust | needs cleanup | share evaluation helpers and add endpoint consistency tests |
| Watertight Solid readiness | downstream target discovery exists, but not ordinary-road acceptance gate | visual surfaces may pass without Digital Twin-ready solids | needs diagnostic | add readiness summary after Build Corridor |

## 6. Immediate Implementation Targets

### Target 1 - Build Corridor consumer disclosure

Add or confirm review properties for:

- consumed `AppliedSectionSet` id
- consumed `Centerline3DResult` id
- centerline source mode
- centerline fallback count
- supplemental source section count
- supplemental section count
- total consumed section count

Acceptance:

- Build Corridor review can explain which result contracts were consumed.

Implementation status:

- `2026-06-20`: started.
- `Corridor 3D Centerline` preview now records consumed AppliedSectionSet id, consumed Centerline3D result id, consumed centerline source mode, source/supplemental/total section counts, section kind counts, centerline fallback flag, supplemental compatibility fallback flag, potential supplemental frame count, potential supplemental fallback count, and a compact consumer summary.
- Focused FreeCADCmd validation passed with `PASS Build Corridor consumer disclosure validation`.
- `2026-06-20`: extended to common corridor surface preview contracts.
- Design, subgrade, daylight/slope-face, drainage, and Region surface preview objects that use the common surface preview contract can now disclose the consumed AppliedSectionSet id, source/supplemental/total section counts, section kind counts, supplemental compatibility fallback flag, potential supplemental frame count, potential supplemental fallback count, and a compact consumer summary.
- Focused FreeCADCmd validation passed with `PASS Build Corridor surface consumer disclosure validation`.

### Target 2 - Applied Sections diagnostic summary

Add or confirm summary rows for:

- centerline fallback usage
- overlap clipping count
- ditch shape inference count
- daylight fallback count
- supplemental section count

Acceptance:

- users can detect result-only fallback behavior before Build Corridor.

Implementation status:

- `2026-06-21`: started.
- Applied Sections result objects now expose source section count, supplemental section count, total section count, section kind counts, centerline source mode counts, centerline fallback count, overlap clipping diagnostic count, ditch shape diagnostic count, daylight fallback diagnostic count, total diagnostic count, diagnostic kind counts, and a compact diagnostic summary.
- This keeps fallback and clipping behavior visible before Build Corridor consumes the AppliedSectionSet.

### Target 3 - Section Preview consistency contract

Add tests comparing:

- lane endpoint
- shoulder endpoint
- sidewalk endpoint
- ditch start point
- side-slope hinge point

Acceptance:

- Section Preview and Applied Sections agree for starter ordinary-road presets.

Implementation status:

- `2026-06-21`: started.
- Added a focused contract test comparing Assembly/Subassembly Section Preview endpoints against Applied Sections result endpoints for lane, shoulder, sidewalk, ditch start, and side-slope hinge behavior.
- Corrected the Assembly/Subassembly fallback preview slope calculation so it uses the same decimal slope convention as Applied Sections.

### Target 4 - Watertight Solid readiness handoff

Add ordinary-road readiness reporting for:

- closed shape families
- material roles
- Region spans
- station span continuity
- missing body prerequisites

Acceptance:

- ordinary-road Build Corridor output can tell whether Digital Twin-ready solid handoff is possible.

Implementation status:

- `2026-06-21`: started.
- Build Corridor preview/result objects now expose Watertight Solid target readiness from `SolidTargetDiscoveryService`.
- The readiness disclosure includes target model id, overall readiness status, available/blocked/planned target counts, diagnostic count, target status counts, target family/status counts, blocked diagnostic rows, and a compact readiness summary.
- This makes the ordinary-road Build Corridor output explain whether the downstream Digital Twin watertight-solid handoff is ready, partial, or blocked.

## 7. Phase 1 Result

Phase 1 is partially complete.

Completed:

- source/consumer map created
- fallback paths classified
- immediate implementation targets identified
- Target 1 initial Build Corridor consumer disclosure properties added to the centerline preview object
- Target 1 disclosure properties extended to common surface preview objects
- Target 2 Applied Sections diagnostic summary properties added
- Target 3 Section Preview consistency contract added
- Target 4 Watertight Solid readiness disclosure added to Build Corridor preview/result objects

Still pending:

- deeper Watertight Solid body generation and closed-solid validation

## 8. Recommended Next Step

Proceed with Phase 2 hardening or expand Target 4 into closed-solid validation.

Phase 1 has completed its immediate ordinary-road audit targets.

The next useful work is to harden 3D Centerline/supplemental sampling behavior further or start validating actual closed solid body generation.

## 9. Phase 2 Implementation Record

### Phase 2 Target 1 - Build Corridor fallback consumer warnings

Goal:

- make fallback consumption visible in Build Corridor review rows.

Implementation status:

- `2026-06-21`: started.
- Build Corridor review rows now warn when a preview/result object consumed a centerline source mode other than `centerline3d_source_geometry`.
- Build Corridor review rows also warn when temporary supplemental compatibility fallback is active.
- The review row status is promoted from `ready` to `warning` so fallback output does not look like a fully preferred v1 result path.

Acceptance:

- downstream centerline fallback use is visible before users trust corridor output.

### Phase 2 Target 2 - Supplemental compatibility fallback disclosure

Goal:

- make stale AppliedSectionSet supplemental requirements self-explanatory.

Implementation status:

- `2026-06-21`: started.
- Build Corridor consumer disclosure now records `SupplementalCompatibilityPolicy`.
- Build Corridor consumer disclosure now records `SupplementalCompatibilityReason`.
- When old AppliedSectionSet rows lack generated supplemental sections but curved-span densification is still needed, the preview/result object reports `rebuild_applied_sections_required`.
- Build Corridor no longer treats this as an active compatibility fallback.

Acceptance:

- stale supplemental requirements are visible as an Applied Sections rebuild requirement, not as source data.

### Phase 2 Target 3 - Applied Sections supplemental row precedence

Goal:

- prevent Build Corridor from adding hidden supplemental frames when Applied Sections already owns supplemental rows.

Implementation status:

- `2026-06-21`: started.
- Build Corridor surface preview creation now computes an effective hidden supplemental sampling flag.
- Hidden supplemental sampling is allowed only when explicitly requested and the AppliedSectionSet lacks supplemental rows but still needs curved-span densification for compatibility.
- Design, subgrade, daylight, drainage, and Region surface previews now pass this effective flag into `CorridorSurfaceGeometryService`.

Acceptance:

- Build Corridor consumes Applied Sections supplemental rows as the result contract instead of resampling over them.

### Phase 2 Target 4 - Remove Build Corridor direct supplemental sampling

Goal:

- remove hidden supplemental frame generation from Build Corridor.

Implementation status:

- `2026-06-21`: started.
- Build Corridor surface preview generation now always passes `supplemental_sampling_enabled=False` into corridor surface geometry builders.
- Potential supplemental frame counts remain available only as diagnostics.
- If potential frames are needed but Applied Sections has no supplemental rows, Build Corridor reports `rebuild_applied_sections_required`.

Acceptance:

- Supplemental rows are owned by Applied Sections only.

## 10. Phase 3 Implementation Record

### Phase 3 Target 1 - Explicit ditch shape source diagnostics

Goal:

- make implicit ditch shape inference visible at the source handoff stage.

Implementation status:

- `2026-06-21`: started.
- Ditch rows with `top_width`, `bottom_width`, and `depth` but no explicit `shape` now report a compatibility warning.
- Assembly/Subassembly validation now reuses the same ditch validation helper used by Applied Sections.
- This lets users see the source issue before Applied Sections and Build Corridor consume the row.

Acceptance:

- implicit `shape=trapezoid` inference is visible as source validation, not only as downstream geometry behavior.

### Phase 3 Target 2 - Shared ditch profile preview handoff

Goal:

- make Assembly/Subassembly Section Preview draw ditch rows from the same local profile helper consumed by Applied Sections.

Implementation status:

- `2026-06-21`: started.
- Section Preview now uses `ditch_section_row_local_profile` for ditch rows.
- Trapezoid, V, rectangular/U/L, and custom polyline ditch profiles therefore share the same local profile interpretation between Preview and Applied Sections.
- The preview consistency contract now checks ditch interior break points, not only the outer endpoint.

Acceptance:

- ditch shape preview and Applied Sections ditch surface points are based on the same source helper.

### Phase 3 Target 3 - Shared side-slope bench preview handoff

Goal:

- make Assembly/Subassembly Section Preview draw side-slope/bench rows from the same profile helper consumed by Applied Sections.

Implementation status:

- `2026-06-21`: started.
- Section Preview now uses the Applied Sections bench profile segment helper for `side_slope` rows.
- Side-slope pre-drop, bench width, bench slope, and post-slope behavior are now shared between Preview and Applied Sections.
- The preview consistency contract now checks side-slope and bench break points.
- `2026-06-21`: validated with FreeCADCmd.

Acceptance:

- side-slope bench preview and Applied Sections side-slope/bench points are based on the same source helper.

### Phase 3 Target 4 - Starter Subassembly connection coverage

Goal:

- make the starter lane, shoulder, sidewalk, ditch, and side-slope chain fail fast when Preview and Applied Sections disagree.

Implementation status:

- `2026-06-21`: started.
- The Section Preview consistency contract now checks lane-to-shoulder, shoulder-to-sidewalk, and sidewalk-to-ditch connection points.
- The same test still checks Applied Sections result points for the corresponding finished-grade and ditch-surface offsets.
- The contract now also exercises the actual `Urban Curb & Gutter` preset and verifies each side chain stays connected across lane, gutter, curb, sidewalk, and green strip rows.
- `2026-06-21`: validated with FreeCADCmd.

Acceptance:

- ordinary starter-style rows expose broken handoffs before Build Corridor consumes them.

## 11. Phase 4 Implementation Record

### Phase 4 Target 1 - Applied Section clipping diagnostic traceability

Goal:

- make section overlap clipping explain which evaluated source rows were affected.

Implementation status:

- `2026-06-21`: started.
- `applied_section_overlap_clip` diagnostics now include notes with current section id, previous section id, clipped side, clip limit, clipped point ids, clipped link ids, and affected Subassembly refs when available.
- The overlap clipping contract now checks that a clipped side-slope daylight point and slope-face link remain traceable through diagnostic notes.
- `2026-06-21`: validated with FreeCADCmd.

Acceptance:

- a clipped section can be traced to the affected evaluated point/link ids and Subassembly ref without changing source rows.

### Phase 4 Target 2 - Daylight fallback status disclosure

Goal:

- make terrain daylight success and fixed-width fallback visible without parsing natural-language messages.

Implementation status:

- `2026-06-21`: started.
- Bench daylight diagnostics now include `daylight_mode`, `daylight_status`, `terrain_hit`, and fallback reason or clip distance in diagnostic notes.
- Existing no-EG fallback keeps the same diagnostic kind but now records `daylight_status=fallback`, `terrain_hit=false`, and `fallback_reason=no_existing_ground_tin`.
- Terrain intersection shortening records `daylight_status=terrain_intersection`, `terrain_hit=true`, and `clip_distance`.
- `2026-06-21`: validated with FreeCADCmd.

Acceptance:

- terrain/daylight fallback is visible in Applied Sections diagnostics and can be consumed downstream without guessing from message text.

### Phase 4 Target 3 - Build Corridor daylight/clipping diagnostic handoff

Goal:

- carry Applied Sections clipping and daylight diagnostics into Build Corridor review surfaces.

Implementation status:

- `2026-06-21`: started.
- Build Corridor surface preview objects now receive `AppliedSectionDiagnosticSummary`, diagnostic counts, overlap clip count, daylight fallback count, terrain-hit count, and serialized `AppliedSectionDiagnosticRows`.
- Build Corridor review rows append the Applied Sections diagnostic summary when diagnostics are present.
- AppliedSectionSet object roundtrip now preserves section-level `diagnostic_rows` so Build Corridor can consume the diagnostics after document storage/reload.
- `2026-06-21`: validated with FreeCADCmd.

Acceptance:

- Build Corridor can show clipping/daylight fallback context that originated in Applied Sections without reinterpreting source rows.

### Phase 4 Target 4 - Review visibility for clipped subassembly/link ids

Goal:

- make clipped Subassembly, point, and link refs visible in Build Corridor review without requiring users to parse raw diagnostic notes.

Implementation status:

- `2026-06-21`: started.
- Build Corridor surface preview objects now expose `AppliedSectionClipReviewSummary` and `AppliedSectionClipReviewRows`.
- Clip review rows extract station, current section, previous section, side, clip limit, affected Subassembly refs, point ids, and link ids from Applied Sections clipping diagnostics.
- Build Corridor review rows append a clipping summary when clipped Applied Section rows exist.
- `2026-06-21`: validated with FreeCADCmd.

Acceptance:

- clipped Subassembly refs and link ids are visible from Build Corridor review properties.

### Phase 4 Target 5 - No source mutation confirmation

Goal:

- confirm overlap clipping is a result adjustment and does not mutate source-like Applied Section rows.

Implementation status:

- `2026-06-21`: started.
- The overlap clipping contract now checks that the original supplemental Applied Section retains its daylight widths, Subassembly point offset, and Subassembly link endpoint after clipping returns an adjusted result section.
- `2026-06-21`: validated with FreeCADCmd.

Acceptance:

- clipping remains traceable result behavior and does not rewrite the input Applied Section row data.

## 12. Phase 5 Implementation Record

### Phase 5 Target 1 - Build Corridor consumed result-contract role counts

Goal:

- make Build Corridor explain which Applied Section result contracts it consumed for generated surface previews.

Implementation status:

- `2026-06-21`: started.
- Build Corridor consumer disclosure now includes consumed Subassembly point, link, and shape counts.
- Surface preview objects now expose `ConsumedSurfaceRoleCounts`, `ConsumedPointRoleCounts`, and `ConsumedShapeFamilyCounts`.
- `BuildCorridorConsumerSummary` now includes link count, surface role counts, and shape count.
- `2026-06-21`: validated with FreeCADCmd.

Acceptance:

- Build Corridor preview objects can explain generated surface context from Applied Section result rows, not hidden source interpretation.

### Phase 5 Target 2 - Build Corridor result-contract fallback warning

Goal:

- keep compatibility use of legacy width/point result fields explicit when Applied Section Subassembly links are missing.

Implementation status:

- `2026-06-21`: started.
- Build Corridor consumer disclosure now sets `ResultContractCompatibilityFallbackActive` when Applied Sections exist but no consumed Subassembly link rows are available.
- Preview objects now include `ResultContractCompatibilityReason`.
- Build Corridor review rows now warn when result-contract fallback is active.
- `2026-06-21`: validated with FreeCADCmd.

Acceptance:

- Build Corridor review surfaces make missing Subassembly link result contracts visible instead of silently treating compatibility geometry as the preferred path.

### Phase 5 Target 3 - Build Corridor expected surface-role contract review

Goal:

- make each Build Corridor surface preview show whether it consumed the expected Applied Section surface-role result contract.

Implementation status:

- `2026-06-21`: started.
- Build Corridor surface preview objects now expose `ResultContractExpectedSurfaceRoleStatus`, `ResultContractExpectedSurfaceRoles`, and `ResultContractMatchedSurfaceRoles`.
- Build Corridor review rows now include expected/consumed surface-role contract notes.
- Review rows now warn when a generated surface consumed Subassembly link rows, but none of them match the expected role for that surface.
- `2026-06-21`: validated with FreeCADCmd.

Acceptance:

- Design, subgrade, daylight/slope-face, and drainage previews can show whether their generated surface is tied to the correct Applied Section link role instead of merely having any Subassembly link data.

### Phase 5 Target 4 - Build Corridor preview Shape reverse-read guard

Goal:

- prevent Build Corridor command logic from treating generated preview `Shape` geometry as source data.

Implementation status:

- `2026-06-21`: started.
- Added a focused contract test that scans `cmd_build_corridor.py` for direct preview/source-object `Shape` reverse-read patterns.
- Removed the intersection contract highlight fallback that copied a generated focus object's `Shape` when result-contract boundary/edge rows were missing.
- The guard keeps Build Corridor aligned with the v1 rule that generated geometry is output/presentation, not durable design intent.
- `2026-06-21`: validated with FreeCADCmd.

Acceptance:

- Build Corridor command logic remains guarded against reintroducing preview `Shape` reads as an ordinary-road source inference path.

### Phase 5 Target 5 - Build Corridor consumed Region refs disclosure

Goal:

- make Build Corridor preview objects report the Region context they consumed from Applied Section result contracts.

Implementation status:

- `2026-06-21`: started.
- Build Corridor consumer disclosure now exposes `ConsumedRegionRefs`, `ConsumedRegionCount`, `ConsumedIntersectionControlRegionRefs`, and `ConsumedIntersectionControlRegionCount`.
- `BuildCorridorConsumerSummary` now includes consumed ordinary/control Region counts.
- `2026-06-21`: validated with FreeCADCmd.

Acceptance:

- Build Corridor output can explain Region context from Applied Sections without reverse-reading preview objects or inferring region meaning from generated surface geometry.

### Phase 5 Target 6 - Build Corridor Region context review notes

Goal:

- make consumed Region context visible in Build Corridor review rows, not only object properties.

Implementation status:

- `2026-06-21`: started.
- Build Corridor review rows now append a compact Region contract note when consumed ordinary or intersection-control Region refs are present.
- The note reports Region count, Region refs, intersection-control Region count, and control refs.
- `2026-06-21`: validated with FreeCADCmd.

Acceptance:

- Guided Review can show which Region context a generated surface consumed without opening the raw preview object property list.

### Phase 5 Target 7 - Build Corridor manual QA checklist alignment

Goal:

- keep the manual QA checklist aligned with the Phase 5 consumer-cleanup diagnostics.

Implementation status:

- `2026-06-21`: started.
- Manual QA now asks reviewers to confirm expected versus consumed surface-role contracts in Build Corridor review rows.
- Manual QA now asks reviewers to confirm warning status when expected Design/Subgrade/Drainage/Slope Face surface roles are missing.
- Manual QA now asks reviewers to confirm consumed Region refs and intersection-control Region refs in preview objects and review notes.
- Manual QA now asks reviewers to confirm review/highlight behavior does not depend on copying generated preview object `Shape` geometry when result-contract boundary rows are missing.
- `2026-06-21`: validated by checklist string checks.

Acceptance:

- Manual QA can verify the visible effects of Phase 5 without relying only on automated contract tests.

## 13. Phase 6 Implementation Record

### Phase 6 Target 1 - Watertight Solid target class disclosure

Goal:

- distinguish road envelope, surface-like, and physical-body solid targets in Build Corridor readiness output.

Implementation status:

- `2026-06-21`: started.
- Build Corridor Watertight Solid readiness properties now expose `WatertightSolidPhysicalBodyTargetCount`, `WatertightSolidSurfaceLikeTargetCount`, and `WatertightSolidEnvelopeTargetCount`.
- Build Corridor readiness properties now expose `WatertightSolidTargetClassCounts`.
- `WatertightSolidReadinessSummary` now includes physical-body, surface-like, and envelope target counts.
- Build Corridor result-contract fallback warning now skips the centerline row because Subassembly link contracts are surface-generation prerequisites, not centerline readiness prerequisites.
- `2026-06-21`: validated with FreeCADCmd.

Acceptance:

- ordinary-road Build Corridor output can distinguish visual/terrain-style targets from physical body targets before Digital Twin-oriented watertight solid generation.

### Phase 6 Target 2 - Watertight Solid target span and context disclosure

Goal:

- make Watertight Solid readiness output expose target station spans plus Region/material context.

Implementation status:

- `2026-06-21`: started.
- Build Corridor Watertight Solid readiness properties now expose `WatertightSolidStationSpanCount`.
- Build Corridor readiness properties now expose `WatertightSolidTargetStationSpans`, `WatertightSolidTargetRegionRefs`, and `WatertightSolidTargetMaterialRefs`.
- `WatertightSolidReadinessSummary` now includes station span, Region ref, and material ref counts.
- `2026-06-21`: validated with FreeCADCmd.

Acceptance:

- ordinary-road Build Corridor output can explain the span and context of downstream watertight solid targets before physical solid generation.

### Phase 6 Target 3 - Watertight Solid missing prerequisite diagnostics

Goal:

- make blocked Watertight Solid readiness explain missing prerequisites and affected target rows.

Implementation status:

- `2026-06-21`: started.
- Build Corridor Watertight Solid readiness properties now expose `WatertightSolidMissingPrerequisiteCount`.
- Build Corridor readiness properties now expose `WatertightSolidMissingPrerequisiteRows` with severity, diagnostic kind, source ref, message, and notes.
- Build Corridor readiness properties now expose `WatertightSolidBlockedTargetRows` with target id, family, scope, Region ref, material ref, status, and linked diagnostic kinds.
- `WatertightSolidReadinessSummary` now includes missing prerequisite and blocked target counts.
- `2026-06-21`: validated with FreeCADCmd.

Acceptance:

- blocked Watertight Solid readiness can point back to the missing source/evaluation prerequisite instead of only reporting a blocked status.

### Phase 6 Target 4 - Watertight Solid readiness review notes

Goal:

- make Watertight Solid readiness visible from Build Corridor Guided Review rows.

Implementation status:

- `2026-06-21`: started.
- Build Corridor review rows now append Watertight Solid readiness notes with physical-body, surface-like, envelope, and station span counts.
- Review rows now include missing prerequisite and blocked target counts when present.
- Review rows now warn when Watertight Solid readiness is `blocked` or `partial`.
- `2026-06-21`: validated with FreeCADCmd.

Acceptance:

- users can detect Digital Twin watertight-solid readiness problems directly from Guided Review without opening raw preview object properties.

### Phase 6 Target 5 - Watertight Solid readiness QA checklist alignment

Goal:

- keep the manual QA checklist aligned with Phase 6 Watertight Solid readiness diagnostics.

Implementation status:

- `2026-06-21`: started.
- Manual QA now asks reviewers to confirm Watertight Solid readiness status and target class counts in Build Corridor review rows.
- Manual QA now asks reviewers to confirm envelope, surface-like, and physical-body target separation.
- Manual QA now asks reviewers to confirm target station spans, Region refs, and material refs.
- Manual QA now asks reviewers to force missing Applied Sections or CorridorModel context and confirm missing prerequisite diagnostics.
- Manual QA now asks reviewers to confirm blocked or partial Watertight Solid readiness appears as a Guided Review warning.
- `2026-06-21`: validated by checklist string checks.

Acceptance:

- Manual QA can verify the visible Digital Twin readiness handoff path without relying only on automated tests.

### Phase 6 Target 6 - Physical-body Watertight Solid readiness gate

Goal:

- warn when ordinary-road output has an envelope target but no physical-body Watertight Solid target contract.

Implementation status:

- `2026-06-21`: started.
- Build Corridor Watertight Solid readiness properties now expose `WatertightSolidPhysicalBodyReadinessStatus`.
- Build Corridor readiness properties now expose `WatertightSolidPhysicalBodyReadinessReason`.
- `WatertightSolidReadinessSummary` now includes `physical_body_readiness`.
- Build Corridor review rows now warn when physical-body Watertight Solid readiness is blocked, even if envelope readiness is otherwise ready.
- `2026-06-21`: validated with FreeCADCmd.

Acceptance:

- users can distinguish visual/envelope readiness from Digital Twin physical-body readiness before attempting watertight solid generation.

### Phase 6 Target 7 - Physical-body readiness QA checklist alignment

Goal:

- keep manual QA aligned with the physical-body Watertight Solid readiness gate.

Implementation status:

- `2026-06-21`: started.
- Manual QA now asks reviewers to distinguish envelope readiness from physical-body readiness.
- Manual QA now asks reviewers to confirm Guided Review warns when envelope targets exist but no physical-body target contract exists.
- Manual QA now asks reviewers to confirm the physical-body readiness reason points to missing closed Subassembly shape/material contracts.
- `2026-06-21`: validated by checklist string checks.

Acceptance:

- manual QA can verify that Digital Twin physical-body readiness is not confused with envelope/visual readiness.

### Phase 6 Target 8 - Closed shape material prerequisite diagnostics

Goal:

- block physical-body Watertight Solid targets when evaluated closed Subassembly shapes lack material contracts.

Implementation status:

- `2026-06-21`: started.
- `SolidTargetDiscoveryService` now emits `subassembly_target_missing_material` diagnostics when Subassembly body targets have closed shape profiles but no material ref.
- Subassembly physical-body targets with missing material refs now remain `blocked` instead of `available`.
- The diagnostic message points reviewers toward the missing material contract required for Digital Twin physical-body solid generation.
- `2026-06-21`: validated with FreeCADCmd.

Acceptance:

- closed shape geometry alone is not treated as sufficient physical-body readiness when material contract data is missing.

### Phase 6 Target 9 - Closed shape station continuity diagnostics

Goal:

- block physical-body Watertight Solid targets when closed Subassembly shape profiles are missing within the target station span.

Implementation status:

- `2026-06-21`: started.
- `SolidTargetDiscoveryService` now compares closed-shape target profile stations against Applied Section stations inside the target span.
- The service now emits `subassembly_shape_target_missing_profile` diagnostics when a closed shape profile is missing at an Applied Section station in the target span.
- Subassembly physical-body targets with missing closed shape profiles now remain `blocked`.
- `2026-06-21`: validated with FreeCADCmd.

Acceptance:

- physical-body readiness requires closed shape profiles to be continuous across the target station span, not merely present at the start and end.

### Phase 6 Target 10 - Digital Twin readiness summary

Goal:

- summarize overall Watertight Solid readiness and physical-body readiness as one Digital Twin readiness status.

Implementation status:

- `2026-06-21`: started.
- Build Corridor Watertight Solid readiness properties now expose `WatertightSolidDigitalTwinReadinessStatus`.
- Build Corridor readiness properties now expose `WatertightSolidDigitalTwinReadinessSummary`.
- Guided Review Watertight Solid notes now include `digital_twin_readiness`.
- Digital Twin readiness summary is computed after missing prerequisite and blocked target rows so blocked cases include the correct counts.
- `2026-06-21`: validated with FreeCADCmd.

Acceptance:

- users can see whether ordinary-road output is actually ready for Digital Twin-oriented physical-body watertight solids, even when envelope readiness is otherwise ready.

### Phase 6 Target 11 - Digital Twin readiness QA checklist alignment

Goal:

- keep manual QA aligned with Digital Twin readiness summary and closed shape continuity diagnostics.

Implementation status:

- `2026-06-21`: started.
- Manual QA now asks reviewers to confirm `digital_twin_readiness` is blocked when physical-body readiness is blocked, even if envelope readiness is ready.
- Manual QA now asks reviewers to confirm `WatertightSolidDigitalTwinReadinessSummary` reports overall readiness, physical-body readiness, missing prerequisite count, and blocked target count.
- Manual QA now asks reviewers to confirm closed Subassembly shape profiles exist at every Applied Section station inside the target span.
- Manual QA now asks reviewers to remove an intermediate closed shape profile and confirm `subassembly_shape_target_missing_profile` identifies the missing station.
- `2026-06-21`: validated by checklist string checks.

Acceptance:

- manual QA can verify the Digital Twin readiness gate and station-continuity diagnostics without relying only on automated tests.

### Phase 6 Target 12 - Phase 6 completion review

Goal:

- summarize the Phase 6 Watertight Solid readiness gate work and identify follow-up implementation tracks.

Implementation status:

- `2026-06-21`: started.
- Phase 6 now has Build Corridor readiness properties for target class counts, station spans, Region refs, material refs, missing prerequisites, blocked targets, physical-body readiness, and Digital Twin readiness.
- Phase 6 now has Guided Review notes and warnings for Watertight Solid readiness and physical-body readiness.
- Phase 6 now has SolidTargetDiscovery diagnostics for missing material contracts and missing closed shape profiles inside the target station span.
- Manual QA now covers Watertight Solid readiness, Digital Twin readiness, physical-body readiness, material contracts, and closed shape continuity.

Follow-up tracks:

- Implement physical watertight solid generation quality checks after target readiness is accepted.
- Improve Subassembly Designer and Assembly/Subassembly UX for material and closed shape contracts.
- Add physical-body-ready sample presets for ordinary road templates.
- Extend the same source/result/output readiness pattern to intersection and ramp domains.
- `2026-06-21`: validated by completion-review string checks.

Acceptance:

- Phase 6 readiness-gate work is summarized separately from later physical solid generation work.

### Phase 6 Target 13 - Physical-body-ready ordinary road sample preset

Goal:

- add an ordinary-road sample Assembly/Subassembly preset that carries explicit physical-body material and thickness contracts.

Implementation status:

- `2026-06-21`: started.
- Added `Full Set Road` to shared Assembly/Subassembly preset data.
- The preset intentionally excludes `pavement_layer:main` and `subbase:main` while current physical-body authoring is held out of scope.
- The preset keeps lane, shoulder, gutter, sidewalk, ditch, and side-slope rows so users can review ordinary road surface and drainage behavior.
- `2026-06-21`: renamed `Digital Twin Ready Road` to `Full Set Road`; sidewalk links to `subassembly-definition:sidewalk-basic`, and ditch links to `subassembly-definition:ditch-trapezoid` from `Starter Road Primitives`.
- `2026-06-21`: validated with FreeCADCmd.

Acceptance:

- users have a starter ordinary-road preset that is closer to the Watertight Solid physical-body readiness contract than visual-only road presets.

### Phase 6 Target 14 - Physical-body-ready preset QA checklist alignment

Goal:

- make the `Full Set Road` preset part of the manual QA flow.

Implementation status:

- `2026-06-21`: started.
- Manual QA now asks reviewers to load the `Full Set Road` Assembly/Subassembly preset.
- Manual QA now asks reviewers to confirm the preset includes pavement_layer, subbase, lane, shoulder, and side-slope rows.
- Manual QA now asks reviewers to confirm pavement/subbase rows carry material, thickness, `solid_family`, and `shape_code` contracts for physical-body readiness.
- `2026-06-21`: validated by checklist string checks.

Acceptance:

- manual QA can verify the new physical-body-ready ordinary-road sample preset before running Build Corridor readiness checks.

### Phase 6 Target 15 - Physical-body-ready preset discovery validation

Goal:

- verify that the `Full Set Road` preset reaches Applied Sections as a full ordinary-road surface/drainage review sample.

Implementation status:

- `2026-06-21`: started.
- Added a contract test that builds Applied Sections from the `Full Set Road` preset at two stations.
- The test runs `SolidTargetDiscoveryService` and confirms pavement, subbase, and shoulder physical-body targets are discovered.
- The test confirms pavement and subbase material contracts survive the preset -> Applied Sections -> SolidTargetDiscovery handoff.
- `2026-06-21`: validated with FreeCADCmd.

Acceptance:

- the physical-body-ready preset is not only visible in the UI list; it can also produce available physical-body solid target candidates in the result pipeline.

### Phase 6 Target 16 - Phase 6 final handoff summary

Goal:

- close the ordinary-road Watertight Solid readiness-gate phase and narrow follow-up work to physical solid generation quality.

Implementation status:

- `2026-06-21`: started.
- Phase 6 readiness gates now distinguish envelope readiness, physical-body readiness, and Digital Twin readiness.
- Physical-body readiness now requires material contracts and continuous closed Subassembly shape profiles across target station spans.
- Build Corridor Guided Review now shows Watertight Solid readiness and warns for blocked or partial readiness.
- `Full Set Road` now provides an ordinary-road full Assembly/Subassembly sample and validates through Applied Sections.

Remaining follow-up:

- implement physical watertight solid generation quality checks after accepted target readiness.
- improve Subassembly Designer and Assembly/Subassembly UX for authoring material and closed shape contracts.
- extend the same readiness-gate pattern to intersection and ramp physical-body targets.
- `2026-06-21`: validated by final handoff string checks.

Acceptance:

- Phase 6 readiness-gate scope is complete enough to hand off to physical solid generation work without confusing readiness diagnostics with actual solid construction.

## 14. Phase 7 Implementation Record

### Phase 7 Target 1 - Physical solid target-family traceability QA

Goal:

- block physical watertight solid simulation QA when built solid outputs lack target-family contracts.

Implementation status:

- `2026-06-21`: started.
- `WatertightSimulationQaService` now emits `solid_output_missing_target_family` when a built solid has no target family contract.
- Simulation readiness now requires target-family traceability diagnostics to be error-free.
- The diagnostic points to the affected output ref and explains that `target_families` is required for Digital Twin traceability.
- `2026-06-21`: validated with FreeCADCmd.

Acceptance:

- valid-looking physical solids cannot pass simulation QA without an explicit target-family contract.

### Phase 7 Target 2 - Physical solid source-ref traceability QA

Goal:

- warn when built watertight solid outputs have target-family contracts but no source/result refs.

Implementation status:

- `2026-06-21`: started.
- `WatertightSimulationQaService` now emits `solid_output_missing_source_refs` when a built solid has target families but no Subassembly, structure, flow route, or source refs.
- The diagnostic is a warning so geometry validity can still be assessed while traceability debt remains visible.
- `2026-06-21`: validated with FreeCADCmd.

Acceptance:

- physical solid QA reports traceability gaps even when the built solid has a valid target-family contract.

### Phase 7 Target 3 - Physical solid traceability QA checklist alignment

Goal:

- align manual QA with physical solid target-family and source-ref traceability diagnostics.

Implementation status:

- `2026-06-21`: started.
- Manual QA now asks reviewers to confirm `solid_output_missing_target_family` when a built solid has no target-family contract.
- Manual QA now asks reviewers to confirm `solid_output_missing_source_refs` when a built solid has target families but no Subassembly, structure, flow route, or source refs.
- Manual QA now asks reviewers to confirm valid-looking solids are not accepted as Digital Twin-ready when target-family traceability is missing.
- `2026-06-21`: validated by checklist string checks.

Acceptance:

- manual QA can verify physical solid traceability diagnostics without relying only on automated tests.

### Phase 7 Target 4 - Simulation QA status summary diagnostic visibility

Goal:

- expose Simulation QA diagnostic totals and leading diagnostic ids in the Watertight Solids panel status summary.

Implementation status:

- `2026-06-21`: started.
- Watertight Solids status text now reports diagnostic count, error count, warning count, and up to five leading diagnostic ids.
- Existing panel/package contract coverage now checks that missing drainage and structure diagnostics are visible in the status text.
- `2026-06-21`: validated with FreeCADCmd direct status-summary helper check.

Acceptance:

- reviewers can see why Simulation QA is blocked without opening the diagnostics table first.

### Phase 7 Scope Alignment - Deferred deep physical solid geometry QA

Goal:

- keep the current Watertight Solid work focused on readiness, traceability, material contracts, closed-shape contracts, and QA visibility.
- defer deep physical solid geometry diagnostics until intersections, ramps, drainage, and structures are more stable.

Implementation status:

- `2026-06-21`: documented the scope hold.
- Deep physical solid geometry QA is not expanded in this stage unless explicitly requested.
- Current retained scope remains target-family traceability, source/result refs traceability, material contract visibility, closed-shape profile contract visibility, readiness gates, and Simulation QA status visibility.
- Deferred scope includes non-manifold checks, self-intersection checks, shell repair, boolean/fuse robustness tuning, and final simulation-grade solid reconstruction strategy.

Acceptance:

- the plan no longer directs the next work toward deeper physical solid geometry QA.
- remaining work can prioritize intersection, ramp, drainage, and structure source/result stabilization first.

### Phase 7 Target 5 - Assembly/Subassembly physical-body contract UX

Goal:

- make physical-body material, thickness, shape-code, and solid-family contract readiness visible in the Assembly/Subassembly selected-row detail view.

Implementation status:

- `2026-06-21`: started.
- Selected Subassembly Detail now reports a `Physical-body contract` summary for pavement_layer, subbase, lane, and shoulder rows.
- The summary reports ready/incomplete status plus shape_code, solid_family, material, thickness, and missing contract fields.
- Non-physical body rows report that the contract is not applicable instead of implying Solid geometry readiness.
- `2026-06-21`: validated with FreeCADCmd.

Acceptance:

- users can review physical-body contract readiness without inspecting hidden table columns.
