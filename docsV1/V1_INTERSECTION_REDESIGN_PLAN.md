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
- `Preview Edge Network`
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
| 5 | Done | Preview edge network | Intersections panel can create a 3D `Intersection Edge Network Preview` before surface build. |
| 6 | Done | Surface zone contracts | Adds `IntersectionSurfaceZoneResult`, candidate zone rows, and zone diagnostics without triangulation. |
| 7 | Done | Intersection design zones | Generates main, side, central, and curb-return pavement zone responsibilities from the edge network without triangulation. |
| 8 | Done | Slope face zones | Generates exterior Slope Face zone boundary contracts from daylight, pavement, and curb-return edge rows without triangulation. |
| 9 | Done | Ordinary corridor clipping | Adds ordinary corridor design/slope clipping contracts by control area before surface merge. |
| 10 | Done | Build Parametric review | Shows Topology, Edge Network, Surface Zone, and Corridor Clip rows with focus/highlight behavior. |
| 11 | Done | Cross Section Viewer | Shows active intersection leg, edge, zone, grading, drainage, and corridor-clip context. |
| 12 | Done | Drainage hints | Generates low-point and inlet recommendation rows from surface zones. |
| 13 | Done | Watertight target handoff | Discovers planned intersection pavement/subgrade/slope/curb-return targets from surface-zone contracts. |
| 14 | Ready | Manual QA | T, Cross, and Y starter intersection manual QA procedure is documented; real-document execution remains manual. |

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
4. Preview Edge Network.
5. Confirm main leg and side leg have separate centerlines.
6. Confirm curb-return edges connect to pavement edges.
7. Build Parametric.
8. Show only `Intersection Surface Zones`.
9. Confirm no ordinary Slope Face exists inside the control area.
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

Phase 5 completion note:

- The Intersections panel now exposes `Preview Edge Network`.
- The preview builds a temporary `IntersectionModel` from current panel selections and control Regions, evaluates topology, then evaluates the edge network.
- The preview creates or updates `V1IntersectionEdgeNetworkPreview` / `Intersection Edge Network Preview` in the 3D view.
- The preview object stores `EdgeNetworkStatus`, `EdgeCount`, `LegEdgeCount`, `DaylightEdgeCount`, `CurbReturnEdgeCount`, `EdgeIds`, and diagnostics as object properties.
- Current edge preview geometry is intentionally lightweight: leg edges are displayed from alignment station spans with role-based offsets, and curb-return edges use the current curb-return arc preview.
- No generated intersection surface behavior was changed in this phase.

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
- The Viewer now shows an `Intersection Context` table with family, status, ID, role, source refs, boundary refs, and notes.
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

This matches the direction used by mature road design tools: intersections are controlled by dedicated junction intent, road arms, edge geometry, targets, and structured zones before final surfaces are generated.
