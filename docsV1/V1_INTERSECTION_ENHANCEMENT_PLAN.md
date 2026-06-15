# Parametric Road V1 Intersection Enhancement Plan

Date: 2026-06-04
Branch: `v1-0503`
Status: Draft enhancement plan after `v1.0.4`
Depends on:

- [V1_MASTER_PLAN.md](./V1_MASTER_PLAN.md)
- [V1_ARCHITECTURE.md](./V1_ARCHITECTURE.md)
- [V1_INTERSECTION_MODEL.md](./V1_INTERSECTION_MODEL.md)
- [V1_INTERSECTION_IMPLEMENTATION_PLAN.md](./V1_INTERSECTION_IMPLEMENTATION_PLAN.md)
- [V1_3D_CENTERLINE_TOOLBAR_PLAN.md](./V1_3D_CENTERLINE_TOOLBAR_PLAN.md)
- [V1_REGION_MODEL.md](./V1_REGION_MODEL.md)
- [V1_SURFACE_MODEL.md](./V1_SURFACE_MODEL.md)
- [V1_BUILD_PARAMETRIC_STABILIZATION_PLAN.md](./V1_BUILD_PARAMETRIC_STABILIZATION_PLAN.md)
- [V1_DRAINAGE_MODEL.md](./V1_DRAINAGE_MODEL.md)
- [V1_WATERTIGHT_SOLID_PLAN.md](./V1_WATERTIGHT_SOLID_PLAN.md)

## 1. Purpose

This document defines the next enhancement plan for the v1 Intersections workflow.

The `v1.0.4` baseline can create or use multi-alignment intersection sources, generate a multi-alignment 3D Centerline preview, carry Alignment-specific 3D Centerline rows into Applied Sections, and show multi-alignment Region rows in Build Parametric.

The next goal is to make intersection geometry and review behavior cleaner, more explicit, and ready for downstream drainage, watertight solids, and simulation workflows.

## 2. Current Baseline

Implemented first slices:

- `Use Existing Alignments` source mode.
- `Create Starter Sources` source mode.
- starter T / Cross / Y source creation.
- Alignment, Profile, Stationing, and Region source generation for starter intersections.
- automatic multi-alignment 3D Centerline preview after starter source creation.
- Applied Sections consumption of Alignment-matched 3D Centerline rows.
- Build Parametric Region Boundaries reading all participating Region source models.
- Build Parametric surface grouping by Alignment before merge.
- Slope Face Surface protection against connecting unrelated Alignment section rows.
- local Wiki documentation for the two Intersections workflows.

Current limits:

- there is no dedicated `Intersection Surface Patch`.
- junction infill is still inferred from ordinary corridor surfaces.
- curb return geometry is not yet generated as a structured source/output.
- intersection crossfall/grading policy is only contextual, not applied as a distinct grading surface.
- drainage recommendations for junction low points are not automated.
- watertight solid targets do not yet include dedicated intersection body or junction patch targets.

## 3. Core Rule

Do not solve intersection geometry by hiding or manually deleting ordinary corridor surface fragments.

Intersection geometry should be owned by structured source intent and generated through explicit result/output contracts.

Ordinary road Regions should still build their own corridor surfaces.

The intersection control area should add or replace only the junction-specific surface and edge relationships.

## 4. Target Workflow

The target user flow is:

1. Create or select participating road sources.
2. Create or apply an Intersection source model.
3. Review multi-alignment 3D Centerline.
4. Build Sections.
5. Build Parametric.
6. Review:
   - Region Boundaries
   - Intersections
   - Intersection Surface Patch
   - Slope Face Issues
   - Drainage context
7. Build downstream outputs or watertight solids only after the junction review is acceptable.

## 5. Object Families

The enhancement work should keep the source/result/output split visible.

Source objects:

- `IntersectionModel`
- `IntersectionRow`
- `IntersectionLegRow`
- `IntersectionControlArea`
- future `CurbReturnPolicyRow`
- future `IntersectionGradingPolicyRow`

Evaluation results:

- `IntersectionEvaluationResult`
- `IntersectionPatchPrerequisiteResult`
- `IntersectionControlAreaSummary`
- `IntersectionDrainageHintResult`

Output objects:

- `intersection_surface`
- `intersection_curb_return_preview`
- `intersection_low_point_hint`
- future `intersection_surface_patch_target`
- future `intersection_pavement_body_target`

Presentation objects:

- Intersections panel overlay
- Build Parametric `Intersection Surface` review row
- Cross Section Viewer intersection context summary
- Watertight Solids intersection target row

Generated presentation objects must stay disposable. They should be regenerated from source and result contracts.

## 6. Enhancement Areas

### 6.1 Intersection Surface Patch

Goal:

Generate an explicit surface over the junction control area.

Scope:

- derive an intersection boundary polygon from participating Region spans
- derive road edge tie-in lines from Applied Section `fg_surface` rows
- clip or avoid ordinary Design Surface fragments inside the patch boundary
- generate a dedicated `intersection_surface` TIN
- expose the result in Build Parametric

Output behavior:

- add a Build Parametric review row: `Intersection Surface`
- route preview objects under `04_Parametric Model / Build Parametric Outputs`
- expose quality rows:
  - patch boundary point count
  - participating Alignment count
  - tie-in edge count
  - clipped design triangle count
  - patch triangle count

Acceptance criteria:

- T-intersection starter sources produce a visible patch over the junction center.
- ordinary Design Surface and Slope Face Surface do not fill the patch area incorrectly.
- Region Boundaries still show primary and side-road Region rows.
- Cross Section Viewer can report that a station is inside an intersection control area.

### 6.2 Curb Return And Corner Radius

Goal:

Represent corner return geometry explicitly instead of leaving the junction edge as a hard overlap.

Source fields:

- `curb_return_policy_ref`
- radius
- side / quadrant
- approach leg refs
- edge role, such as curb, shoulder, ditch, or pavement edge

First implementation:

- support T and Cross intersections
- generate corner arc preview linework
- store policy refs in `IntersectionRow` or policy rows
- expose review diagnostics when radius is too small or cannot connect both legs

Acceptance criteria:

- a starter T-intersection can show two corner return arcs.
- a starter Cross intersection can show four corner return arcs.
- generated arcs are review geometry, not source replacement.

### 6.3 Intersection Crossfall And Grading Policy

Goal:

Control how crossfall behaves inside the intersection area.

Policy options:

- keep primary-road crown
- flatten intersection area
- blend primary and side-road crossfall
- hold side-road approach grade at tie-in

Result behavior:

- Applied Sections should expose intersection grading context.
- Build Parametric should use this context when generating the Intersection Surface Patch.
- Superelevation should remain the source for normal road sections, but intersection policy may override or flatten it inside the control area.

Acceptance criteria:

- Cross Section Viewer shows intersection crossfall/grading context.
- Build Parametric diagnostics report which grading policy was used.
- ordinary Superelevation behavior remains unchanged outside the control area.

### 6.4 Drainage Handoff

Goal:

Make the intersection usable for drainage design.

First implementation:

- detect low-point candidates inside or near the intersection patch
- suggest inlet candidate positions
- report whether Drainage Elements exist for the intersection control Region
- optionally show flow arrows from patch edges to candidate inlets

Acceptance criteria:

- Build Parametric or Drainage Review can report missing drainage context for an intersection Region.
- starter junction examples can show where an inlet would be expected.
- no automatic hydraulic sizing is required.

### 6.5 Region And UI Improvements

Goal:

Make the user understand which Region belongs to which road and why.

UI changes:

- keep `Alignment` column in Region Boundaries.
- add an `Intersection` or `Control Area` filter in Build Parametric.
- add a compact Intersections review table:
  - Intersection ID
  - Kind
  - Primary Alignment
  - Secondary Alignments
  - Control Regions
  - Status
  - Diagnostics

Acceptance criteria:

- the user can select one intersection and highlight all related Regions.
- the user can select one Region and see which intersection, if any, owns its control context.

### 6.6 Watertight Solid Readiness

Goal:

Prepare intersection outputs for future simulation-ready solids.

First target families:

- `intersection_surface_patch`
- `intersection_pavement_body`
- `intersection_subgrade_body`
- later: curb/gutter bodies and drainage inlet integration

Acceptance criteria:

- Watertight Solids can discover intersection patch targets after Build Parametric.
- validation reports when the patch is not closed or lacks enough boundary data.
- no boolean union with the full road body is required in the first slice.

## 7. Implementation Order

This table is the working sequence for implementation.

| Phase | Status | Primary Output | Why First |
|---|---|---|---|
| 1. Diagnostics And Contracts | Done | explicit prerequisites and viewer summaries | prevents hidden surface guesses |
| 2. Intersection Surface Patch | Done | visible junction patch surface | fixes the current overlap/gap problem first |
| 3. Curb Return Preview | Done | corner radius linework and diagnostics | makes the edge shape intentional |
| 4. Crossfall And Grading Policy | Done | patch grading behavior | controls final junction shape |
| 5. Drainage Review Handoff | Done | low-point and inlet context | prepares practical drainage design |
| 6. Watertight Target Discovery | Done | simulation-ready target discovery | connects to the long-term solid goal |

### Phase 1: Diagnostics And Contracts

Status: Done

Implementation status:

- Done: added `IntersectionPatchPrerequisiteResult` as the readiness contract for future `intersection_surface` output.
- Done: added Build Parametric prerequisite summary and diagnostics for missing IntersectionModel, Applied Sections, control Regions, participating alignments, tie-in edges, and boundary point count.
- Done: connected Guided Review `3. Intersections` to patch prerequisite readiness.
- Done: added contract tests for ready and missing prerequisite states.

Tasks:

- define `intersection_surface` output contract fields
- add patch target diagnostics to Build Parametric
- expose intersection control-area summaries in Cross Section Viewer
- add tests for multi-alignment Region and Centerline source matching

Acceptance:

- Build Parametric reports whether patch prerequisites are available.

### Phase 2: Intersection Surface Patch

Status: Done

Implementation status:

- Done: added `Intersection Surface` as a Build Parametric review role.
- Done: added `V1CorridorIntersectionSurfacePreview` as the first disposable patch preview object.
- Done: generated first-slice `intersection_surface` TIN rows from intersection Applied Section `fg_surface` points.
- Done: recorded patch provenance, control Region refs, participating alignment count, tie-in edge count, boundary point count, and triangle count on the preview object.
- Done: added a dedicated visual style for intersection surface previews.
- Done: added FreeCAD smoke coverage for the preview object and review row.
- Done: stabilized T-intersection patch triangulation so the preview uses center-nearest Applied Sections per participating Alignment and a non-self-crossing XY boundary hull instead of fanning every control-Region point.
- Done: corrected T-intersection starter Region generation so the side-road intersection control Region is placed at the side-road end station where it meets the primary road.

Tasks:

- collect participating Applied Section edge rows
- build a first patch boundary
- triangulate the patch
- add Build Parametric preview object and review row
- add diagnostics for missing edges, open boundary, and degenerate triangles

Acceptance:

- T starter source creates a patch surface over the center junction.

### Phase 3: Curb Return Preview

Status: Done

Implementation status:

- Done: added `IntersectionCurbReturnPolicyRow` as the source contract for corner return radius intent.
- Done: persisted curb return policy rows in the FreeCAD `V1IntersectionModel` object.
- Done: created default kind-based curb return policies for Intersections panel output.
- Done: added T/Cross/Y curb return arc preview linework to `V1IntersectionReviewOverlay`.
- Done: recorded policy ref, radius, arc count, and diagnostics on the overlay object.
- Done: added model and FreeCAD smoke coverage for curb return preview.

Tasks:

- add simple radius policy fields
- generate corner return linework
- show corner return preview in the Intersections panel
- validate radius and leg connectivity

Acceptance:

- T and Cross starter sources show corner return arcs in 3D review.

### Phase 4: Crossfall And Grading Policy

Status: Done

Implementation status:

- Done: added `IntersectionGradingPolicyRow` as the source contract for intersection-area crossfall/grading behavior.
- Done: persisted grading policy rows in the FreeCAD `V1IntersectionModel` object.
- Done: generated a default `flatten_intersection` policy from the Intersections panel.
- Done: preserved active intersection grading policy refs in `AppliedSection` results and `V1AppliedSectionSet`.
- Done: exposed intersection grading policy in SectionOutput and Cross Section Viewer summaries.
- Done: applied the grading policy during `Intersection Surface` patch generation.
- Done: recorded grading policy ref, mode, target crossfall, and z-delta on `V1CorridorIntersectionSurfacePreview`.

Tasks:

- add grading policy options
- apply policy during patch surface generation
- report policy in Cross Section Viewer and Build Parametric diagnostics

Acceptance:

- flatten and primary-crown modes produce visibly different patch surfaces.

### Phase 5: Drainage Review Handoff

Status: Done

Implementation status:

- Done: added intersection drainage handoff rows to Build Parametric Drainage Review.
- Done: detects the lowest `fg_surface` point candidate from the intersection patch Applied Sections.
- Done: reports missing Drainage Element coverage for the intersection control Regions.
- Done: marks the handoff as ready when a Drainage Element references the intersection or one of its control Regions.
- Done: records drainage coverage status, low-point station/Z, and Drainage Element refs on `V1CorridorIntersectionSurfacePreview`.
- Done: added contract coverage for missing and ready intersection drainage handoff states.
- Deferred: flow direction preview markers remain a later Drainage visualization enhancement.

Tasks:

- detect low-point candidates from patch vertices
- report missing inlet / drainage element coverage
- defer optional flow direction preview markers to the Drainage visualization backlog

Acceptance:

- Drainage Review can identify an intersection with no drainage handling.

### Phase 6: Watertight Target Discovery

Status: Done

Implementation status:

- Done: added `intersection_patch_body` as a Watertight Solid target family.
- Done: added `intersection` as a Watertight Solid target scope.
- Done: Watertight Solids discovery now reads `IntersectionModel` and lists one `Intersection Patch Solid` target per intersection.
- Done: target rows preserve intersection id and control Region refs through target id, `source_refs`, and `region_ref`.
- Done: first-slice target readiness is `available` when intersection Applied Sections provide enough `fg_surface` boundary points.
- Done: insufficient intersection section coverage is blocked with an explicit `intersection_patch_target_insufficient_sections` diagnostic.
- Done: Watertight Solids UI labels the target as `Intersection Patch Solid`.
- Done: added a first-slice thin patch-prism build backend for `intersection_patch_body`.
- Done: added FreeCAD contract coverage for intersection patch target discovery, panel display, validation, and build output.
- Done: validation now blocks degenerate intersection patch boundaries with zero or near-zero XY area.
- Done: validation reports boundary area and minimum edge length in the Watertight Solids status message.
- Done: Simulation QA treats `intersection_patch_body` as road-body context and includes it in terrain-domain checks.
- Done: Simulation QA now checks whether intersection patch solids share control `region:` source refs with built road/region body outputs when those refs are available.
- Done: Simulation QA reports the nearest XY gap between a disconnected `intersection_patch_body` and built road/region body outputs.
- Done: Simulation QA reports patch and road `region:` source refs when intersection patch Region context does not match the built road/region body outputs.
- Done: Simulation QA now carries lightweight output edge XY segments from Watertight Solid shapes.
- Done: Simulation QA reports nearest patch/road edge-pair XY gap for disconnected or loosely paired intersection patch outputs.
- Done: Simulation QA reports `intersection_patch_trim_candidate` when patch/road edge pairs are within clip/trim tolerance.
- Done: Watertight Solids can create an `Intersection Trim Candidate Preview` object from candidate patch/road edge pairs.
- Done: the trim candidate preview is routed under the v1 Watertight Solids tree folder for hide/show and property review.
- Done: added `IntersectionTrimBoundaryResult` as a durable result contract for candidate patch/road trim edge pairs.
- Done: Watertight Solids stores the trim-boundary result object under the v1 Watertight Solids tree folder alongside the preview.
- Done: Watertight Solids links the trim-boundary result back to the related road and intersection patch output objects through `ResultRefs`.
- Done: trim-boundary pairs are evaluated as `ready_to_trim` or `blocked` before any future geometry clip is attempted.
- Done: the visible trim preview now uses only `ready_to_trim` pairs and records ready/blocked pair counts.
- Done: Simulation Package output now carries intersection trim-boundary handoff status and ready/blocked pair counts.
- Done: Simulation Package JSON export now includes ready trim pair rows with patch/road output refs and XYZ segment coordinates.
- Done: Watertight Solids can create an `Intersection Trim Application Preview` object from ready trim pairs.
- Done: Watertight Solids can create an `Intersection Trim Application Output` object that promotes ready trim pairs into downstream trim application geometry.
- Done: Watertight Solids can create an `Intersection Trim Closure Surface Preview` object from ready trim pairs.
- Done: Watertight Solids can create an `Intersection Trim Closure Surface Output` object for downstream shell/solid reconstruction.
- Done: Watertight Solids can create an `Intersection Trim Closure Cell Output` object with top, bottom, and side faces for ready trim pairs.
- Done: Watertight Solids can create an `Intersection Trim Shell Candidate Output` object that groups road, patch, closure-surface, and closure-cell geometry.
- Done: Watertight Solids can create an `Intersection Trim Fuse Candidate Output` object that attempts to fuse source outputs with closure-cell geometry and keeps a compound candidate when Boolean fuse fails.
- Done: Simulation Package output and JSON export now carry intersection trim fuse-candidate status, object refs, source refs, face count, and open-edge count.
- Done: the shell candidate output records open-edge diagnostics before final shell/solid reconstruction.
- Done: Watertight Solids can create an `Intersection Trim Shell Reconstruction Output` object from shell candidate faces and report remaining open edges.
- Done: Watertight Solids can create an `Intersection Trim Solid Reconstruction Output` object and block solid creation when the reconstructed shell still has open edges.

Tasks:

- expose intersection patch targets
- validate patch boundary and surface closure
- prepare first body target contracts

Acceptance:

- Watertight Solids can list intersection targets and block invalid ones with clear diagnostics.

## 7.1 Next Refinement Plan

Status: Planned

The current `Intersection Surface` is a stable first-slice local patch.
It is acceptable as a preview, but it is not yet a final geometric junction surface.

The next goal is to replace the simple center-nearest section hull with an explicit, source-traceable intersection patch boundary that follows road tie-in edges and curb return intent.

### Refinement Goal

Create a cleaner T/Cross intersection surface that:

- stays local to the control area
- follows participating road pavement edges
- uses curb return arcs as real boundary contributors
- trims ordinary Design/Slope surfaces around the junction instead of overlapping them
- exposes diagnostics before downstream watertight solid generation

### Current First-slice Behavior

Current behavior:

- selects center-nearest Applied Sections per participating Alignment
- collects `fg_surface` points from those sections
- builds a non-self-crossing XY hull
- creates a centroid fan TIN
- applies the active intersection grading policy

This prevents long or torn surfaces, but it does not yet create a civil-quality intersection shape.

Current limitations:

- curb return arcs are preview linework only
- patch boundary is inferred from section points, not from explicit edge topology
- main-road and side-road pavement edges are not clipped against the patch boundary
- the patch may look like a simple diamond or quadrilateral instead of a true curb-return junction
- Design Surface and Slope Face Surface still need stronger exclusion around the control area

### Phase 7: Explicit Tie-in Edge Extraction

Status: Completed

Purpose:

Extract the road edges that the intersection patch must connect to.

Implementation status:

- Done: added `IntersectionTieInEdgeResult` and `IntersectionTieInEdgeRow` result contracts.
- Done: added first-slice tie-in edge extraction from intersection Applied Section `fg_surface` rows.
- Done: extracts left/right pavement-edge candidates per participating Alignment.
- Done: uses intersection primary/secondary target station context to choose nearby section pairs.
- Done: feeds actual tie-in edge count into intersection patch prerequisite readiness.
- Done: added focused contract coverage for primary/side left/right tie-in edge extraction.
- Done: added `V1CorridorIntersectionTieInEdgePreview` linework so Build Parametric can show the pavement-edge candidates used by the intersection patch.
- Done: Build Parametric Guided Review and Results rows now report tie-in edge count, boundary point count, grading mode, drainage status, and tie-in preview object ref.
- Done: tie-in extraction now records warning-only diagnostics for single-section candidates and error diagnostics for missing or incomplete edge candidates.
- Done: Intersection Surface preview objects carry tie-in status, tie-in diagnostic count, and intersection diagnostic refs for panel review.
- Done: Intersection Surface preview now exposes troubleshooting metrics for patch triangulation mode, boundary bounding-box aspect ratio, minimum triangle quality, and skinny triangle count.

Implementation tasks:

1. Done: Add an `IntersectionTieInEdgeResult` contract.
2. Done: For each participating Alignment, read the center-nearest Applied Section rows around the control area.
3. Done: Identify left/right pavement edge candidates from `fg_surface` points.
4. Done: Store edge role, Alignment ref, Region ref, station, side, XYZ start/end, and source section refs.
5. Optional follow-up: Prefer Subassembly metadata over simple left/right offset extremes when stable Subassembly edge ids are available.
6. Done: Expose tie-in edge rows as optional Build Parametric preview linework.
7. Done: Expose Build Parametric review notes when a leg has missing or ambiguous tie-in edges.

Acceptance:

- T-intersection has at least four usable tie-in edges: primary left/right and side left/right.
- edge rows remain traceable to Applied Sections.
- missing edge data blocks refined patch generation but does not crash Build Parametric.

### Phase 8: Curb-return Boundary Construction

Status: Completed for first-slice T-intersection scope

Purpose:

Convert curb return policy from preview-only linework into patch boundary geometry.

Implementation status:

- Done: added `IntersectionBoundarySegmentResult` and `IntersectionBoundarySegmentRow` result contracts.
- Done: promotes tie-in edge rows into `tie_in` boundary segment candidates.
- Done: converts active curb return policy radius into first-slice `arc` boundary segment candidates.
- Done: supports two T-intersection curb-return arc candidates and records chord sample points.
- Done: records boundary mode, status, tie-in segment count, arc segment count, and diagnostics on the `Intersection Surface` preview object.
- Done: added focused contract coverage for tie-in and curb-return boundary segment generation.
- Done: added `V1CorridorIntersectionBoundarySegmentPreview` linework so Build Parametric can show tie-in and curb-return boundary segment candidates in the 3D View.
- Done: added first-pass diagnostics for fallback directions, oversized curb-return radius, invalid radius sampling, and arc endpoint gaps.

Implementation tasks:

1. Done: Convert active `IntersectionCurbReturnPolicyRow` into boundary arc segments.
2. Done: Build arc segments between compatible primary/side tie-in edges for the first-slice T-intersection scope.
3. Done: Support first-slice T-intersection two-corner return geometry.
4. Optional follow-up: Support Cross intersection four-corner return geometry after T is stable.
5. Done: Store boundary segments as rows:
   - `line`
   - `arc`
   - `tie_in`
   - `control_edge`
6. Done: Add diagnostics for radius too large, radius too small, missing direction, or disconnected edge endpoints.

Acceptance:

- T-intersection patch boundary visually follows two curb return corners.
- changing the curb return radius changes the patch boundary, not only the overlay linework.
- disconnected boundary segments are reported before triangulation.

### Phase 9: Ordered Patch Polygon And Triangulation

Status: Completed for ordered outer-boundary first-slice scope

Purpose:

Replace centroid fan triangulation with ordered boundary triangulation.

Implementation status:

- Done: added `IntersectionPatchBoundaryResult` and `IntersectionPatchBoundaryPointRow` result contracts.
- Done: converts tie-in and curb-return boundary segment candidates into ordered patch-boundary point rows.
- Done: records ordered boundary point count, source segment count, closed flag, and diagnostics on the `Intersection Surface` preview object.
- Done: records ordered patch-boundary quality rows on the generated `TINSurface`.
- Done: added focused contract coverage for ordered patch-boundary generation and preview metadata.
- Done: uses the ordered patch-boundary points as the first source for Intersection Surface TIN vertices, with convex-hull fallback.
- Done: keeps Z values tied back to graded Applied Section FG points when ordered boundary rows come from source intent.
- Done: filters zero-area polygon/fallback triangles and records degenerate triangle count, maximum boundary edge length, and long boundary edge count.
- Done: makes long boundary edge detection policy-driven through optional curb-return policy fields.
- Done: replaced the first fan triangulation with ordered polygon ear-clipping triangulation.
- Done: blocks zero-area and self-crossing ordered boundaries from becoming the preferred surface triangulation input.
- Done: records ordered boundary polygon area and self-crossing state on the `Intersection Surface` preview object.
- Done: adds first multi-ring contract fields for outer, hole, and island boundary intent.
- Done: preserves hole/island boundary candidates as multi-ring boundary intent for downstream exclusion and diagnostics.

Implementation tasks:

1. Done: Add an `IntersectionPatchBoundaryResult` contract.
2. Done: Build a closed ordered polygon from tie-in and curb-return boundary segments.
3. Done: Sample arc segments into stable chord points using a configurable tolerance.
4. Done: Triangulate the ordered polygon for the ordered outer-boundary first-slice scope.
   - Done: first ordered-boundary fan triangulation.
   - Done: first quality filter for zero-area polygon/fallback triangles.
   - Done: replace fan triangulation with first ordered polygon ear-clipping triangulation.
   - Done: add first contract-level hole/island awareness.
   - Optional follow-up: triangulate holes, islands, and complex multi-leg intersection polygons as part of final intersection patch surface generation.
5. Done: Reject self-crossing, zero-area, or overly long boundary edges.
   - Done: self-crossing boundary candidate diagnostic.
   - Done: zero-area ordered boundary diagnostic.
   - Done: zero-area fan triangle exclusion.
   - Done: long edge count quality metric.
   - Done: make long edge thresholds policy-driven.
   - Optional follow-up: expose long edge policy controls in the Intersections UI when this becomes user-editable.
6. Done: Preserve boundary provenance in `TINQualityRow` and `TINProvenanceRow`.

Acceptance:

- patch surface no longer appears as a simple diamond when curb returns are available.
- triangle edges stay inside the ordered patch polygon.
- boundary point count, arc segment count, and triangle count are visible on the preview object.

### Phase 10: Surface Exclusion And Trim Zones

Status: Completed

Purpose:

Prevent ordinary corridor surfaces from overlapping the refined intersection patch.

Implementation status:

- Done: promotes the ordered intersection patch boundary into a `V1CorridorIntersectionExclusionZonePreview` object.
- Done: records exclusion zone ref, status, point count, area, and ring counts on relevant Build Parametric preview objects.
- Done: applies first-slice centroid/edge-intersection exclusion clipping to Design Surface and Slope Face Surface preview TIN triangles.
- Done: records clipped/kept triangle counts per affected surface preview.
- Done: reports Design/Slope exclusion clipped/kept triangle counts in the Build Parametric Guided Review notes.
- Done: records exact-cut candidate and boundary-crossing triangle counts so final-output clipping needs are explicit.
- Done: performs first-slice exact outside-fragment triangulation for convex intersection exclusion polygons.
- Done: supports simple non-convex outer exclusion polygons by triangulating the exclusion area before exact cutting.
- Done: supports multi-ring exact cutting inputs where outer/island rings remove surface fragments and hole rings preserve surface fragments.
- Done: generates hole/island patch-boundary `point_rows` from boundary segment sources so multi-ring exclusion data can flow into clipping.
- Done: validates multi-ring topology for too-few points, zero-area rings, self-crossing rings, inner rings outside the outer ring, and ring intersections.
- Done: exposes patch-boundary ring counts and first topology diagnostics in Build Parametric Guided Review and Results notes.

Implementation tasks:

1. Done: Add an intersection exclusion polygon to Build Parametric surface generation.
   - Done: create reviewable exclusion zone from `IntersectionPatchBoundaryResult`.
   - Done: apply the exclusion polygon to Design/Slope preview TIN generation.
2. Done: Remove or suppress Design Surface triangles inside the patch boundary.
3. Done: Remove or suppress Slope Face Surface triangles that bridge across unrelated intersection legs.
4. Done: Record clipped triangle counts per surface family.
5. Keep the patch visible as a separate `Intersection Surface` object for review.
6. Done: replace suppression-based clipping with exact polygon/triangle cutting for current Build Parametric preview scope.
   - Done: expose candidate counts that identify where exact cutting is needed.
   - Done: implement exact polygon/triangle cutting for convex exclusion polygons in Build Parametric preview surfaces.
   - Done: extend exact cutting to simple non-convex outer patch boundaries using triangulated exclusion parts.
   - Done: extend the clipping engine to multi-ring exclusion input.
   - Done: generate real hole/island `point_rows` from boundary segment sources instead of diagnostics-only ring counts.
   - Done: validate multi-ring patch-boundary topology against complex production intersection source patterns.
   - Done: expose multi-ring topology diagnostics in Build Parametric review notes.
   - Optional follow-up: add a dedicated topology diagnostics table only if production QA needs more than compact notes.

Acceptance:

- Design Surface does not cover the same central area as `Intersection Surface`.
- Slope Face Surface does not create stray triangles across the T junction.
- Build Parametric review rows report clipped/kept triangle counts.
- Build Parametric quality rows report whether exact polygon/triangle cutting is recommended.
- Multi-ring quality rows report hole/island ring counts when the exclusion input contains them.

### Phase 11: Grading And Superelevation Integration

Status: Completed for first-slice low-point review scope

Purpose:

Make intersection patch elevations behave predictably.

Implementation tasks:

1. Done: Evaluate active Superelevation and Crossfall context from Applied Sections used by the intersection patch.
2. Done: Apply `IntersectionGradingPolicyRow` inside the patch boundary.
3. Support first-slice modes:
   - Done: `flatten_intersection`
   - Done: `keep_primary_crown`
   - Done: `blend_primary_side`
4. Done: Store elevation source notes on patch vertices.
5. Show grading mode and max Z adjustment in Build Parametric and Cross Section Viewer.
   - Done: Build Parametric Results and Guided Review report grading policy, grading mode, max Z adjustment, and Superelevation source/transition counts.
   - Done: Cross Section Viewer Summary exposes active Intersection, control area, leg, grading policy, and Superelevation context for the selected station.

Implementation status:

- Done: Intersection Surface TIN quality rows now record Applied Section Superelevation source count, transition count, left/right crossfall range, and a compact context summary.
- Done: `V1CorridorIntersectionSurfacePreview` exposes the same Superelevation context for Property View and Build Parametric Results notes.
- Done: grading policy modes now have distinct first-slice behavior: flatten all patch vertices, preserve primary crown, or blend side vertices toward primary average Z.
- Done: ordered patch boundary vertices preserve the nearest graded elevation source reference and source notes.
- Done: Build Parametric review notes expose intersection grading policy, mode, max Z adjustment, and Superelevation context.
- Done: Cross Section Viewer Summary now reports active Intersection grading context and Superelevation context for the selected station.

Acceptance:

- changing grading policy produces visible and traceable elevation changes.
- normal road Superelevation remains unchanged outside the control area.
- Cross Section Viewer clearly shows when a station is inside intersection grading context.

### Phase 12: Drainage And Low-point Review

Status: In progress

Purpose:

Make the refined patch usable for practical drainage planning.

Implementation tasks:

1. Done: Detect low-point candidates from the refined patch TIN.
2. Done: Report first-slice boundary-to-low flow direction hints from patch boundary toward low points.
3. Done: Check whether Drainage Elements cover the owning Intersection/control Regions and the low-point station range.
4. Done: Show suggested inlet candidate positions as review markers only.
5. Done: Keep hydraulic sizing and automatic pipe design out of this phase.

Implementation status:

- Done: Intersection Surface TIN quality rows now record low-point candidate count, low-point XYZ/source ref, and boundary-to-low flow hint summary.
- Done: `V1CorridorIntersectionSurfacePreview` exposes the refined TIN low-point and flow hint context for Property View and Build Parametric Results notes.
- Done: Intersection Drainage review rows create `intersection_suggested_inlet` marker objects when focused, with `SuggestedInletReviewOnly=Yes`.
- Done: Intersection Drainage coverage now distinguishes linked candidates from ready coverage; linked elements must also cover the low-point station range.

Acceptance:

- Drainage Review reports whether intersection drainage is missing or ready.
- low-point candidate is local to the refined patch.
- suggested inlet markers do not become durable source rows without user action.

### Phase 13: Watertight Handoff

Status: In progress

Purpose:

Prepare the refined intersection patch for simulation-ready solid workflows.

Implementation status:

- Done: `intersection_patch_body` target discovery now marks refined patch boundary output as the preferred boundary source.
- Done: Watertight Solids validation/build now uses `V1CorridorIntersectionSurfacePreview` boundary points first when the refined preview exists.
- Done: refined patch validation blocks solid creation when the preview boundary is open or carries boundary diagnostics.
- Done: refined patch solid output records `path_source=refined_intersection_surface_preview` so first-slice fallback and refined patch body can be distinguished.
- Done: refined patch output source refs carry the Intersection Surface preview, tie-in edge preview, boundary segment preview, and exclusion-zone preview refs when available.
- Done: Simulation Package now records an explicit handoff chain from trim-boundary result through trim application, closure surface, closure cell, shell candidate, fuse candidate, shell reconstruction, and solid reconstruction.
- Done: related road/patch Watertight Solid output objects receive the same `IntersectionTrimHandoffChainRefs` and stage status rows for Property View traceability.

Implementation tasks:

1. Done: Update `intersection_patch_body` target discovery to prefer refined patch boundary output.
2. Done: Validate patch boundary closure before solid creation.
3. Done: Carry tie-in edge refs and curb-return/boundary segment refs into target/output `source_refs`.
4. Done: Use trim-boundary and closure-cell outputs to connect patch body to road/region bodies through the simulation handoff chain.
5. Done: Keep Boolean fuse fallback explicit when final solid reconstruction is not possible.

Acceptance:

- Watertight Solids can distinguish first-slice patch body from refined patch body.
- Simulation Package export preserves intersection patch boundary, tie-in, trim, and fuse traceability.

### UI Plan

Build Parametric should expose the refined workflow without making the panel crowded.

Planned UI changes:

- `Guided Review`
  - keep `3. Intersections`
  - show status: `ready`, `warning`, `blocked`
  - notes should mention tie-in edge count, boundary status, and patch triangle count
- `Results`
  - keep `Intersection Surface`
  - add diagnostic text for boundary mode:
    - `center-section hull`
    - `tie-in boundary`
    - `curb-return boundary`
- `Intersections` tab
  - add read-only rows:
    - Intersection ID
    - Kind
    - Boundary Mode
    - Tie-in Edges
    - Curb Returns
    - Patch Status
- `Visibility`
  - separate toggles:
    - Intersection Surface
    - Tie-in Edges
    - Curb Return Boundary
    - Trim/Exclusion Area

The Intersections source panel should remain source-focused.
It should edit intersection type, participating Alignments, control Regions, curb radius, and grading policy.
It should not directly edit generated patch triangles.

### Implementation Priority

Recommended order:

| Step | Status | Work Item | Reason |
|---|---|---|---|
| 1 | Pending | Tie-in edge result contract | defines what the patch must connect to |
| 2 | Pending | Boundary segment contract | separates line/arc/tie-in boundary logic from TIN generation |
| 3 | Pending | T-intersection curb-return boundary | first practical visual upgrade |
| 4 | Pending | Ordered polygon triangulation | replaces simple hull/fan surface |
| 5 | Pending | Design/Slope exclusion zone | prevents overlapping surfaces |
| 6 | Pending | Cross Section Viewer context | makes grading/boundary source explainable |
| 7 | Pending | Drainage low-point review update | supports practical drainage workflow |
| 8 | Pending | Watertight refined patch handoff | prepares simulation target continuity |

### Manual QA For Refined Patch

1. Create starter `T Intersection` sources.
2. Build 3D Centerline, Build Sections, and Build Parametric.
3. Show only `Intersection Surface`.
4. Confirm patch stays local to the junction.
5. Show tie-in edges.
6. Confirm the patch connects to primary and side-road pavement edges.
7. Show curb-return boundary.
8. Change curb radius and rebuild.
9. Confirm the visible patch boundary changes.
10. Show Design Surface and Slope Face Surface.
11. Confirm central overlap and stray slope triangles are not present.
12. Open Cross Section Viewer at a control-area station.
13. Confirm intersection grading/boundary context is reported.
14. Open Watertight Solids.
15. Validate intersection patch target and confirm diagnostics are explicit.

### Phase 14: Practical Curb-return And Edge-blending Geometry

Status: In progress

Purpose:

Move the current stable T-intersection patch from a rectangular strip-union result toward a practical road-design junction shape.

The current `Intersection Surface` is acceptable as a stable first patch:

- the patch stays local to the junction
- the main-road strip and side-road stem are separated by Alignment context
- ordinary Design/Slope surfaces can be clipped around the patch
- the patch uses structured strip triangulation instead of arbitrary fan or hull triangulation

The next goal is not only to avoid broken geometry, but to make the patch boundary reflect design intent such as curb returns, corner radii, edge blending, and leg-specific tie-in behavior.

Core rule:

Do not edit generated patch triangles directly.

Practical junction shape must be produced from:

- `IntersectionModel`
- participating `IntersectionLegRow` rows
- `IntersectionCurbReturnPolicyRow`
- Applied Section `fg_surface` edge rows
- intersection grading policy
- source-owned control Regions

Implementation sequence:

| Step | Status | Work Item | Acceptance |
|---|---|---|---|
| 14.1 | Done | Structured strip triangulation | T starter patch uses main strip + side stem triangles instead of arbitrary ear-clipping diagonals. |
| 14.2 | Done | Surface boundary role split | Patch output reports pavement tie-in, stem tie-in, overlap-cut, and curb-return boundary roles in Build Parametric review and Property View. |
| 14.3 | Done | Curb-return boundary integration | T starter `Intersection Surface` adds two curb-return arc sectors to the structured strip patch. |
| 14.4 | Done | Arc sampling density policy | Curb-return arcs use radius-based sample counts, and Build Parametric exposes arc count, sample count, and segment count diagnostics. |
| 14.5 | Done | Edge blending faces | Curb-return sectors are split into outer blend bands plus inner core surfaces, and Build Parametric reports edge blend face counts. |
| 14.6 | Done | Design/Slope clipping alignment | Design and Slope preview TINs record practical boundary source/strategy and clip against the same structured strip + curb-return blend boundary. |
| 14.7 | Done | Review and property output | Build Parametric Results, Guided Review, and Property View report boundary mode, curb-return edge count, structured strip count, arc sample count, edge blend count, clipping boundary strategy, and triangle quality. |
| 14.8 | Done | Watertight handoff update | Watertight Solids reports the practical curb-return boundary handoff and annotates `intersection_patch_body` targets with boundary, clipping, arc, and edge-blend context. |

Slope Face clipping rule:

- Design Surface may use exact-cut fragments around the intersection exclusion boundary.
- Region-level Design Surface and Subgrade Surface previews must use the same intersection exclusion clipping as the full corridor previews. A side-road Region preview must not protrude into the intersection patch or curb-return control area.
- Slope Face Surface must not leave exact-cut fragments inside or across the intersection control area.
- If a Slope Face triangle intersects the practical curb-return boundary or the daylight protection area around it, suppress the whole triangle instead of generating an outside fragment.
- If a Slope Face triangle is sourced from an AppliedSection with active intersection control context and touches the daylight protection area, suppress the whole triangle even when the triangle falls just outside the practical boundary polygon.
- If a whole-corridor Slope Face triangle remains outside the practical polygon but near a curb-return arc, suppress it through curb-return arc daylight protection so `corridor:main` daylight fragments do not protrude into the curb-return tie-in.
- If a whole-corridor Slope Face triangle intrudes into a representative intersection pavement strip polygon, suppress it through pavement-strip daylight protection so `corridor:main` Slope Face does not cross over the designed road surface.
- Do not suppress exterior Slope Face triangles solely because they come from an intersection-control section; outside tie-in slopes must remain continuous between the main road and side road.
- Keep the curb-return arc Slope Face band so the curb-return exterior edge has daylight surface coverage.
- Do not append endpoint caps or bridge triangles after TIN construction.
- Curb-return Slope Face continuity must come from build-time generated `intersection_tie_in` Applied Sections placed at the side-road/intersection contact points.
- The normal Slope Face builder must create the side-road-to-curb-return daylight surface from those generated section rows.
- Intersection Surface preview must also use the build-time generated `intersection_tie_in` Applied Sections so the patch boundary, curb-return blend, and side-road stem remain aligned to the same section context.
- If an intersection tie-in candidate has only one Applied Section, use that section frame tangent as the temporary tie-in edge direction instead of falling back to global X/Y axes.
- Side-road corner Slope Face boundary strips are deferred; do not infer them from nearest curb-return arc sample points.
- The `intersection_slope_tie_in` strip is a source-traceable Slope Face surface, not a free cap or arbitrary bridge.
- If the existing side-road Slope Face boundary stops short of the side-road Applied Section edge, add `intersection_side_slope_extension` strips from nearby existing side-road Slope Face boundary edges to that Applied Section edge.
- The side extension is limited to the nearest existing Slope Face boundary edges and must not connect to unrelated main-road or curb-return generated edges.
- Generated `intersection_slope_tie_in` and `intersection_side_slope_extension` triangles must not be appended when they intrude into representative pavement strip polygons.
- Intersection Surface preview displays `curb_return_blend` and `curb_return_core` faces so the curb-return half-round patch remains visible during intersection review.
- Intersection corner Slope Face continuity is reviewed on the Daylight/Slope Face surface. The build should expose generated section rows through section diagnostics and corner boundary strip counts, not full curb-return slope-band counts.
- Build Parametric should expose `IntersectionExclusionControlSectionClippedTriangleCount` so this source-context suppression is visible during QA.
- The expected Slope Face role is exterior terrain/daylight tie-in only, not filling the main-road/side-road junction interior.

Curb-return arc role:

- The arc is the outside turning-corner boundary between the main road and the side road.
- It defines the practical edge of the `Intersection Surface` patch.
- It gives the clipping boundary for ordinary `Design Surface` and the stronger protection boundary for `Slope Face Surface`.
- It is not a drainage pipe, lane marking, or decorative preview. It is first-slice geometry intent for the intersection corner return.

First implementation target:

Use the existing T-intersection starter as the acceptance case.

Expected visual result:

- main road remains a continuous through strip
- side road stem ties into the main road
- the two outside corners use curb-return arcs
- internal triangle edges follow strip and arc bands as much as possible
- no large fan of triangles collapses into one corner
- no Design/Slope Surface overlaps the central patch

Non-goals for Phase 14:

- full lane-based intersection design
- traffic island design
- signal design
- automatic road-marking layout
- roundabout geometry
- complete hydraulic design
- final Boolean union of all road bodies

Manual QA for Phase 14:

1. Create starter `T Intersection` sources.
2. Run `Build Sections`.
3. Run `Build Parametric`.
4. In Guided Review, select `3. Intersections`.
5. Confirm the patch is local and stable.
6. Confirm `PatchTriangulationMode` is `structured_strip` or a later practical boundary mode.
7. Confirm `PatchTriangleSkinnyCount` is `0`.
8. Confirm curb-return preview arcs appear near the junction.
9. After Phase 14.2, confirm `PatchBoundaryRoleSummary` reports `pavement_tie_in`, `stem_tie_in`, `overlap_cut`, and `curb_return` counts.
10. After Phase 14.3, confirm the surface boundary follows the curb-return arcs.
11. After Phase 14.4, confirm Guided Review notes include curb-return arc count, arc samples, and arc segments.
12. After Phase 14.5, confirm Guided Review notes include edge blend faces and `PatchTriangulationMode` is `structured_strip_curb_return_blend`.
13. After Phase 14.6, confirm Design/Slope exclusion notes report `boundary=structured_strip_curb_return_blend` and `aligned=practical`.
14. After Phase 14.7, select the `Intersection Surface` preview object and confirm `IntersectionReviewSummary` and `IntersectionPatchQualitySummary` are populated.
15. Show Design Surface and Slope Face Surface together with Intersection Surface.
16. Confirm ordinary surfaces do not overlap the practical patch boundary.
16.1. Show a side-road Region Design Surface by itself and confirm it is clipped at the intersection patch boundary.
17. Confirm Slope Face Surface does not leave green wedge fragments inside the main-road/side-road junction, near the protected curb-return area, or across curb-return arcs.
18. Confirm the Slope Face preview property `IntersectionExclusionControlSectionClippedTriangleCount` is greater than `0` when intersection-control sections would otherwise create local green wedge faces.
19. Confirm generated `intersection_tie_in` Applied Sections are created at side-road/intersection contact points when curb-return arcs are present.
19.1. Confirm `IntersectionCurbReturnSlopeBandTriangleCount` is greater than `0` when curb-return arcs are present.
19.2. Confirm `IntersectionSlopeTieInTriangleCount` is greater than `0` when a side-road Applied Section has a valid slope-face edge near the curb-return band.
19.3. Confirm `IntersectionSideSlopeExtensionTriangleCount` is greater than `0` when the existing side-road Slope Face boundary stops short of the side-road Applied Section tie-in edge.
20. Confirm no endpoint cap or arbitrary bridge triangles are appended after TIN construction.
21. Confirm exterior Slope Face strips remain continuous between the main-road, side-road, and curb-return edges through the generated tie-in sections.
22. Open Watertight Solids and confirm intersection patch target diagnostics still reference the refined boundary source.
23. After Phase 14.8, confirm `Intersection Solid QA` reports `boundary=structured_strip_curb_return_blend`, `aligned=practical`, curb-return arc counts, and edge blend face counts.
24. After Phase 14.8, select the `Intersection Patch Solid` target and confirm its source/diagnostic text includes `IntersectionHandoff` with the same practical boundary strategy.

## 8. Risks

### Risk: Patch Boundary Ambiguity

Intersection boundaries are not always rectangular or symmetric.

Mitigation:

- start with T and Cross starter geometries
- require diagnostics before generating a patch
- keep user-visible control Regions as the boundary source

### Risk: Surface Overlap

Ordinary corridor surfaces and intersection patch surfaces may overlap.

Mitigation:

- record clipped triangle counts
- keep patch preview separately visible
- delay full boolean or mesh merge until patch quality is stable

### Risk: Crossfall Conflict

Superelevation, Assembly crossfall, and intersection grading may conflict.

Mitigation:

- make intersection grading policy explicit
- show source provenance in Applied Sections and Cross Section Viewer
- keep normal Superelevation unchanged outside control areas

### Risk: Too Much Automation Too Early

Automatic curb returns, drainage, and solids can create misleading geometry if source intent is weak.

Mitigation:

- keep first outputs as reviewable previews
- expose diagnostics before writing downstream solids
- require explicit Build Sections / Build Parametric rebuilds

## 9. Non-goals

This plan does not implement:

- full roundabout design
- signal timing
- traffic simulation
- automatic lane marking/drafting
- final hydraulic analysis
- automatic pipe sizing
- complete intersection solid boolean union

## 10. Diagnostics

Required diagnostics:

- `intersection_patch_prerequisites_missing`
- `intersection_patch_boundary_open`
- `intersection_patch_boundary_too_few_points`
- `intersection_patch_tie_in_edge_missing`
- `intersection_patch_degenerate_triangle`
- `intersection_patch_overlaps_design_surface`
- `intersection_patch_unclipped_design_surface`
- `intersection_curb_return_policy_missing`
- `intersection_curb_return_radius_invalid`
- `intersection_curb_return_radius_small`
- `intersection_curb_return_radius_large`
- `intersection_curb_return_arc_endpoint_gap`
- `intersection_grading_policy_missing`
- `intersection_grading_policy_conflict`
- `intersection_drainage_context_missing`
- `intersection_low_point_without_inlet`
- `intersection_watertight_target_not_closed`

Diagnostic rows should report:

- intersection id
- alignment id, where applicable
- region id, where applicable
- station range
- severity
- short message
- suggested next action

## 11. Manual QA

Manual QA is required, but it is not the only verification surface.

Use this section as the interactive FreeCAD checklist after the focused contract tests pass.
The current Intersections work touches source creation, multi-alignment 3D Centerline generation, Applied Sections, Build Parametric surface review, and Watertight Solid handoff.
Therefore QA should be split into:

- automated contract tests for source/result/output contracts
- manual panel QA for user-visible workflows
- visual 3D View QA for overlays, Regions, surfaces, and trim/fuse previews
- release smoke QA before tagging

### 11.1 Automated Verification

Run focused tests after code changes when feasible:

1. Intersections command contract tests.
2. Applied Sections contract tests for multi-alignment section rows.
3. Build Parametric contract tests for intersection-aware design and slope-face surfaces.
4. Watertight Solids contract tests for intersection patch, trim candidate, closure cell, fuse candidate, shell reconstruction, solid reconstruction, and simulation package handoff.
5. Python compile smoke for changed v1 command, service, model, object, and test files.

Expected result:

- tests pass without changing source intent unexpectedly
- generated objects stay routed to the correct project tree folders
- diagnostics remain explicit instead of silent fallback behavior

### 11.2 Minimum Manual Smoke QA

Minimum smoke QA after each implementation phase:

1. Create starter `T Intersection` sources.
2. Confirm Alignment, Profile, Stationing, Regions, and multi-alignment 3D Centerline objects exist.
3. Run `Build Sections`.
4. Open Cross Section Viewer and confirm intersection context appears for control-area stations.
5. Run `Build Parametric`.
6. Confirm ordinary Design Surface, Slope Face Surface, and intersection-related review rows are listed separately.
7. Show Region Boundaries and verify primary and side-road Regions are both visible.
8. Highlight each Region and confirm only the selected alignment/region scope is highlighted.
9. Show the intersection review overlay and confirm control area and participating legs are visible.
10. Confirm diagnostics explain missing patch, open patch, or drainage gaps without crashing.

### 11.3 Preview Selection And Overlay QA

Run this when Intersections overlay or control-area highlight logic changes:

1. Open `Intersections`.
2. Use `Create Starter Sources`.
3. Click `Preview Selection`.
4. Confirm the highlighted control area stays local to the intersection and does not extend far along the right or left side of an Alignment.
5. Confirm curb return preview arcs appear near the junction only.
6. Confirm `Hide Overlay` removes the preview object from the 3D View.
7. Confirm the `Intersection Review Overlay` object is routed under the Intersections tree folder.

Pass condition:

- preview geometry remains bounded around the selected intersection control area
- no long stray highlight segment is created along an Alignment
- repeated Preview/Hide/Preview cycles update the same review object cleanly

### 11.4 Multi-alignment 3D Centerline QA

Run this when starter source generation, 3D Centerline, or downstream station-frame usage changes:

1. Use `Create Starter Sources`.
2. Confirm a multi-alignment `3D Centerline` review object is created under the 3D Centerline tree folder.
3. Confirm the primary road and side road have separate 3D Centerline rows.
4. Run `Build Sections`.
5. Confirm Applied Sections use the matching 3D Centerline row for each active Alignment.
6. Confirm Build Parametric does not force side-road geometry onto the primary-road 3D Centerline.

Pass condition:

- primary and side-road section geometry follows each road's own baseline
- no station/offset/elevation frame is resolved from the wrong Alignment

### 11.5 Build Parametric Visual QA

Run this when design surface, slope face, Region boundary, or intersection build behavior changes:

1. Build the starter T intersection.
2. Show `Design Surface`.
3. Show `Slope Face Surface`.
4. Review `Region Boundaries`.
5. Confirm primary-road approach, intersection, and departure Regions are visible.
6. Confirm side-road Regions are also listed and reviewable when the source model includes them.
7. Confirm Slope Face Surface does not connect unrelated Alignment section rows.
8. Confirm ordinary road surfaces do not produce stray triangles through the intersection control area.

Pass condition:

- road legs are separated by Alignment context
- slope-face triangles do not bridge across unrelated roads
- intersection control-area diagnostics are visible when a patch or trim step is still incomplete

### 11.6 Intersection Surface Patch QA

Extra QA when `Intersection Surface Patch` is implemented:

1. Confirm a patch is created at the junction center.
2. Confirm ordinary road surfaces do not produce stray triangles across the control area.
3. Confirm turning Slope Face Surface on and off does not hide the patch.
4. Confirm patch diagnostics include point count, edge count, and triangle count.

### 11.7 Watertight Solid And Simulation QA

Extra QA when Watertight discovery, trim, fuse, shell, solid, or package handoff changes:

1. Open Watertight Solids.
2. Confirm intersection targets are listed only after Build Parametric prerequisites exist.
3. Validate an intersection target.
4. Confirm open or invalid targets are blocked with clear diagnostics.
5. Build road/region body targets and intersection patch targets.
6. Run Simulation QA.
7. Confirm trim-boundary, trim preview, closure surface, closure cell, shell candidate, fuse candidate, shell reconstruction, and solid reconstruction objects are created under Watertight Solids when candidate geometry exists.
8. Confirm the Simulation Package JSON includes intersection trim/fuse handoff fields.

Pass condition:

- invalid targets are blocked before solid creation
- fuse fallback is reported as a compound candidate when Boolean fuse fails
- shell/solid reconstruction reports open-edge status clearly
- simulation package export preserves intersection trim/fuse traceability

## 12. Documentation Updates

When implementation begins, update:

- [wiki/Intersections.md](./wiki/Intersections.md)
- [wiki/Workflow.md](./wiki/Workflow.md)
- [wiki/Applied-Sections-Build-Corridor.md](./wiki/Applied-Sections-Build-Corridor.md)
- [V1_INTERSECTION_MODEL.md](./V1_INTERSECTION_MODEL.md), if source fields change
- [V1_SURFACE_MODEL.md](./V1_SURFACE_MODEL.md), if `intersection_surface` becomes a stable surface kind
- [V1_WATERTIGHT_SOLID_PLAN.md](./V1_WATERTIGHT_SOLID_PLAN.md), when intersection targets become discoverable
