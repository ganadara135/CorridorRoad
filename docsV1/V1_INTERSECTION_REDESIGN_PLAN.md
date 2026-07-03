# Parametric Road V1 Intersection Redesign Plan

Date: 2026-06-07
Branch: `v1-0503`
Status: Draft redesign plan
Depends on:

- [V1_MASTER_PLAN.md](./V1_MASTER_PLAN.md)
- [V1_ARCHITECTURE.md](./V1_ARCHITECTURE.md)
- [V1_INTERSECTION_MODEL.md](./V1_INTERSECTION_MODEL.md)
- [V1_INTERSECTION_IMPLEMENTATION_PLAN.md](./V1_INTERSECTION_IMPLEMENTATION_PLAN.md)
- [V1_INTERSECTION_ENHANCEMENT_PLAN.md](./V1_INTERSECTION_ENHANCEMENT_PLAN.md)
- [V1_ALIGNMENT_MODEL.md](./V1_ALIGNMENT_MODEL.md)
- [V1_REGION_MODEL.md](./V1_REGION_MODEL.md)
- [V1_SECTION_MODEL.md](./V1_SECTION_MODEL.md)
- [V1_SURFACE_MODEL.md](./V1_SURFACE_MODEL.md)
- [V1_SUPERELEVATION_MODEL.md](./V1_SUPERELEVATION_MODEL.md)
- [V1_DRAINAGE_MODEL.md](./V1_DRAINAGE_MODEL.md)
- [V1_WATERTIGHT_SOLID_PLAN.md](./V1_WATERTIGHT_SOLID_PLAN.md)

## 1. Purpose

This document resets the intersection implementation direction.

The current first-slice implementation proved that multi-alignment starter sources, multi-alignment 3D Centerline, Region review, and a first intersection patch can work.

It also exposed a structural limit: intersection quality cannot be stabilized by repeatedly clipping and patching ordinary corridor surfaces after the fact.

The next design should treat intersections as a road-network and edge-network problem first, then generate surfaces from that controlled topology.

## 2. Core Rule

Do not build an intersection by repairing ordinary corridor surface fragments.

Build the intersection from explicit junction intent:

1. participating road legs
2. control area
3. edge network
4. vertical control
5. structured surface zones
6. exterior daylight boundaries

Ordinary corridor Regions should stop or transition at the intersection control area.

Intersection-owned geometry should create the junction interior, curb-return areas, side-road tie-ins, drainage low-point context, and watertight-solid handoff.

## 3. Lessons From Existing Road Design Tools

### 3.1 Civil 3D

Civil 3D treats corridors as Alignment + Profile + Assembly + Feature Line systems.

Complex corridors such as intersections use multiple baselines, Regions, targets, and corridor rebuilding.

Civil 3D Intersection objects can update corridor Regions so Region station ranges stay synchronized with the intersection area geometry.

Implication for Parametric Road:

- intersection source state should own the relationship between participating Alignments
- Regions should be derived or validated against the intersection control area
- offset/elevation targets should be explicit edge or profile references
- Build Parametric should not infer intersection boundaries from final mesh fragments

References:

- Autodesk Civil 3D Corridor Modeling: https://help.autodesk.com/cloudhelp/2023/ENU/Civil3D-UserGuide/files/GUID-F2246A0B-809E-4801-97A5-EFACFA05EE46.htm
- Autodesk Civil 3D Corridor Regions: https://help.autodesk.com/view/CIV3D/2025/ENU/?guid=GUID-30C77B59-8DEA-4FFB-BC79-9BBE45DE1A50
- Autodesk Civil 3D Intersection Region Update: https://help.autodesk.com/view/CIV3D/2025/ENU/?guid=GUID-AEEE06FE-D8CD-4588-8A29-A6E8378A10C6
- Autodesk Civil 3D Corridor Targets: https://help.autodesk.com/cloudhelp/2023/ENU/Civil3D-UserGuide/files/GUID-AD5B70C3-3F7C-4B53-8F5D-E565001EF173.htm

### 3.2 OpenRoads Designer

OpenRoads uses a model-centric corridor workflow with templates, template drops, point controls, linear templates, and Civil Cells.

Intersections are commonly handled as reusable civil-cell or feature-network behavior that attaches to corridor features and updates with source changes.

Implication for Parametric Road:

- an intersection should behave like a reusable parametric junction cell
- control points and edge features should be first-class outputs
- side-road tie-in should be handled through generated section/control rows, not mesh bridges
- clipping should be a controlled boundary operation, not a visual cleanup pass

References:

- Bentley OpenRoads Designer overview: https://www.bentley.com/software/openroads-designer/
- CTDOT OpenRoads Civil Cells guide: https://portal.ct.gov/dot/-/media/dot/aec/cad-connect-dde-guide/ctdot-connect-dde-volume-3_4---openroads-designer-civil-cells.pdf

### 3.3 InfraWorks

InfraWorks creates intersections where component roads meet.

The intersection object exposes widening zones, turning zones, lane groups, roundabout conversion, design vehicle, and superelevated intersection review.

Implication for Parametric Road:

- the Intersections panel should expose clear junction type and design-vehicle intent
- intersection preview should show editable control zones before final surface build
- widening, turn paths, and curb-return sizing should be source policy, not hard-coded geometry

Reference:

- Autodesk InfraWorks Intersections: https://help.autodesk.com/cloudhelp/ENU/InfraWorks-RoadsandHighways/files/GUID-6871B3B2-93EC-4276-A0D9-4CBEDB06874B.htm

### 3.4 Trimble Novapoint

Novapoint provides dedicated tools for Roundabout, T-Intersection, and X-Intersection.

The T-Intersection workflow separates road arms and lets users define medians, deflection islands, turn lanes, widths, curb radii, design vehicle, and design speed.

Implication for Parametric Road:

- T, Cross, Y, and Roundabout should become explicit intersection kinds
- each road arm should have stable identity
- arm-level lane, island, and curb-return policies should be stored in source rows

References:

- Trimble Novapoint Intersection Tools: https://help.trimble.com/en/novapoint/novapoint/road/road-cad-tools/intersection-tools
- Novapoint T-Intersection library note: https://community.trimble.com/viewdocument/t-intersection

### 3.5 12d Model

12d emphasizes string-based and super-alignment design.

Intersections, turning lanes, and roundabouts are generated through parametric geometry and linked design objects.

Templates and modifiers control width, crossfall, height, hinge strings, and other local behavior.

Implication for Parametric Road:

- edge strings should be the primary geometry source for intersection surfaces
- width/crossfall/height modifiers should be attached to legs and edge families
- the final surface should be generated from controlled strings, not from unordered TIN repair

References:

- 12d Detailed Alignment Design: https://www.12d.com/product/12d_model_alignment.html
- 12d Roads and Highways: https://www.12d.com/product/road-and-highways.html

## 4. Target Architecture

### 4.1 Source Layer

Add or extend source objects so intersection intent is explicit.

Required source families:

- `IntersectionModel`
- `IntersectionRow`
- `IntersectionLegRow`
- `IntersectionControlArea`
- `IntersectionArmPolicyRow`
- `CurbReturnPolicyRow`
- `IntersectionEdgePolicyRow`
- `IntersectionGradingPolicyRow`
- `IntersectionDrainagePolicyRow`

Key source rules:

- one road leg references one Alignment/Profile/Region context
- side-road alignment means a separate road centerline, not a main-road edge line
- curb-return geometry is source policy plus generated edge output
- ordinary Regions may reference an intersection, but they do not own junction geometry
- Drainage and Structures may reference intersection legs, edges, and low-point zones

### 4.2 Evaluation Layer

Create an `IntersectionTopologyEvaluationService`.

The service should produce a deterministic topology result before any surface is built.

Expected result rows:

- participating leg rows
- intersection center point
- leg approach/departure spans
- conflict/control area polygon
- curb-return candidate arcs
- lane-edge rows
- shoulder-edge rows
- gutter/ditch edge rows where available
- daylight hinge edge rows
- low-point candidates
- diagnostics

### 4.3 Result Layer

Introduce explicit result contracts.

Proposed contracts:

- `IntersectionTopologyResult`
- `IntersectionEdgeNetworkResult`
- `IntersectionVerticalControlResult`
- `IntersectionSurfaceZoneResult`
- `IntersectionDrainageHintResult`
- `IntersectionSolidTargetResult`

The edge network result is the main handoff.

Build Parametric should consume edge network rows, not reconstruct intersection geometry from mesh objects.

### 4.4 Output Layer

Generated output objects should be traceable and separable:

- `Intersection Edge Network`
- `Intersection Design Surface`
- `Intersection Curb Return Surface`
- `Intersection Slope Face Surface`
- `Intersection Low Point Review`
- `Intersection Solid Target`

Ordinary corridor surfaces should stop at or be clipped by the intersection control area.

Intersection surfaces should fill the control area through structured zones.

## 5. Surface Strategy

### 5.1 Do Not Use One Patch For Everything

The current `Intersection Surface` tries to behave like one patch.

The new design should use surface zones:

- main-road pavement strip inside the control area
- side-road pavement strip inside the control area
- curb-return quadrant zones
- central blended junction zone
- shoulder/ditch transition zones
- exterior daylight/slope zones

Each zone has:

- owner
- boundary edges
- vertical policy
- triangulation method
- source refs
- diagnostics

### 5.2 Edge-First Build

The build order should be:

1. generate leg centerline references
2. generate pavement/lane/shoulder edge rows
3. generate curb-return arc edge rows
4. generate tie-in edges
5. assign elevation/crossfall to all edge rows
6. create zone boundaries
7. triangulate each zone
8. merge only after topology validation

### 5.3 Curb Return

Curb-return arcs should not be decorative review arcs.

They should be boundary edges used by:

- pavement surface zones
- slope face zones
- drainage low-point search
- solid target boundaries

### 5.4 Slope Face

Slope Face should be generated outside the design edge network.

Rules:

- no Slope Face inside the pavement/control area
- no whole-corridor Slope Face across the junction interior
- side-road Slope Face must connect to curb-return exterior edge through explicit zone boundaries
- main-road Slope Face must stop at the control area and resume outside it
- if an edge relation is missing, report a topology diagnostic instead of creating a guessed triangle

### 5.5 Intersection Slope Face Boundary

Intersection Slope Face generation should not rely only on ordinary corridor daylight sampling.

For the junction edge zone, Build Parametric should first create an explicit `IntersectionSlopeFaceBoundaryResult`.

The boundary result uses:

- the `Intersection Surface` outer boundary as the inner Slope Face boundary
- Applied Section left/right start points as the inner Slope Face boundary candidates
- Applied Section left/right end points as the outer Slope Face boundary candidates
- Alignment context to separate primary-road and side-road strips
- side context to separate left and right strips
- station order to connect boundary points without crossing
- the Applied Sections that actually define each tie-in edge, not the full alignment section list
- a distance-based extension before and after the tie-in edge

The intended strip is:

```text
Applied Section end points
  -> outer boundary

Intersection Surface boundary edge
  -> inner boundary

start/end connector edges
  -> strip closure

closed strip
  -> Intersection Slope Face Surface
```

The boundary extension must be distance-based, not "one more station" based.

Default rule:

- extend the boundary by `5.0 m` before the tie-in start station
- extend the boundary by `5.0 m` after the tie-in end station
- create virtual Applied Sections at the extension stations by interpolation
- if the extension station is outside the available section range, project the nearest Applied Section along its tangent

This keeps the transition zone stable when Applied Section spacing is coarse or irregular.

The extension must apply to both Applied Section start points and end points.

Using only end points makes the preview strip become a trapezoid that does not follow the section boundary.

For the first implementation, Build Parametric should create this boundary only for the primary-road outside tie-in edge that needs Slope Face completion.

It must not generate all primary/secondary left/right boundary candidates as visible white rectangles.

This boundary is a result contract, not an editable source object.

It must record:

- `intersection_id`
- `alignment_ref`
- `side`
- `inner_boundary_points`
- `outer_boundary_points`
- `start_tie_edge`
- `end_tie_edge`
- `source_applied_section_refs`
- `source_intersection_surface_ref`
- `status`
- `diagnostics`

Build Parametric should record the boundary before using it for triangulation.

The visible boundary preview object is currently suppressed.

Boundary review is metadata-only until a production-safe boundary display is approved.

The visible strip triangulation step is currently suppressed.

The earlier implementation appended `intersection_slope_face_boundary_strip` triangles to the Slope Face Surface result, but manual QA showed visible forced rectangular patches in Side Slope Surface areas.

Build Parametric now records boundary metadata only:

- `intersection_slope_face_boundary_strip_count`
- `intersection_slope_face_boundary_strip_sample_count`
- `intersection_slope_face_boundary_strip_triangle_count`
- `intersection_slope_face_boundary_strip_generation_mode=suppressed`
- `intersection_slope_face_boundary_strip_output_path=metadata_only`

The ordinary `Corridor Slope Face Surface` remains responsible outside the intersection footprint.

The `Intersection Surface` remains responsible inside the intersection footprint.

### 5.6 Deferred: Intersection Corner Slope Face Boundary

The old curb-return-wide Slope Face band strategy is removed from the active build path.

Build Parametric should not create a full Slope Face band around the entire curb-return arc.

The attempted corner-specific Slope Face boundary rows are also removed from the active build path.

The removed approach tried to use:

- side-road Applied Section start/end slope edge points
- one nearest curb-return arc sample point for each start/end slope edge point
- the intersection id
- the secondary alignment ref
- side context

The approach is deferred because robust point selection is harder than expected with the current TIN-first intersection output.

Do not reintroduce this as a quick helper that guesses nearest arc points.

Future work should solve this at the topology/control-edge level before surface generation.

The deferred target remains:

```text
explicit intersection control edges
  -> validated boundary loops
  -> Slope Face Surface generation from those loops
```

For now, Build Parametric keeps only the stable primary outside Slope Face boundary strip support.

## 6. Vertical And Crossfall Strategy

Intersection vertical control should be separate from ordinary Superelevation.

Inputs:

- primary profile
- secondary profile
- sampled 3D Centerline rows
- crossfall/superelevation model
- grading policy

Policies:

- `primary_controls`
- `secondary_controls`
- `blend_profiles`
- `flatten_intersection`
- `manual_edge_elevation`

Crossfall should be calculated per surface zone.

Superelevation remains the source for normal road sections, but intersection policy may override it inside the control area.

## 7. Drainage Strategy

Intersection drainage should be reviewed after surface zones are created.

Required outputs:

- low-point candidate rows
- gutter/ditch edge rows
- inlet recommendation rows
- flow direction hints
- drainage element coverage status

Do not size pipes or run hydraulic analysis in this redesign phase.

The goal is to make the geometry and low-point context stable enough for future drainage simulation.

## 8. Watertight Solid Strategy

Intersection solids should be discovered as separate targets.

Target families:

- `intersection_pavement_body`
- `intersection_subgrade_body`
- `intersection_slope_body`
- `intersection_curb_return_body`
- future `intersection_drainage_context_body`

Each target should carry:

- edge network source refs
- surface zone refs
- open edge diagnostics
- non-manifold diagnostics
- merge readiness

The final simulation goal remains a set of watertight solids that can be combined or exported by target family.

## 9. UI Plan

### 9.1 Intersections Panel

Replace the current first-slice panel behavior with a staged workflow:

1. Select intersection type
2. Select source mode
3. Select participating legs
4. Define control area
5. Define curb-return policy
6. Define grading/crossfall policy
7. Preview edge network
8. Apply

Tables:

- `Intersections`
- `Legs`
- `Control Area`
- `Curb Returns`
- `Edge Policies`
- `Grading`
- `Diagnostics`

Buttons:

- `Auto Detect`
- `Create Starter Sources`
- `Review Contract Diagnostics`
- `Preview Zones`
- `Apply`
- `Close`

### 9.2 Build Parametric Panel

Guided Review should become:

1. Centerline
2. Design Surface
3. Intersection Edge Network
4. Intersection Surface Zones
5. Slope Face Issues
6. Drainage Surface
7. Drainage Flow

Review rows should report:

- topology status
- zone count
- missing edge relations
- curb-return count
- low-point candidate count
- clipped ordinary corridor triangle count
- intersection-owned triangle count

### 9.3 3D Review

Users should be able to independently show/hide:

- leg centerlines
- edge network
- curb-return edges
- surface zones
- slope face zones
- low-point markers
- diagnostics

Double-click behavior:

- leg row highlights leg centerline and control span
- edge row highlights the exact edge
- zone row highlights only that surface zone
- diagnostic row highlights the failed topology relation

## 10. Implementation Phases

| Phase | Status | Scope | Acceptance Criteria |
| --- | --- | --- | --- |
| 1 | Done | Current implementation freeze | Current one-patch intersection preview is marked `legacy_patch_frozen`, review notes point to `edge_network_first`, and no new mesh-repair expansion should be added to that path. |
| 2 | Done | Source model extension | Added arm, curb-return, edge, grading, and drainage policy rows to the source contract without changing generated geometry. |
| 3 | Done | Topology evaluator | Produces `IntersectionTopologyResult` with leg spans, control areas, policy refs, source refs, and diagnostics without building geometry. |
| 4 | Done | Edge network result | Produces leg, curb-return, and daylight edge rows with stable IDs from topology and source policies. |
| 5 | Removed | Standalone edge-network geometry | Standalone edge-network geometry was removed; edge-network review now happens through source/result contracts and Build Parametric `Intersections` diagnostics. |
| 6 | Done | Surface zone contracts | Adds `IntersectionSurfaceZoneResult`, candidate zone rows, and zone diagnostics without triangulation. |
| 7 | Done | Intersection design zones | Generates main, side, central, and curb-return pavement zone responsibilities from the edge network without triangulation. |
| 8 | Done | Slope face zones | Generates exterior Slope Face zone boundary contracts from daylight, pavement, and curb-return edge rows without triangulation. |
| 9 | Done | Ordinary corridor clipping | Adds ordinary corridor design/slope clipping contracts by control area before surface merge. |
| 10 | Done | Build Parametric review | Shows Topology, Edge Network, Surface Zone, and Corridor Clip rows with focus/highlight behavior. |
| 11 | Done | Cross Section Viewer | Shows active intersection leg, edge, zone, grading, drainage, and corridor-clip context. |
| 12 | Done | Drainage hints | Generates low-point and inlet recommendation rows from surface zones. |
| 13 | Done | Watertight target handoff | Discovers planned intersection pavement/subgrade/slope/curb-return targets from surface-zone contracts. |
| 14 | Ready | Manual QA | T, Cross, and Y starter intersection manual QA procedure is documented; real-document execution remains manual. |
| 15 | Ready | Slope Face loop stabilization | Source-traceable intersection Slope Face loop contracts and reviewed TIN output are implemented; real-document visual QA remains manual. |

## 11. Migration Strategy

No legacy file migration is required.

Current first-slice intersection implementation may remain as a fallback until the new edge-network path is usable.

Once Phase 7 and Phase 8 are stable:

- deprecate current one-patch intersection surface build
- remove ad-hoc Slope Face repair paths
- remove review-only curb-return mesh dependencies
- keep source row IDs stable where practical

## 12. Manual QA

Detailed manual QA is maintained in `V1_INTERSECTION_MANUAL_QA.md`.

The steps below are the short-form checklist.

### 12.1 T-Intersection

1. Create starter T-intersection sources.
2. Build 3D Centerline.
3. Build Sections.
4. Build Parametric.
5. Confirm main leg and side leg have separate centerlines.
6. Confirm edge-network contract rows preserve curb-return to pavement edge lineage.
7. Show only `Intersection Surface Zones`.
8. Confirm no ordinary Slope Face exists inside the control area.
10. Show only `Intersection Slope Face Surface`.
11. Confirm side-road Slope Face connects to curb-return exterior edge.
12. Confirm diagnostics are `ready` or actionable `warning`.

### 12.2 Cross Intersection

1. Create starter Cross-intersection sources.
2. Confirm four leg identities.
3. Confirm four curb-return edge sets.
4. Confirm central junction zone is closed.
5. Confirm no overlapping pavement zone triangles.

### 12.3 Y Intersection

1. Create starter Y-intersection sources.
2. Confirm skewed leg geometry does not use global-axis fallback.
3. Confirm curb-return radius policy is applied per leg pair.
4. Confirm surface zones remain non-self-crossing.

## 13. Risks

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Edge network model becomes too complex | Slow implementation | Start with T-intersection only. |
| Surface zone triangulation fails | Broken preview | Keep zones small, explicit, and diagnosable. |
| Ordinary corridor clipping removes too much | Missing road surface | Clip only by accepted control area and expose clipped counts. |
| Vertical policy is ambiguous | Twisted surfaces | Require explicit grading policy per intersection. |
| Drainage expectations grow too early | Scope creep | Keep drainage to low-point hints and coverage checks first. |
| Watertight solid demands force premature geometry | Unstable solids | Generate solids only after edge network and zones pass topology checks. |

## 14. Decision

Adopt an edge-network-first intersection redesign.

The current patch-and-repair approach should stop after short-term stabilization.

The next implementation should begin with Phase 1 through Phase 4:

1. freeze current mesh repair expansion
2. extend source contracts
3. add topology evaluation
4. add edge network result and preview

Phase 1 completion note:

- `V1CorridorIntersectionSurfacePreview` exposes `IntersectionImplementationMode = legacy_patch_frozen`.
- `V1CorridorIntersectionSurfacePreview` exposes `IntersectionRedesignPath = edge_network_first`.
- Build Parametric review notes include the implementation mode and next redesign path.
- Future work should add the edge-network path instead of adding more triangle repair rules to the frozen one-patch path.

Phase 2 completion note:

- `IntersectionLegRow` now carries `arm_policy_ref`, `edge_policy_refs`, and `grading_policy_ref`.
- `IntersectionModel` now stores `arm_policy_rows`, `edge_policy_rows`, and `drainage_policy_rows` in addition to existing curb-return and grading policy rows.
- `V1IntersectionModel` FreeCAD source objects persist the new policy row families through JSON and count properties.
- The Intersections panel creates default arm, pavement-edge, daylight-edge, grading, curb-return, and low-point drainage policies when applying source rows.
- No generated intersection surface behavior was changed in this phase.

Phase 3 completion note:

- Added `IntersectionTopologyResult` as the source-level topology handoff before edge or surface generation.
- Added `IntersectionTopologyLegSpanRow` for participating leg spans.
- Added `IntersectionTopologyControlAreaRow` for control-area and influence-area spans.
- `IntersectionEvaluationService.evaluate_topology()` now reports participating alignment count, control Region count, leg span count, control area count, policy refs, source refs, and diagnostics.
- The evaluator reports missing source essentials as `error:*` diagnostics and incomplete policy links as `warning:*` diagnostics.
- No generated intersection surface behavior was changed in this phase.

Phase 4 completion note:

- Added `IntersectionEdgeNetworkResult` as the edge-network handoff before surface-zone generation.
- Added `IntersectionEdgeNetworkRow` for deterministic leg, daylight, and curb-return edge rows.
- `IntersectionEvaluationService.evaluate_edge_network()` now consumes `IntersectionTopologyResult` and `IntersectionModel` source policies.
- Leg edge rows carry source policy refs, leg refs, control-area refs, alignment refs, station spans, edge roles, and side information.
- Curb-return policy rows now produce `curb_return_edge` rows instead of remaining only as review arc intent.
- Topology `error:*` diagnostics stop edge generation; topology `warning:*` diagnostics are carried forward.
- No generated intersection surface behavior was changed in this phase.

Phase 5 removal note:

- Standalone edge-network geometry is no longer exposed.
- The panel must not create a dedicated edge-network preview object.
- Edge-network status, counts, edge IDs, source refs, and diagnostics are reviewed through result contracts.
- This prevents preview geometry from being mistaken for accepted surface source truth.

Phase 6 completion note:

- Added `IntersectionSurfaceZoneResult` as the handoff before surface-zone triangulation.
- Added `IntersectionSurfaceZoneRow` for candidate central junction, leg pavement, curb-return, and exterior slope-face zones.
- `IntersectionEvaluationService.evaluate_surface_zones()` now consumes `IntersectionEdgeNetworkResult`.
- Edge-network `error:*` diagnostics stop zone evaluation; edge-network warnings are carried forward.
- Candidate zone rows carry source edge refs, leg refs, control-area refs, surface role, zone family, vertical policy ref, pending triangulation method, status, and diagnostics.
- No generated intersection surface behavior was changed in this phase.

Phase 7 completion note:

- Surface zone rows now identify `design_zone_role`.
- Design zone roles currently include `central_pavement`, `main_pavement`, `side_pavement`, `curb_return_pavement`, and `exterior_slope_face`.
- `IntersectionSurfaceZoneResult` now counts design zones, central pavement zones, main pavement zones, side pavement zones, curb-return zones, and slope-face zones separately.
- Curb-return zone rows carry participating leg, alignment, and control-area context resolved from pavement edge rows.
- This phase still does not generate triangles or mesh geometry.

Phase 8 completion note:

- Exterior Slope Face zone rows now carry explicit edge-boundary responsibility.
- Each Slope Face zone records `outer_edge_refs` from daylight hinge edges, `inner_edge_refs` from matching pavement edges, and `tie_edge_refs` from curb-return edges that reference the same leg.
- `boundary_edge_refs` combines those edge refs so later triangulation can build only from accepted topology.
- Slope Face zones become `ready` only when the required pavement and curb-return tie context exists.
- Missing pavement or curb-return relations are reported as topology diagnostics instead of generating guessed triangles.
- This phase still does not generate triangles or mesh geometry.

Phase 9 completion note:

- Added `IntersectionCorridorClipResult` as the handoff for ordinary corridor clipping before surface merge.
- Added `IntersectionCorridorClipRow` for ordinary design and ordinary Slope Face clipping responsibilities.
- `IntersectionEvaluationService.evaluate_corridor_clipping()` now consumes topology and surface-zone results.
- Clip rows are generated per control area and surface role.
- Clip rows carry station ranges, influence ranges, control Region refs, protected intersection zone refs, boundary source, timing, method, status, and diagnostics.
- Missing control Region refs are reported as warnings instead of silently clipping against an ambiguous target.
- This phase still does not generate triangles or modify Build Parametric mesh output.

Phase 10 completion note:

- Build Parametric now includes an `Intersections` review tab.
- The tab lists topology, edge-network, surface-zone, and ordinary corridor clipping contract rows.
- `corridor_intersection_contract_review_rows()` exposes stable row data for UI, tests, and future review handoff.
- Row status, role, source refs, boundary refs, and diagnostics are shown before final intersection surface generation.
- Double-clicking an intersection contract row focuses the best available review object, such as edge-network, intersection surface, or exclusion-zone preview output.
- This phase keeps the legacy patch preview path frozen and does not add new mesh repair behavior.

Phase 11 completion note:

- Cross Section Viewer payloads now include `intersection_context_rows` when the focused Applied Section has active intersection context.
- The context rows are generated from `IntersectionEvaluationService` topology, edge-network, surface-zone, and corridor-clipping contracts.
- The Viewer now shows an `Intersection Context` table with family, status, ID, role, source refs, boundary refs, handoff owner, handoff target, lineage status, and notes.
- Viewer summary text also reports the intersection contract row count and grouped contract summary.
- The table includes active leg, control area, pavement/daylight/curb-return edge context, surface-zone responsibility, ordinary corridor clipping responsibility, grading policy, and drainage policy.
- This phase is review-only and does not generate or modify mesh geometry.

Phase 12 completion note:

- Added `IntersectionDrainageHintResult` as the review handoff between surface-zone responsibility and future drainage element generation.
- Added `IntersectionDrainageHintRow` for low-point candidate and inlet recommendation rows.
- `IntersectionEvaluationService.evaluate_drainage_hints()` consumes accepted `IntersectionSurfaceZoneResult` rows.
- Central pavement zones produce `low_point_candidate` rows for low-point review.
- Curb-return pavement zones and exterior Slope Face zones produce `inlet_recommendation` rows.
- Build Parametric `Intersections` review rows now include `drainage_hint` contracts.
- Cross Section Viewer intersection context rows now include matching drainage hint rows for the focused control area.
- This phase is review-only and does not create Drainage Elements, Structures, pipes, or mesh geometry.

Phase 13 completion note:

- `SolidTargetRow` now accepts intersection zone target families: `intersection_pavement_body`, `intersection_subgrade_body`, `intersection_slope_body`, and `intersection_curb_return_body`.
- `SolidTargetDiscoveryService` evaluates intersection surface-zone contracts and creates zone-scoped Watertight Solid target handoff rows.
- Pavement zones create `intersection_pavement_body` and `intersection_subgrade_body` target candidates.
- Curb-return zones create `intersection_curb_return_body` and `intersection_subgrade_body` target candidates.
- Exterior Slope Face zones create `intersection_slope_body` target candidates.
- These rows are marked `planned` because Phase 13 is target discovery and handoff only; Part solid building for these zone families remains a later implementation step.
- The Watertight Solids panel labels the new target families separately so users can see pavement, subgrade, slope, and curb-return handoff candidates.

Phase 14 readiness note:

- Added `V1_INTERSECTION_MANUAL_QA.md` as the active manual QA procedure for T, Cross, and Y starter intersections.
- The procedure checks source creation, multi-alignment 3D Centerline, Applied Sections, Build Parametric `Intersections` contracts, Cross Section Viewer context, drainage hints, and Watertight Solid target handoff.
- Phase 14 is marked `Ready`, not `Done`, because actual visual QA must be executed in FreeCAD on a real document.
- Passing manual QA must not rely on manually deleting or hiding generated geometry.

## 15. Intersection Slope Face Stabilization Plan

### 15.1 Purpose

The current Slope Face issue is not a display-only problem.

It comes from trying to repair generated TIN triangles after ordinary corridor surfaces and intersection patch surfaces already exist.

The next implementation should stop adding ad-hoc corner strips, cap faces, or guessed arc-to-section bridges.

Slope Face near an intersection should be generated from explicit intersection control edges and validated boundary loops.

### 15.2 Current Problem

Observed issues:

- ordinary `Corridor Slope Face Surface` can remain inside or across the intersection control area
- side-road Slope Face can stop before the curb-return or intersection edge
- main-road Slope Face can leave holes near the intersection boundary
- generated repair strips can pick wrong curb-return points
- generated repair strips can overlap or protrude through the `Intersection Surface`
- nearest-point matching is unreliable around curb-return arcs

### 15.3 Core Rule

Do not infer intersection Slope Face geometry from nearest mesh points.

Do not create new geometry by connecting arbitrary generated TIN vertices.

Use this order instead:

```text
Intersection source intent
  -> topology result
  -> edge network result
  -> surface zone result
  -> Slope Face boundary loop result
  -> Slope Face TIN output
  -> review/solid handoff
```

### 15.4 Boundary Loop Strategy

Create a new `IntersectionSlopeFaceLoopResult`.

Each loop row should describe one closed Slope Face responsibility area.

Minimum loop families:

- `primary_outside_loop`
- `secondary_outside_loop`
- `curb_return_left_loop`
- `curb_return_right_loop`
- `corner_gap_loop`

Each row should carry:

- `loop_id`
- `intersection_id`
- `alignment_ref`
- `leg_ref`
- `side`
- `loop_family`
- `inner_edge_refs`
- `outer_edge_refs`
- `tie_edge_refs`
- ordered `loop_points_xyz`
- source Applied Section refs
- source edge-network refs
- status
- diagnostics

The loop is valid only when:

- it has at least four ordered points
- it is closed in XY within tolerance
- it does not self-cross
- it does not overlap the `Intersection Surface` interior
- it has source refs back to accepted topology or Applied Sections

### 15.5 Applied Section Role

Applied Sections remain important, but they should not be used as free-floating repair anchors.

They should provide:

- pavement edge points
- daylight hinge points
- slope edge points
- station/frame context
- active intersection context

Build Parametric may add generated intersection tie-in Applied Sections, but only when they are represented as source-traceable section rows before Slope Face generation.

The Slope Face builder should consume these rows through the same section contract used by ordinary corridor surfaces.

### 15.6 Surface Generation Strategy

The next Slope Face generation path should be:

1. Evaluate intersection topology and edge network.
2. Evaluate surface zones.
3. Build Slope Face loops from accepted surface-zone rows.
4. Triangulate each loop independently.
5. Suppress ordinary corridor Slope Face inside accepted intersection loops.
6. Keep intersection Slope Face output as a separate reviewable family before final merge.

Do not append loose triangles after TIN construction.

Do not use curb-return arc bands as a standalone repair surface.

Do not use nearest arc sample matching as a production rule.

### 15.7 UI And Review Plan

Build Parametric should expose:

- `Intersection Slope Face Loops` review row
- loop count
- ready/warning/error count
- loop family summary
- self-crossing diagnostics
- overlap diagnostics
- source edge refs

The `Intersections` tab should allow double-click focus for:

- topology row
- edge network row
- surface zone row
- Slope Face loop row
- Slope Face output row

The 3D view should use distinct colors:

- edge network: green
- surface zone boundary: magenta
- Slope Face loop boundary: white
- loop diagnostics: red
- overlap/cut line diagnostics: yellow

### 15.8 Implementation Order

| Step | Status | Work Item | Acceptance |
| --- | --- | --- | --- |
| 15.1 | Done | Freeze ad-hoc corner repair path | No active code creates corner Slope Face strips from nearest curb-return arc points. |
| 15.2 | Done | Add `IntersectionSlopeFaceLoopResult` contract | Loop rows can be created and validated without generating mesh. |
| 15.3 | Done | Build loop evaluator from surface zones | Primary, secondary, curb-return, and gap loop candidates are listed with source edge refs. |
| 15.4 | Done | Add loop preview | Build Parametric can display and focus each loop boundary in 3D. |
| 15.5 | Done | Add loop diagnostics | Open, self-crossing, overlap, and missing-source loops report actionable diagnostics. |
| 15.6 | Done | Triangulate ready loops only | Ready loop rows generate separate intersection Slope Face TIN triangles. |
| 15.7 | Done | Suppress ordinary Slope Face by loop ownership | Ordinary Slope Face is removed only where accepted intersection loops own the area. |
| 15.8 | Done | Merge review output | Build Parametric shows ordinary Slope Face and intersection Slope Face as separate review families before final merge. |
| 15.9 | Done | Manual QA update | T, Cross, and Y QA include Slope Face loop visibility and diagnostics. |

### 15.9 Acceptance Criteria

For the T-intersection starter:

- no ordinary Slope Face exists inside the `Intersection Surface`
- no Slope Face triangle protrudes through the intersection pavement surface
- side-road Slope Face reaches the accepted intersection tie-in boundary
- main-road Slope Face stops and resumes at accepted loop boundaries
- curb-return exterior Slope Face is generated from a validated loop, not a guessed band
- all Slope Face loop rows have source edge refs and diagnostics
- failed loops remain visible as diagnostics instead of generating broken mesh

Manual QA must also verify:

- `Guided Review` step `4. Slope Face Issues` reports both ordinary and intersection-owned Slope Face output.
- `Results` includes separate rows for `Slope Face Surface` and `Intersection Slope Face Surface`.
- The `Intersections` contract table includes `slope_face_loop` rows.
- Double-clicking a `slope_face_loop` row highlights the selected loop itself as one thick yellow closed or ordered boundary line, not arbitrary mesh vertices.
- Showing only `Intersection Slope Face Surface` displays only geometry generated from `ready` loop rows.
- Showing only ordinary `Slope Face Surface` confirms ordinary triangles are suppressed only where accepted intersection loops own the area.
- Ordinary Slope Face preview properties expose loop suppression status, ready loop count, tested triangle count, suppressed triangle count, and kept triangle count.
- Intersection Slope Face preview objects are routed under `04_Parametric Model > Intersections`.
- Warning or error loop rows remain visible as diagnostics and do not create `Intersection Slope Face Surface` triangles.

Fail conditions:

- ordinary Slope Face triangles remain inside an accepted loop-owned area
- intersection-owned Slope Face mesh is generated from a warning or error loop
- `slope_face_loop` rows cannot be focused in 3D
- loop preview or intersection Slope Face preview objects appear at the tree root
- empty ready-loop input causes a traceback

### 15.10 Non-goals

- complete lane-based intersection design
- traffic island design
- final watertight solid construction
- automatic hydraulic design
- arbitrary mesh boolean cleanup
- hidden repair triangles with no source refs

### 15.11 Phase 15.1 Completion Note

- Removed the attempted corner-specific Slope Face boundary row generator from the active build path.
- Removed nearest-arc and arc-intersection helper code used by the deferred corner repair approach.
- Removed unused gap/corner closure helper code that could append ad-hoc repair triangles after TIN construction.
- Removed obsolete gap/corner closure preview properties from Slope Face preview output.
- The remaining Slope Face stabilization work must proceed through `IntersectionSlopeFaceLoopResult`, not mesh repair helpers.

### 15.12 Phase 15.2 Completion Note

- Added `IntersectionSlopeFaceLoopRow` as the row-level contract for one closed Slope Face responsibility loop.
- Added `IntersectionSlopeFaceLoopResult` as the result-level handoff before triangulation.
- Loop rows carry loop family, source edge refs, source Applied Section refs, ordered loop points, closure/self-crossing/overlap flags, status, diagnostics, and notes.
- The result contract tracks ready, warning, error, primary outside, secondary outside, curb-return, and corner-gap loop counts.
- This phase does not generate mesh geometry or alter Build Parametric surface output.

### 15.13 Phase 15.3 Completion Note

- Added `IntersectionEvaluationService.evaluate_slope_face_loops()`.
- The evaluator consumes `IntersectionSurfaceZoneResult` and creates one loop candidate per slope-face surface zone.
- Loop candidates carry inner, outer, tie, boundary, source edge-network, and source surface-zone refs.
- Missing inner, outer, or tie edge refs are reported as warnings instead of generating guessed geometry.
- Loop family classification is first-slice and source-ref based; detailed point ordering and loop validation remain Phase 15.4 and Phase 15.5 work.
- This phase does not generate mesh geometry or alter Build Parametric surface output.

### 15.14 Phase 15.4 Completion Note

- Build Parametric no longer creates `V1CorridorIntersectionSlopeFaceLoopPreview` by default.
- Slope Face Loop contract metadata remains available on the main Intersection preview and related review rows.
- The preview is linework only; it exposes candidate loop references before any new Slope Face mesh generation is attempted.
- Intersection contract review includes `slope_face_loop` rows, and double-click focus highlights the related loop boundary edges in 3D.
- The preview is routed under `04_Parametric Model > Intersections` with the other intersection review/output objects.

### 15.15 Phase 15.5 Completion Note

- `evaluate_slope_face_loops()` now consumes the evaluated edge network so loop rows can derive candidate point sequences from source edge refs.
- Loop rows now report unresolved edge refs, duplicate edge refs, too-few points, open XY loops, self-crossing risk, and missing source-edge refs before mesh generation.
- Loop status is promoted to `ready`, `warning`, or `error` from diagnostics instead of remaining a generic candidate.
- The loop preview object exposes open-loop, self-crossing, overlap, and point-count summary properties for review.

### 15.16 Phase 15.6 Completion Note

- Build Parametric now creates a separate `V1CorridorIntersectionSlopeFaceSurfacePreview` from `ready` Slope Face loop rows only.
- Non-ready loop rows are skipped; they remain review diagnostics and do not generate hidden repair triangles.
- The first-slice triangulation is a simple loop fan TIN for review handoff, not the final production Slope Face algorithm.
- The generated preview is routed under `04_Parametric Model > Intersections` and carries source loop refs, ready/skipped loop counts, and triangle count.

### 15.17 Phase 15.7 Completion Note

- Ordinary `Corridor Slope Face Surface` now checks the ready-loop `Intersection Slope Face Surface` footprint before final preview output.
- Daylight triangles overlapping accepted intersection Slope Face loop ownership are suppressed with quality metadata.
- If no ready loops exist, suppression is skipped and recorded as such; warning/error loops still do not remove ordinary geometry.
- The ordinary Slope Face preview exposes ready loop count, tested/suppressed/kept triangle counts, and reference surface id.

### 15.18 Phase 15.8 Completion Note

- Build Parametric review now lists `Intersection Slope Face Surface` separately from ordinary `Slope Face Surface`.
- Guided Review `4. Slope Face Issues` now considers both ordinary Slope Face and intersection-owned Slope Face output.
- Ordinary Slope Face review notes include loop-ownership suppression counts when available.
- Intersection Slope Face review notes expose ready loop count, skipped loop count, and source loop count so users can distinguish accepted loop output from diagnostics.

### 15.19 Phase 15.9 Completion Note

- Updated the manual QA expectation for T, Cross, and Y intersections to include Slope Face loop review.
- QA now requires separate review of ordinary `Slope Face Surface` and `Intersection Slope Face Surface`.
- QA now checks loop focus, loop diagnostics, ready-loop-only triangulation, ordinary Slope Face suppression metadata, and project-tree routing.
- Phase 15 is implementation-complete for the current loop-owned Slope Face review path, but final pass/fail still depends on manual FreeCAD visual QA on real T, Cross, and Y documents.

This matches the direction used by mature road design tools: intersections are controlled by dedicated junction intent, road arms, edge geometry, targets, and structured zones before final surfaces are generated.
