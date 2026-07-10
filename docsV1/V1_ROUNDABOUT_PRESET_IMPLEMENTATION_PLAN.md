# V1 Roundabout Preset Implementation Plan

## Purpose

Implement the `Roundabout - Single Lane` preset as a dedicated v1 roundabout geometry workflow.

The roundabout must not be modeled as ordinary corridor lane, shoulder, subgrade, and side-slope geometry passing through an intersection area with a circular surface added on top.

The correct v1 direction is:

- ordinary approach corridor geometry stops at the roundabout approach boundary
- the roundabout owns its own central island, circulatory roadway, apron/shoulder, connector, splitter, slope, and subgrade result contracts
- approach and roundabout results meet through explicit shared breaklines

This plan replaces the earlier first-slice roundabout implementation plan with a source-driven dedicated geometry plan.

## Scope

This plan covers:

- `Roundabout - Single Lane` source policy cleanup
- ordinary corridor clipping at roundabout approach boundaries
- dedicated roundabout pavement, shoulder/apron, slope, and subgrade contracts
- entry/exit connector and splitter-island transitions
- shared breaklines between approach corridor results and roundabout results
- Results, Intersections, Breakline Audit, Visibility, and manual QA updates
- FreeCADCmd regression tests

This plan does not cover:

- multi-lane roundabouts
- traffic capacity analysis
- sign and marking design
- drainage hydraulic sizing
- vehicle swept path simulation
- construction phasing

## Core Rule

Roundabout geometry must be generated from `IntersectionModel` roundabout source policy and evaluated result contracts.

Generated meshes, preview objects, existing tree objects, or ordinary corridor output surfaces must not become source truth.

Fallback geometry is allowed only when it is:

- explicit
- diagnostic
- traceable
- kept out of accepted source intent

## Current Problem

The current roundabout implementation still allows ordinary corridor geometry to pass through the roundabout area.

Observed issues:

- ordinary lane, shoulder, and subgrade surfaces enter the circular roundabout control area
- the roundabout circulatory surface is added near or over those ordinary corridor outputs
- entry/exit and tie slope surfaces are only partial transition patches
- ordinary subgrade still behaves as a continuous road strip instead of a roundabout-specific subgrade
- Breakline Audit can report ready while the ownership model is still visually and architecturally wrong

This means the current result is not a true roundabout model. It is a corridor crossing with roundabout-like overlays.

## Current Manual QA Gap

Phase 10 FreeCADCmd smoke confirms the minimum v1 contracts are generated, but manual QA showed the current visual output is still not the intended four-approach roundabout.

Observed remaining gaps:

- The central annular/circular roundabout surface is present, but approach transitions are not generated symmetrically for all four approach directions.
- Entry/exit connector, splitter island, subgrade, and slope handoff outputs appear to be driven too much by the two source alignments instead of the four physical approach legs.
- Some connector/slope output is visible only on diagonal/opposite approach pairs while other approach directions remain visually open or weakly connected.
- Back-side inspection shows dedicated roundabout geometry exists, but the approach-to-roundabout handoff is not yet consistently closed around the whole ownership boundary.
- Shared Boundary Graph readiness does not yet prove that every approach leg has a complete approach clip, connector, splitter, subgrade, and slope handoff chain.

Root interpretation:

- A roundabout built from two crossing alignments must be evaluated as four approach legs:
  - primary start approach
  - primary end approach
  - secondary start approach
  - secondary end approach
- The current implementation still behaves like a two-alignment intersection in parts of the transition logic.
- The next implementation slice must promote approach-leg decomposition to an explicit roundabout result contract instead of deriving connector geometry directly from alignment-level assumptions.

## Target Behavior

For `Roundabout - Single Lane`, Build Parametric should produce these dedicated output families:

- `Roundabout Central Island`
- `Roundabout Circulatory Surface`
- `Roundabout Apron / Shoulder Surface`
- `Roundabout Slope Face Surface`
- `Roundabout Subgrade Surface`

Entry/exit connector source candidates may remain as evaluated boundary/context rows, but the earlier transitional `Roundabout Entry Exit Surface`, `Roundabout Entry/Exit Connector Surface`, `Roundabout Splitter Island Surface`, generic `Intersection Tie Slope Surface`, and generic `Intersection Slope Face Surface` outputs are not production outputs for the generalized roundabout workflow.

Roundabouts use the dedicated `Roundabout Slope Face Surface` output. The generic `Intersection Slope Face Surface` remains a T/Cross intersection output and must be removed or marked `not_applicable` when the intersection kind is `roundabout`.

`Roundabout Slope Face Surface` must suppress all approach handoff sectors, not only the primary-road connector sector. The suppression spans are derived from connector, approach clip, subgrade clip, and slope handoff boundary roles. Primary and secondary physical approach legs must therefore be decomposed into four approach directions before the slope-face ring is built:

- primary start
- primary end
- secondary start
- secondary end

If the secondary control leg is evaluated as another 0/180-degree primary axis, the roundabout slope-face ring will remain across the secondary approach and create extra geometry where the approach road should own the handoff. The topology contract must preserve secondary approach direction as the 90/270-degree axis.

The ordinary corridor outputs should be clipped or suppressed inside the roundabout ownership area:

- Design Surface: clipped at approach-to-roundabout boundary
- Slope Face Surface: clipped at approach slope handoff boundary
- Subgrade Surface: clipped at approach-to-roundabout subgrade boundary
- lane/shoulder preview output: used only as approach context, not accepted roundabout geometry

## Geometry Ownership

### Source Owners

`IntersectionModel` owns:

- roundabout kind
- participating legs
- central island policy
- circulatory lane width
- apron / shoulder width
- entry/exit connector policy
- splitter island policy
- roundabout subgrade policy
- radial grading policy
- shared breakline ownership policy

`Alignment`, `Profile`, `Region`, `Assembly/Subassembly`, and `Applied Sections` provide approach context only.

They do not own roundabout interior geometry.

### Result Owners

Roundabout evaluation owns:

- central island boundary
- circulatory inner and outer boundary
- apron / shoulder boundary
- entry/exit connector boundaries
- splitter island boundaries
- approach clip boundaries
- roundabout subgrade boundaries
- roundabout slope / tie slope boundaries
- shared breakline rows

### Output Owners

Build Parametric owns generated output objects:

- roundabout design/pavement surfaces
- roundabout subgrade surface
- roundabout slope and tie slope surfaces
- review highlights
- diagnostics

Output objects must remain traceable to:

- intersection id
- leg id
- boundary role
- source policy row
- applied section approach context where consumed

## Implementation Phases

### Phase 0. Cleanup and Guardrails

Status: In progress

Tasks:

- Mark earlier roundabout overlay outputs as transitional until the dedicated model replaces them.
- Remove or disable roundabout logic that reuses T/Cross-only assumptions.
- Keep already useful source-policy and annular-boundary code only if it remains source-driven.
- Add diagnostics when ordinary corridor geometry enters the roundabout ownership area.

Progress:

- Added ordinary Design/Subgrade/Slope Face preview metadata that reports triangle intrusion into the roundabout ownership radius.
- Added Results-row warning notes for roundabout ownership intrusion.
- Added a FreeCADCmd smoke target for the first guardrail slice.
- Disabled T/Cross-style `intersection_tie_slope_window` review rows for roundabout contracts.
- Marked first-slice roundabout entry/exit and tie-slope output rows as transitional in Results notes.
- Removed the transitional `Roundabout Entry Exit Surface` preview output from roundabout Build Parametric generation.
- Removed the generic `Intersection Tie Slope Surface` preview output from roundabout Build Parametric generation.
- Removed the generic `Intersection Slope Face Surface` preview output from roundabout Build Parametric generation.
- Removed transitional entry/exit and connector-to-tie-slope roles from roundabout shared-boundary graph promotion.
- This phase does not clip geometry yet. Phase 2 consumes this diagnostic to suppress ordinary corridor surfaces inside the roundabout boundary.

Acceptance criteria:

- No T/Cross intersection tie-slope rule is selected for roundabouts.
- Roundabout debug/highlight objects are not presented as final production output.
- The plan clearly distinguishes transitional objects from accepted roundabout results.
- Ordinary corridor surface intrusion into the roundabout ownership area is visible as a diagnostic before clipping is implemented.

### Phase 1. Roundabout Ownership Boundary

Status: In progress

Tasks:

- Define an authoritative roundabout ownership boundary from source policy:
  - central island radius
  - circulatory outer radius
  - apron / shoulder width
  - entry/exit connector extent
  - splitter island extent
  - approach clip station per leg
- Store boundary result rows with stable roles:
  - `roundabout_outer_ownership_boundary`
  - `roundabout_approach_clip_boundary`
  - `roundabout_subgrade_clip_boundary`
  - `roundabout_slope_handoff_boundary`
- Add self-crossing, closed-loop, and leg-contact diagnostics.

Progress:

- Added source-policy boundary loop rows for `roundabout_outer_ownership_boundary`.
- Added per-approach rectangular boundary loop rows for:
  - `roundabout_approach_clip_boundary`
  - `roundabout_subgrade_clip_boundary`
  - `roundabout_slope_handoff_boundary`
- Added contract coverage so the new boundary rows advertise their expected consumers without yet changing ordinary corridor clipping behavior.
- Added a FreeCADCmd regression target that confirms the new ownership, clip, subgrade, and slope handoff loops are closed and have positive area.

Acceptance criteria:

- A closed ownership boundary can be highlighted around the full roundabout.
- Each participating leg has an approach clip boundary.
- The boundary is generated from source/evaluation data, not from generated surfaces.

### Phase 2. Ordinary Corridor Clipping

Status: In progress

Tasks:

- Clip or suppress ordinary Design Surface triangles inside the roundabout ownership boundary.
- Clip or suppress ordinary Slope Face Surface triangles inside the roundabout slope ownership boundary.
- Clip or suppress ordinary Subgrade Surface triangles inside the roundabout subgrade ownership boundary.
- Preserve approach edges as shared breakline consumers instead of deleting traceability.
- Add diagnostics:
  - `roundabout_design_clip_ready`
  - `roundabout_slope_clip_ready`
  - `roundabout_subgrade_clip_ready`
  - `roundabout_clip_missing_boundary`
  - `roundabout_clip_orphan_triangle`

Acceptance criteria:

- Ordinary lane/shoulder/subgrade geometry no longer passes through the roundabout.
- Approach corridor output stops cleanly at roundabout clip boundaries.
- No clipping is based on visual overlap with generated roundabout meshes.

Progress:

- Added centralized ordinary-surface suppression for roundabout ownership intrusion.
- Design Surface, Subgrade Surface, and Slope Face Surface now remove triangles whose centroids fall inside the source-policy ownership radius.
- Added preview metadata:
  - `RoundaboutOwnershipClipStatus`
  - `RoundaboutOwnershipClippedTriangleCount`
  - `RoundaboutOwnershipClipTestedTriangleCount`
  - `RoundaboutOwnershipClipMode`
  - `RoundaboutOwnershipClipReasonSummary`
  - `RoundaboutOwnershipClipCentroidInsideCount`
  - `RoundaboutOwnershipClipVertexInsideCount`
  - `RoundaboutOwnershipClipEdgeCrossesCount`
  - `RoundaboutOwnershipClipCenterInsideTriangleCount`
- Connected ordinary surface clipping metadata to evaluated boundary-loop contracts:
  - Design Surface consumes `roundabout_approach_clip_boundary`
  - Subgrade Surface consumes `roundabout_subgrade_clip_boundary`
  - Slope Face Surface consumes `roundabout_slope_handoff_boundary`
- Added preview metadata for the consumed boundary result:
  - `RoundaboutClipBoundaryStatus`
  - `RoundaboutClipBoundaryRole`
  - `RoundaboutClipBoundaryLoopCount`
  - `RoundaboutClipBoundarySegmentCount`
- Promoted clip boundary loops to explicit `SharedBreaklineResult` rows:
  - `roundabout_approach_clip_to_design_surface`
  - `roundabout_subgrade_to_approach_subgrade`
  - `roundabout_slope_to_corridor_slope_face`
- Restricted the new clip breaklines to ordinary-surface consumers so existing roundabout annular Intersection Surface shared-breakline counts remain stable.
- Added regression coverage that verifies the new shared breakline roles, consumers, and `roundabout_ordinary_surface_clip` handoff target.
- Surfaced roundabout clip boundary diagnostics in Breakline Audit rows:
  - default surface rows now include `roundabout_clip_boundary=<role>:<status>`
  - default surface rows now include clip mode and reason summary
  - internal audit rows expose a `Roundabout Clip Boundary` handoff detail row
  - Subgrade Surface is included when it has roundabout clip metadata even if it does not yet have a full shared-breakline audit result
- Updated the roundabout guardrail regression test so clipping evidence is expected instead of ownership intrusion warnings.
- Replaced centroid-only triangle suppression with source-policy circle-intersection clipping:
  - centroid inside ownership circle
  - vertex inside ownership circle
  - triangle edge crossing ownership circle
  - ownership center contained by a triangle
- Added FreeCADCmd coverage for clip mode and clip reason counts.

Remaining:

- Manually validate that ordinary Design/Subgrade/Slope Face previews stop cleanly at the roundabout approach, subgrade, and slope handoff boundaries.
- If visual clipping still leaves partial boundary artifacts, add true polygon clipping instead of whole-triangle suppression.

### Phase 3. Dedicated Roundabout Surface Zones

Status: In progress

Tasks:

- Create production surface-zone roles:
  - `roundabout_central_island`
  - `roundabout_circulatory_lane`
  - `roundabout_truck_apron`
  - `roundabout_outer_shoulder`
  - `roundabout_entry_exit_connector`
- Do not create `roundabout_splitter_island` source-zone, edge-network, boundary-loop, or production-output contracts until splitter islands have an explicit source model.
- Keep these zones separate from ordinary `lane`, `shoulder`, and `side_slope` roles.
- Replace rectangular/ordinary intersection surface behavior with annular and connector-specific zones.

Progress:

- Replaced the transitional `roundabout_circulatory_pavement` surface-zone role with `roundabout_circulatory_lane`.
- Replaced the transitional `roundabout_entry_exit_pavement` surface-zone role with `roundabout_entry_exit_connector`.
- Added explicit roundabout source-zone rows for:
  - `roundabout_truck_apron`
  - `roundabout_outer_shoulder`
- Kept `roundabout_entry_exit_connector` and `roundabout_outer_shoulder` as diagnostic/source-zone contracts until their dedicated geometry phases are implemented.
- Removed splitter-island diagnostic/source-zone contracts from the roundabout preset. Splitter islands need a dedicated source model before they return as production or diagnostic contracts.
- Updated boundary-loop consumer expectations so roundabout entry/exit boundaries no longer point to removed transitional production outputs.

Acceptance criteria:

- Results and Intersections tabs expose roundabout-specific production roles.
- No roundabout interior role is named or treated as ordinary corridor lane/shoulder.
- Surface-zone diagnostics identify missing source policy rows.

### Phase 4. Circulatory and Apron Surfaces

Status: In progress

Tasks:

- Build circulatory lane as an annular strip between inner and outer circular/arc boundaries.
- Build truck apron / shoulder as a separate annular or segmented strip if policy enables it.
- Use stable radial sample ordering.
- Apply roundabout radial grading policy.
- Preserve breakline roles:
  - `roundabout_island_to_circulatory`
  - `roundabout_circulatory_to_apron`
  - `roundabout_apron_to_slope_face`

Progress:

- Added a dedicated `Roundabout Apron Surface` output object.
- The apron is generated from source/evaluation boundary loops, not from generated mesh:
  - inner loop: `roundabout_circulatory_outer_boundary`
  - outer loop: `roundabout_outer_ownership_boundary`
- Updated roundabout slope-face generation so it starts at `roundabout_outer_ownership_boundary` when available.
- Updated shared breakline roles from the transitional direct `roundabout_circulatory_to_slope_face` handoff to:
  - `roundabout_circulatory_to_apron`
  - `roundabout_apron_to_slope_face`
- Added Results tab reporting for `Roundabout Apron Surface`.
- Added tree-routing and regression coverage for the apron output under the Intersections group.

Acceptance criteria:

- The visible circulatory surface is circular/annular, not rectangular.
- Apron/shoulder output is distinguishable from circulatory lane output.
- Shared Breakline Audit reports the annular boundaries as consumed.

### Phase 5. Entry / Exit and Splitter Geometry

Status: In progress

Tasks:

- Keep entry and exit connector boundary contracts as internal diagnostics from:
  - approach clip boundary
  - circulatory outer contact arc
  - connector source policy
- Build splitter island surfaces where source policy exists.
- Use Applied Sections only as approach context at the corridor side of the boundary.
- Do not reuse ordinary lane/shoulder strips inside the roundabout.

Progress:

- Removed the dedicated `Roundabout Entry/Exit Connector Surface` production output because it duplicated/overlapped the corridor approach connector area.
- `roundabout_entry_exit_connector_boundary` remains an internal source/evaluation contract for diagnostics and future approach handoff design.
- The transitional `Roundabout Entry Exit Surface` output remains disabled and is not reused.
- Connector shared breaklines remain registered as internal graph contracts with:
  - `roundabout_entry_exit_connector`
  - `design_surface`
  - `roundabout_circulatory_surface`
- Removed splitter-island source policy rows, splitter edge-network rows, `roundabout_splitter_island_boundary` boundary-loop contracts, splitter source-zone rows, splitter shared-breakline consumers, and the `Roundabout Splitter Island Surface` output object.
- Splitter-island geometry is deferred until a source-owned splitter-island model exists.

Acceptance criteria:

- Each leg has entry/exit connector surfaces that meet the circulatory boundary.
- Splitter-island contracts are absent unless a future explicit splitter-island source model is introduced.
- Connector surfaces consume shared breaklines with both approach Design Surface and roundabout surfaces.
- Splitter surfaces consume shared breaklines with approach Design Surface without becoming ordinary corridor shoulder geometry.

### Phase 6. Roundabout Subgrade Surface

Status: Complete

Tasks:

- Done: Added `Roundabout Subgrade Surface` as a dedicated output contract.
- Done: Built the dedicated subgrade from the authoritative `roundabout_outer_ownership_boundary` loop.
- Done: Reused `roundabout_subgrade_clip_boundary` as the shared handoff between ordinary approach subgrade and dedicated roundabout subgrade.
- Done: Routed the generated object under the Intersections tree group.
- Done: Exposed the output in the Results tab and roundabout breakline readiness summary.
- Done: Promoted the 0.30 m subgrade depth into an explicit `roundabout_subgrade_depth` preset source policy row.

Acceptance criteria:

- Roundabout subgrade is generated as its own object under the Intersections group.
- Breakline Audit distinguishes approach subgrade from roundabout subgrade with `roundabout_subgrade_to_approach_subgrade`.
- The generated subgrade surface reports `roundabout_subgrade_depth_policy` as its depth source for preset-created roundabouts.
- FreeCADCmd smoke confirms the dedicated subgrade object is ready and shared-breakline audit reports zero geometry, mesh, and missing-consumer mismatches.

### Phase 7. Roundabout Slope and Tie Slope

Status: Complete

Tasks:

- Generate slope and tie slope surfaces outside the roundabout pavement/apron/connector zones.
- Use approach Applied Section side-slope edges only at approach handoff boundaries.
- Generate roundabout-specific side-slope strips around exposed outer boundaries.
- Keep ordinary Slope Face Surface separate from dedicated roundabout slope outputs.

Progress:

- Added an explicit `roundabout_slope_face_width` source policy row to the Roundabout preset.
- `Roundabout Slope Face Surface` now records `RoundaboutSlopeFaceWidthSource` so the generated strip width is traceable to preset source intent instead of an implicit builder fallback.
- Current production slope strips remain dedicated roundabout outputs and are not mixed into ordinary `Slope Face Surface`.
- Renamed the roundabout ordinary-surface handoff breakline roles to the Phase 8 canonical names:
  - `roundabout_subgrade_to_approach_subgrade`
  - `roundabout_slope_to_corridor_slope_face`
  Existing legacy role names remain accepted as compatibility aliases.

Acceptance criteria:

- Roundabout slope/tie slope fills exterior transition gaps without entering the circulatory lane.
- The source of each slope strip is traceable to a roundabout boundary role or approach handoff boundary.
- T/Cross-specific tie slope windows are not used for roundabout production output.

### Phase 8. Shared Breakline Audit

Status: In Progress

Tasks:

- Register roundabout shared boundary roles:
  - `roundabout_island_to_circulatory`
  - `roundabout_circulatory_to_apron`
  - `roundabout_apron_to_slope_face`
  - `roundabout_entry_exit_connector_boundary`
  - `roundabout_subgrade_to_approach_subgrade`
  - `roundabout_slope_to_corridor_slope_face`
- Ensure all generated roundabout surfaces consume canonical edge ids.
- Add actionable recommended actions for missing consumers, reversed edges, and unmatched boundaries.

Progress:

- Registered canonical roundabout ordinary-surface handoff roles in the shared boundary graph:
  - `roundabout_approach_clip_to_design_surface`
  - `roundabout_subgrade_to_approach_subgrade`
  - `roundabout_slope_to_corridor_slope_face`
- Kept the earlier builder-oriented role names as compatibility aliases only.
- Updated regression coverage so new shared breakline rows use the canonical Phase 8 role names.
- Deduplicated roundabout boundary-loop and ordinary-surface clip shared breakline rows by canonical role and endpoint pair before converting them into Shared Boundary Graph edges.
- Verified the roundabout Shared Boundary Graph reports `ready` with duplicate edges `0` and missing consumers `0`.

Acceptance criteria:

- Breakline Audit reports ready for accepted roundabout surfaces.
- Missing or mismatched boundaries identify exact roundabout roles.
- Double-click highlights stay local to the roundabout.

### Phase 9. Output Tree, Visibility, and UI

Status: Complete

Tasks:

- Route all production roundabout outputs under `04_Parametric Model > Intersections`.
- Keep debug/highlight objects separate from production objects.
- Update Results tab rows:
  - `Roundabout Circulatory Surface`
  - `Roundabout Apron Surface`
  - `Roundabout Subgrade Surface`
  - `Roundabout Slope Face Surface`
  - `Roundabout Breakline Readiness`
- Update Visibility tab with roundabout output toggles only if the existing grouped visibility cannot cover them clearly.

Progress:

- Routed production roundabout output previews under `04_Parametric Model > Intersections`.
- Results tab now exposes production roundabout rows for circulatory, entry/exit connector, splitter island, apron, subgrade, slope face, and breakline readiness.
- Internal/debug contracts remain hidden from the default Intersections tab while still available through internal review.
- Added the production roundabout preview objects to the existing `Intersection` grouped visibility control instead of adding a separate one-off roundabout toggle.
- Added FreeCADCmd regression coverage for output tree routing, production Results rows, Intersections tab filtering, and grouped visibility routing.

Acceptance criteria:

- The user can hide/show the Intersections group and affect all production roundabout outputs.
- Results rows distinguish missing, warning, ready, and blocked states.
- Internal/debug rows are not shown as production rows.

### Phase 10. Validation and Manual QA

Status: Complete

Tasks:

- Add FreeCADCmd tests for:
  - ownership boundary generation
  - ordinary Design Surface clipping
  - ordinary Slope Face Surface clipping
  - ordinary Subgrade Surface clipping
  - annular circulatory surface
  - entry/exit connector surfaces
  - roundabout subgrade surface
  - shared breakline consumption
  - object tree grouping
- Add manual QA steps with expected visual checks.
- Document known limitations.

Progress:

- Added a full `Roundabout - Single Lane` smoke regression that builds Applied Sections, ordinary corridor outputs, dedicated roundabout outputs, Results rows, Breakline Audit rows, and Intersections tree routing in one flow.
- The smoke verifies ordinary Design, Subgrade, and Slope Face outputs are clipped at the roundabout ownership boundary and report zero ownership intrusion triangles.
- The smoke verifies production roundabout outputs are present for:
  - circulatory intersection surface
  - splitter island surface
  - apron surface
  - subgrade surface
  - slope face surface
- The smoke verifies transitional roundabout entry/exit, entry/exit connector surface, and generic intersection tie-slope outputs remain disabled for roundabout generalization.
- The smoke verifies the shared boundary graph is ready with duplicate edges `0` and missing consumers `0`.
- The smoke verifies production roundabout outputs are routed under `04_Parametric Model > Intersections`, not the document root.

Acceptance criteria:

- FreeCADCmd smoke passes for `Roundabout - Single Lane`.
- Manual QA confirms ordinary lane/shoulder/subgrade do not pass through the roundabout.
- Manual QA confirms dedicated roundabout surfaces fill the roundabout ownership area.

Manual QA checklist:

1. Create `Intersection > Roundabout - Single Lane`.
2. Run Applied Sections, then Build Parametric.
3. In Results, confirm roundabout rows are `ready`:
   - Roundabout Circulatory Surface
   - Roundabout Apron Surface
   - Roundabout Subgrade Surface
   - Roundabout Breakline Readiness
4. In Breakline Audit, confirm:
   - Intersection Surface is `ready`
   - Design Surface is `ready`
   - Slope Face Surface is `ready`
   - geometry mismatch, mesh mismatch, duplicate edge, and missing consumer counts are `0`
   - Shared Boundary Graph is `ready`
5. In Tree View, confirm production roundabout objects are under `04_Parametric Model > Intersections`.
6. Toggle the Visibility tab `Intersection` group and confirm production roundabout outputs hide/show together.
7. In 3D View, confirm ordinary Design/Subgrade/Slope Face surfaces stop at the roundabout ownership boundary and do not pass through the roundabout interior.
8. In 3D View, confirm the dedicated annular circulatory surface, apron, splitter, subgrade, and slope-face outputs fill the roundabout ownership area.

Known limitations:

- This implementation targets the `Roundabout - Single Lane` preset only.
- Entry/exit connector geometry is not generated as a production surface. Its boundary contract remains internal until the approach handoff design is revisited.
- Splitter island geometry is implemented as a first production slice, but still needs manual QA before it should be treated as visually complete.
- Roundabout drainage, advanced superelevation behavior, and watertight solid handoff remain follow-up domains.
- Generated preview/highlight objects remain presentation artifacts and must not be used as source truth.

### Phase 11. Four-Approach Roundabout Generalization

Status: Pending

Purpose:

Make the roundabout transition workflow operate on four physical approach legs instead of only two source alignments.

Scope:

- Introduce a roundabout approach-leg result contract derived from the roundabout `IntersectionModel`.
- Split each participating alignment into directional approach contexts:
  - primary start
  - primary end
  - secondary start
  - secondary end
- For each approach leg, evaluate and store:
  - approach direction vector
  - approach centerline handoff point
  - approach corridor clip boundary
  - circulatory entry/exit tangent point or tangent span
  - connector boundary loop
  - splitter island boundary loop
  - subgrade handoff boundary
  - slope-face handoff boundary
  - shared breakline refs and consumers
- Generate connector, splitter, subgrade, and slope outputs from the approach-leg contracts, not from generated preview geometry.
- Keep ordinary Design/Subgrade/Slope Face clipping centralized at the roundabout ownership boundary.
- Extend Breakline Audit to report approach-leg completeness by leg role.

Implementation order:

1. Add roundabout approach-leg decomposition to the intersection evaluation layer.
2. Add source/result diagnostics for missing or invalid approach leg geometry.
3. Convert connector and splitter boundary-loop builders to consume approach-leg rows.
4. Convert subgrade and slope handoff builders to consume approach-leg rows.
5. Add Shared Boundary Graph roles for each approach leg handoff.
6. Update Results and Breakline Audit rows with approach-leg counts and readiness.
7. Add FreeCADCmd tests for four approach legs and per-leg output completeness.
8. Run manual QA from top and bottom views.

Acceptance criteria:

- `Roundabout - Single Lane` reports four accepted approach-leg rows.
- Connector and splitter output is generated for all four approach directions.
- Ordinary corridor Design/Subgrade/Slope Face outputs stop before the roundabout ownership area in all four directions.
- Roundabout Subgrade and Slope Face handoff rows exist for all four approach legs.
- Breakline Audit identifies per-leg missing handoffs instead of only reporting aggregate graph readiness.
- Top and bottom manual QA views show no asymmetric missing approach transition around the roundabout.

Non-goals:

- Do not reintroduce the disabled transitional `Roundabout Entry Exit Surface`.
- Do not reintroduce generic `Intersection Tie Slope Surface` for roundabout production output.
- Do not derive approach geometry from existing generated mesh or tree preview objects.
- Do not treat visual cleanup patches as accepted roundabout source intent.

Progress:

- Added `IntersectionRoundaboutApproachLegResult` and `IntersectionRoundaboutApproachLegRow` as source/topology-derived contracts.
- Added `IntersectionEvaluationService.evaluate_roundabout_approach_legs()`.
- The first slice decomposes two roundabout source leg spans into four physical approach roles:
  - `primary_start`
  - `primary_end`
  - `secondary_start`
  - `secondary_end`
- Each approach row records direction vector, station span, handoff station, boundary roles, and shared breakline role names.
- Added FreeCADCmd contract coverage for four accepted approach-leg rows on `Roundabout - Single Lane`.
- Converted roundabout connector, splitter, approach-clip, subgrade-clip, and slope-handoff boundary-loop specs to consume approach-leg rows instead of iterating raw topology leg spans.
- Boundary-loop rows now carry approach-leg source refs so downstream builders and audits can trace each loop to `primary_start`, `primary_end`, `secondary_start`, or `secondary_end`.
- Added FreeCADCmd coverage that connector/splitter/clip boundary loops include approach-leg source refs.
- Connector boundary-loop contracts still carry approach-leg refs for traceability, but the connector surface builder is disabled from production output.
- Splitter surface builders now propagate approach-leg refs into TIN source refs and expose approach-leg count, roles, and source as preview metadata.
- Results tab notes now report splitter approach-leg coverage so users can see four-approach completeness without opening internal diagnostics.
- Added FreeCADCmd coverage for splitter preview metadata and Results notes.
- Ordinary Design/Subgrade/Slope roundabout clip boundaries now expose approach-leg count, roles, and source on preview metadata.
- Breakline Audit surface rows and internal Roundabout Clip Boundary detail rows now report per-approach handoff completeness for subgrade and slope-face outputs.
- Added FreeCADCmd coverage for roundabout clip-boundary approach-leg metadata and Breakline Audit notes/detail rows.
- Dedicated Roundabout Subgrade preview now reports approach-leg completeness from subgrade clip loops.
- Dedicated Roundabout Slope Face preview now reports handoff-loop and approach-leg completeness from slope handoff loops.
- Roundabout Entry/Exit Connector Surface is no longer generated as a production preview object.
- Splitter acceptance criteria now require exactly four loops and eight source triangles.
- Added FreeCADCmd coverage for four-approach splitter, subgrade, and slope-face output acceptance metadata.
- Next implementation slice should compare the acceptance metadata with manual top/bottom screenshots and decide whether geometry construction itself needs expansion.

## Implementation Order

1. Add ownership boundary and diagnostics.
2. Clip ordinary corridor design/slope/subgrade outputs at roundabout boundaries.
3. Add dedicated roundabout surface-zone contracts.
4. Build circulatory, apron, connector, and splitter surfaces.
5. Build dedicated roundabout subgrade.
6. Build dedicated roundabout slope and tie slope.
7. Wire shared breaklines.
8. Update Results, Intersections, Breakline Audit, and Visibility.
9. Add FreeCADCmd and manual QA coverage.
10. Generalize connector, splitter, subgrade, and slope handoff generation to four physical approach legs.

## Risks

- Existing ordinary corridor output builders may continue generating triangles inside the roundabout unless clipping is centralized.
- Previous first-slice roundabout objects may look valid but still depend on ordinary corridor geometry.
- Applied Section approach rows are useful at handoff boundaries but can corrupt roundabout ownership if used as interior source truth.
- Subgrade requires a separate roundabout contract; otherwise watertight solid generation will inherit incorrect ordinary corridor strips.
- Aggregate Shared Boundary Graph readiness can hide per-approach missing handoffs unless per-leg diagnostics are exposed.
- Two-alignment assumptions can generate visually asymmetric roundabout transition geometry for a four-approach case.

## Completion Definition

The roundabout preset is considered implemented when:

- ordinary corridor lane/shoulder/slope/subgrade outputs stop at roundabout boundaries
- roundabout interior pavement, apron, connector, splitter, slope, and subgrade outputs are generated from roundabout source contracts
- all four physical approach legs have connector, splitter, subgrade, and slope handoff results
- shared breaklines connect approach outputs and roundabout outputs
- output objects are grouped under the Intersections tree group
- Results and Breakline Audit expose actionable status
- FreeCADCmd smoke and manual QA pass for `Roundabout - Single Lane`
- docs and wiki describe the implemented scope and remaining non-goals
