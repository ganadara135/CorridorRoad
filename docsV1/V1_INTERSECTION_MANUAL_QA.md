# Parametric Road V1 Intersection Manual QA

Date: 2026-06-24
Status: manual QA procedure; preset records, Slope Face loop QA, dedicated Intersection Slope Face Surface QA, and source handoff/lineage QA added, execution pending real FreeCAD document

## Purpose

This checklist verifies the edge-network-first Intersection workflow from source creation through Build Parametric review, Cross Section Viewer context, drainage hints, and Watertight Solid target handoff.

## Scope

This QA covers:

- T, Cross, Skewed, Urban Curb/Gutter, Drainage-Sensitive Sag, Y, and Roundabout preset-driven intersection source creation
- `Intersection` workflow for T, Cross, Skewed, Urban Curb/Gutter, Drainage-Sensitive Sag, Y, and Roundabout starter contracts
- multi-alignment 3D Centerline handoff
- Applied Sections with active intersection context
- Build Parametric `Intersections` review rows
- surface-zone responsibility for pavement, curb-return, and Slope Face zones
- ordinary corridor clipping contracts
- drainage low-point, inlet recommendation, and outlet handoff hints
- Watertight Solid planned target discovery for intersection zone bodies

This QA does not certify final intersection Part solids.

The `intersection_pavement_body`, `intersection_subgrade_body`, `intersection_slope_body`, and `intersection_curb_return_body` targets are expected to be `planned` handoff rows until dedicated zone solid builders are implemented.

## Preconditions

- FreeCAD starts without command registration errors.
- Parametric Road workbench is active.
- A clean test document can run the v1 workflow.
- Build Parametric can generate ordinary design, subgrade, and Slope Face outputs.
- The document is not relying on manually deleted or hidden generated geometry to pass review.

Recommended baseline setup:

1. Create Project.
2. Create or import TIN if terrain context is needed.
3. Create main Alignment, Stations, Profile, and 3D Centerline.
4. Create Assembly and Regions.
5. Open Intersection.

## Common Acceptance Rules

The QA passes only when:

- source rows remain the durable design intent
- generated preview/output objects are disposable and reproducible
- intersection control areas are explicit
- ordinary corridor surfaces stop at or are clipped by the intersection control area
- intersection surface zones explain ownership before geometry is trusted
- no Slope Face is accepted inside the pavement/control-area interior
- ordinary `Slope Face Surface` and `Intersection Slope Face Surface` can be reviewed separately
- accepted intersection Slope Face triangles come only from `ready` Slope Face loop rows
- `Intersection Slope Face Surface` is enabled in Visibility only when `V1CorridorIntersectionSlopeFaceSurfacePreview` exists
- missing `Intersection Slope Face Surface` rows include a recommended action rather than a generic missing state
- diagnostics are `ready` or actionable `warning`
- no Report View traceback appears

## Intersection Smoke QA

Use this smoke test before detailed geometry review.

Run it once for each preset:

- `T Intersection - Basic`
- `Cross Intersection - Basic`
- `Skewed Intersection - Basic`
- `Urban Curb/Gutter - Basic`
- `Drainage-Sensitive Sag - Basic`
- `Y Intersection - Basic`
- `Roundabout - Single Lane`

Steps:

1. Open a clean FreeCAD document.
2. Open `Intersection`.
3. Select the preset.
4. Review Design Vehicle, Radius / Diameter, Control Length, Grading Policy, and Drainage Mode.
5. Click `Create Sources`.
6. Confirm the status message reports created Alignment, Profile, Stationing, Region, IntersectionModel, Superelevation, and Drainage source objects.
7. Confirm no final corridor mesh is created by the preset panel.
8. Open `Intersections`.
9. Confirm the created Intersection source model can be reviewed without traceback.
10. Confirm the staged source table exposes row-level `handoff_target` diagnostics for Anchor, Lane Connections, and Drainage where result rows exist.
11. Confirm the read-only preview stages expose `source_lineage_status` diagnostics for Drainage and Slope Loops where those result rows exist.
12. Run `Build Sections`.
13. Open Cross Section Viewer.
14. Confirm Station Navigation includes both primary and secondary Alignment station rows when the intersection has more than one participating Alignment.
17. Confirm Intersection Context rows are visible at primary and secondary control-area stations.
18. Confirm the Cross Section Viewer Intersection Context table includes a `source_status` row.
19. Run `Build Parametric`.
20. Open the `Intersections` tab in Build Parametric.
21. Confirm topology, edge-network, surface-zone, slope-face-loop, grading-context, corridor-clip, and drainage-hint rows are visible or represented in the notes/context rows.
22. Confirm `Source Status` and `Source Diagnostics` columns show accepted, warning, or missing source context explicitly.
23. Confirm Build Parametric row notes preserve source-lineage and consumed surface-zone warning context for `slope_face_loop` rows.
24. Confirm warnings are reviewable source/contract warnings, not Python exceptions.

Pass criteria:

- preset source objects are editable
- the single `Intersection` panel remains usable for preset and existing-Alignment source workflows
- staged source rows expose same-context handoff targets without applying output geometry
- read-only preview rows expose source-lineage status without applying output geometry
- Build Sections produces intersection supplemental station context
- Cross Section Viewer exposes station-level intersection source status
- Build Parametric does not silently hide missing policy, grading, or drainage handoff context
- generated output can be deleted and rebuilt from source rows

## T Preset Intersection Slope Face Source-Loop QA

Use this checklist after the T preset can build Applied Sections and Build Parametric output.

This verifies the source-loop completion path from Applied Section side-slope boundaries into the dedicated `Intersection Slope Face Surface`.

Steps:

1. Create `T Intersection - Basic`.
2. Review and accept preset prerequisites if needed for the test document.
3. Run `Build Sections`.
4. Run `Build Parametric`.
5. Open the Build Parametric `Intersections` tab.
6. Find the `boundary_loop` row before judging surface fill.
7. Confirm the `boundary_loop` row is `ready`, role is `outer_intersection_boundary`, and notes include `closed=yes`.
8. Double-click the `boundary_loop` row.
9. Confirm the 3D View shows one continuous cyan outer intersection perimeter.
10. Confirm the cyan perimeter encloses the intended intersection-owned area and does not come from generated mesh cleanup.
11. Find the `edge_network` rows and confirm any endpoint geometry warnings use `edge_network_endpoint_degenerate`.
12. Confirm those warnings include policy ref, leg ref, alignment ref, control-area ref, edge family, station span, and endpoint xyz.
13. Find the `slope_face_loop` rows.
14. Confirm at least one row is `ready`.
15. Confirm ready rows include `applied_section_boundary_completion=used`.
16. Confirm ready rows include `surface_generation=surface_candidate:ready`.
17. Confirm ready rows preserve `applied_section_side_slope_refs`.
18. Open the `Results` tab.
19. Confirm `Intersection Slope Face Surface` is `ready`.
20. Open the `Visibility` tab.
21. Hide ordinary `Slope Face Surface`.
22. Show only `Intersection Slope Face Surface`.
23. Confirm a dedicated surface exists around the intersection perimeter.
24. Confirm the dedicated surface does not enter the central pavement/intersection surface interior.
25. Show ordinary `Slope Face Surface` again.
26. Confirm ordinary and dedicated Slope Face surfaces remain separate review/output families.
27. Inspect both curb-return sides.
28. Record whether perimeter coverage is complete, partial, or missing.

Pass criteria:

- `V1CorridorIntersectionSlopeFaceSurfacePreview` exists.
- Intersections tab exposes a ready `boundary_loop` row with `outer_intersection_boundary`.
- double-clicking the boundary row highlights one continuous cyan perimeter.
- `Intersection Slope Face Surface` is generated without synthetic ready-loop injection.
- generated Slope Face triangles come from ready `slope_face_loop` rows.
- Applied Section side-slope boundary refs are visible in row notes.
- ordinary `Slope Face Surface` does not become the source truth for the dedicated intersection surface.

Known follow-up:

- explicit curb-return contact refs are not yet stored on the completed Applied Section boundary candidate rows.
- non-T presets need separate regression coverage after T preset visual QA is accepted.
- when multiple left/right side groups exist in one surface zone, the current first slice selects the strongest strip group; full multi-group loop splitting remains follow-up work.

## Preset QA Records

Record one row per preset when manual QA is executed in a real FreeCAD document.

| Preset | Intersection kind | Expected source status | Expected preview status | Expected Build Parametric status | Expected Watertight handoff status | Required record notes |
| --- | --- | --- | --- | --- | --- | --- |
| `T Intersection - Basic` | `t_intersection` | `warning`; preset default/draft Anchor, Control Areas, Corners, Edge Families, Lane Connections, Grading, and Drainage rows require review. | Intersections contract rows expose two curb-return edge groups without creating standalone edge-network geometry. | `Intersections` rows present for topology, edge network, surface zones, corridor clip, grading, drainage hints, and Slope Face loops. Warnings must be source-completeness or planned-handoff warnings. | `Intersection Patch` remains transitional/review-required; planned pavement, subgrade, Slope Face, and curb-return target rows should be discoverable when surface-zone contracts exist. | Record central pavement, curb-return, ordinary Slope Face suppression, and intersection Slope Face loop readiness. |
| `Cross Intersection - Basic` | `cross_intersection` | `warning`; four corner defaults and lane/edge/grading/drainage defaults remain draft. | Intersections contract rows expose four curb-return groups and primary/secondary through-road identity without preview geometry. | No topology `error` rows. Corridor clipping should cover both participating alignments. | Planned intersection zone targets should be discoverable; final zone bodies remain planned until dedicated builders are accepted. | Record whether curb-return zones overlap or self-cross. |
| `Skewed Intersection - Basic` | `skewed_intersection` | `warning`; skew corner and skew edge-family rows require source review. | Intersections contract rows preserve non-orthogonal Alignment lineage without global-axis rectangular repair. | Surface-zone and corridor-clip rows should remain source/result driven; skew warnings must be explicit. | Planned zone targets should remain reviewable; no final handoff should be accepted from mesh repair. | Record skew angle readability, corner policy diagnostics, and any asymmetric curb-return warnings. |
| `Urban Curb/Gutter - Basic` | `urban_curb_gutter_intersection` | `warning`; curb, gutter, sidewalk, inlet, and low-point rows are draft starter intent. | Intersections contract rows include pavement plus curb/gutter/sidewalk edge-family refs where available. | Drainage hints should expose gutter edge refs, inlet candidate refs, and low-point refs. | Watertight target discovery may show planned pavement/subgrade/Slope Face/curb-return rows; final inlet/outlet solids remain outside this preset. | Record gutter edge refs, inlet candidate count, and whether Drainage source rows are visible. |
| `Drainage-Sensitive Sag - Basic` | `drainage_sag_intersection` | `warning`; sag Profile controls, low-point refs, inlet candidates, flow-route refs, and hydraulic sizing remain review-required. | Intersections contract rows preserve sag main/side Alignment lineage; source-stage table should show warning/draft Grading and Drainage rows. | Grading context should report `sag_low_point_review`; Drainage hints should expose sag low points, inlet candidates, and critical flow-route review. | Planned zone targets remain discoverable; final simulation/export must stay blocked until hydraulic sizing and real inlet/outlet Structures replace hints. | Record Profile middle control as `sag_low_point`, inlet candidate refs, flow-route refs, and critical drainage warnings. |
| `Y Intersection - Basic` | `y_intersection` | `warning`; branch geometry and diverge/merge lane-connection defaults require review. | Intersections contract rows preserve primary approach, left branch, and right branch source Alignment lineage. | Surface-zone rows should remain non-self-crossing; branch warnings must stay source diagnostics. | Planned zone targets should remain reviewable; no final handoff should be accepted from branch mesh repair. | Record left/right branch roles and diverge/merge movement rows. |
| `Roundabout - Single Lane` | `roundabout` | `warning`; first-slice roundabout source contract, outside-gutter drainage hints, and radial grading require review. | Intersections contract rows expose `roundabout` family rows: central island, circulatory outer edge, and entry/exit edges. | Surface zones should include central island, circulatory pavement, and entry/exit pavement. `roundabout_edge_network_first_slice_source_only` is acceptable. | Planned handoff only. Final roundabout triangulation and accepted zone solids are not yet claimed complete. | Record roundabout edge-family rows, radial grading context, outside-gutter drainage hints, and missing explicit Drainage Element warnings. |

Manual execution status:

| Preset | Date | Result | Source status | Source handoff targets | Preview lineage | Build Parametric status | Watertight status | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `T Intersection - Basic` | pending | pending | pending | pending | pending | pending | pending |  |
| `Cross Intersection - Basic` | pending | pending | pending | pending | pending | pending | pending |  |
| `Skewed Intersection - Basic` | pending | pending | pending | pending | pending | pending | pending |  |
| `Urban Curb/Gutter - Basic` | pending | pending | pending | pending | pending | pending | pending |  |
| `Drainage-Sensitive Sag - Basic` | pending | pending | pending | pending | pending | pending | pending |  |
| `Y Intersection - Basic` | pending | pending | pending | pending | pending | pending | pending |  |
| `Roundabout - Single Lane` | pending | pending | pending | pending | pending | pending | pending |  |

## Source Handoff And Lineage Checks

Use these checks while the `Intersection` panel is still in read-only review mode.

| Stage | Expected handoff or lineage field | Passing condition | Failing condition |
| --- | --- | --- | --- |
| Anchor | `handoff_target:intersection-source-stage:anchor:<row>` | The stage diagnostics identify the specific Anchor source row needing review. | The panel reports only a generic warning with no row target. |
| Lane Connections | `handoff_target:intersection-source-stage:lane_connections:<row>` | Draft/default lane movement rows point back to the Lane Connections source stage. | Diverge/merge or turn movement warnings have no same-context return target. |
| Drainage source stage | `handoff_target:intersection-source-stage:drainage:<policy>` | Low-point, inlet, or outlet hint rows point back to the owning Drainage policy/source stage. | Drainage warnings require editing but do not identify the source stage. |
| Drainage preview | `source_lineage_status:<status>` | `hint_only`, `source_warning`, or `accepted` lineage is visible in preview diagnostics. | Drainage hints appear as geometry or generic warnings without lineage status. |
| Grading preview | `handoff_target:intersection-preview-stage:grading:<zone>` | Grading context rows point to the review stage for the affected surface zone. | Grading warnings cannot be traced to a zone or review stage. |
| Slope Loops preview | `source_lineage_status:<status>` | Slope loop rows show accepted or warning lineage before any triangle output is trusted. | Warning/error loops can be mistaken for accepted triangulation input. |

## Skewed Practical Exclusion Footprint QA

Use this checklist for `Skewed Intersection - Basic` and any manually authored skewed T-intersection.

Purpose:

- verify curb-return surface generation separately from adjacent-surface clipping
- confirm Design/Slope clipping uses a practical exclusion footprint when it is ready
- confirm missing or degraded footprints are visible before the user trusts adjacent surface clipping

Steps:

1. Create or load a skewed T-intersection source model.
2. Run `Build Sections`.
3. Run `Build Parametric`.
4. Open Build Parametric `Guided Review`.
5. Find the `Intersections` step notes.
6. Confirm curb-return triangulation reports `structured_strip_curb_return_blend` or equivalent ready surface context.
7. Confirm Design/Slope exclusion notes include boundary strategy and practical footprint status.
8. If the footprint is ready, confirm notes do not ask for corrective action.
9. If the footprint is recovered or degraded, confirm the notes include a diagnostic such as `intersection_exclusion_footprint_outer_loop_recovered:exterior_hull`.
10. If the footprint is missing, confirm adjacent clipping uses conservative skip and no valid adjacent triangles disappear.
11. Toggle the Design, Slope Face, Breaklines, and Diagnostics visibility groups.
12. Visually confirm the recovered footprint covers the skewed pavement/curb-return footprint and does not swallow unrelated corridor surface.
13. Check Shared Breakline Audit.
14. Confirm no geometry mismatch or missing-consumer warning is introduced by the skewed footprint recovery.

Pass criteria:

- curb-return surface remains generated from source/result contracts
- practical footprint status is visible as `ready`, `degraded`, or `missing`
- `missing` or `degraded` status includes a recommended action
- ready/recovered footprint clips only triangles inside the skewed intersection footprint
- missing footprint preserves adjacent surface triangles and reports conservative skip
- no Report View traceback appears

Fail conditions:

- ordinary Design or Slope Face triangles disappear when practical footprint status is `missing`
- Review notes mention clipping but do not expose footprint status
- recommended action is missing for `missing` or `degraded` footprint status
- the user must inspect raw tree objects to understand the skewed footprint state

## Intersection Existing Alignment QA

Use this test when the participating Alignments already exist.

1. Create or import a primary Alignment.
2. Create or import a secondary Alignment.
3. Create matching Profile, Stationing, Region, and 3D Centerline sources as needed.
4. Confirm Region source rows are tagged with the target intersection ref.
5. Open `Intersection`.
6. Set `Source Mode` to `Use Existing Alignments`.
7. Select the preset family that matches the intended junction type.
8. Select Primary Alignment.
9. Select Secondary Alignment.
10. Click `Auto Detect`.
11. Confirm detected XY, Primary STA, and Secondary STA are reported.
12. Click `Apply`.
13. Confirm the created `IntersectionModel` stores `source_mode = use_existing_alignments`.
14. Run `Build Sections`.
15. Run `Build Parametric`.
16. Confirm Build Parametric `Intersections` rows preserve selected Alignment refs in edge-network and surface-zone diagnostics.

Pass criteria:

- no starter Alignment is created in this mode
- selected Primary and Secondary Alignment refs are stored in the `IntersectionModel`
- control Regions remain source-owned Region rows
- the existing `Intersections` panel can still open and review the resulting model

Fail conditions:

- Primary and Secondary Alignment are the same ref
- no intersection-tagged control Regions are found
- Auto Detect silently fails without a status message
- Apply creates starter source objects when `Use Existing Alignments` is selected

## T-Intersection QA

1. Open `Intersections`.
2. Select `T Intersection`.
3. Use `Create Starter Sources`.
4. Click `Create Starter Sources`.
5. Confirm main and side Alignment source objects exist.
6. Confirm a multi-alignment 3D Centerline is created or refreshed.
7. Click `Apply`.
8. Build Sections.
9. Open Cross Section Viewer for a main-road station inside the control area.
10. Confirm `Intersection Context` shows active intersection, control area, leg, edge-network, surface-zone, corridor-clip, grading, drainage, and drainage-hint rows.
11. Open Build Parametric.
12. Build outputs.
13. Confirm Build Parametric `Intersections` rows show separate main/side leg edge contracts and two curb-return edge groups.
16. Open the `Intersections` tab.
17. Confirm `topology`, `edge_network`, `surface_zone`, `corridor_clip`, and `drainage_hint` rows are present.
18. Double-click representative edge-network and surface-zone rows.
19. Confirm focus/highlight targets the relevant review object.
20. Show only intersection-related surface outputs.
21. Confirm the central pavement and curb-return zones form a readable T-junction area.
22. Show ordinary Slope Face outputs.
23. Confirm ordinary Slope Face does not fill the control-area pavement interior.
24. Confirm side-road Slope Face responsibility reaches the curb-return boundary through explicit surface-zone rows.
25. In the `Intersections` tab, find the `slope_face_loop` rows.
26. Confirm each `slope_face_loop` row shows `generation=<role>:<status>` in Notes.
27. Confirm at least one accepted output loop has:
    - `Status = ready`
    - `closed_xy=yes`
    - `generation=surface_candidate:ready`
    - no `slope_face_loop_open_xy`, `slope_face_loop_dangling_endpoint`, or `slope_face_loop_self_crossing` diagnostic
28. If no loop is ready, confirm the Results row for `Intersection Slope Face Surface` is `missing` and Notes include `Recommended Action`.
29. Open the `Results` tab.
30. Confirm `Intersection Slope Face Surface` is `ready` only when `V1CorridorIntersectionSlopeFaceSurfacePreview` exists.
31. Confirm the row reports nonzero triangle count and consumed loop contract notes when ready.
32. Open the `Visibility` tab.
33. Confirm the `Intersection Slope Face Surface` checkbox is enabled only when `V1CorridorIntersectionSlopeFaceSurfacePreview` exists.
34. If the checkbox is disabled, hover it and confirm the tooltip explains the missing preview status and recommended action.
35. Show only `Intersection Slope Face Surface`.
36. Confirm it is generated only from ready Slope Face loop rows.
37. Confirm the object is located under `04_Parametric Model > Intersections` and not under ordinary Alignment review groups.
38. Show only ordinary `Slope Face Surface`.
39. Confirm ordinary Slope Face review notes or object properties report loop suppression status, ready loop count, tested triangle count, suppressed triangle count, and kept triangle count.
40. Toggle ordinary `Slope Face Surface` off and `Intersection Slope Face Surface` on.
41. Around both curb returns, confirm the dedicated surface touches the curb-return/side-slope tie-in area without crossing into central pavement.
42. Confirm no dedicated Slope Face triangles appear inside the `Intersection Surface` pavement footprint.
43. Confirm no forced rectangular boundary patch or old `Intersection Slope Face Boundary` white/outline patch is visible.
44. Double-click representative `slope_face_loop` rows in the `Intersections` tab.
45. Confirm ready closed loops highlight green, open loops highlight orange, dangling endpoints highlight red, self-crossing loops highlight magenta, and source-warning closed loops highlight yellow.
46. Confirm the selected loop itself is highlighted as one closed or ordered boundary line in 3D and no arbitrary mesh repair marker is created.
47. Confirm warning or error loop rows remain diagnostics and do not create intersection Slope Face triangles.

`Intersection Slope Face Loops` linework is no longer created by default.

Slope Face Loop contract metadata remains on the main Intersection preview and related review rows.
48. Confirm `slope_face_loop` row notes include source-lineage context before trusting any loop output.
49. Open Watertight Solids.
50. Confirm `Intersection Patch` target remains discoverable.
51. Confirm planned intersection zone targets appear for pavement, subgrade, Slope Face, and curb-return bodies.

Dedicated Slope Face record:

| Item | Expected | Actual |
| --- | --- | --- |
| `IntersectionSlopeFaceLoopReadyCount` | at least `1` for accepted output | pending |
| `V1CorridorIntersectionSlopeFaceSurfacePreview` | exists when ready loops exist | pending |
| Results status | `ready` when preview exists, `missing` with action when absent | pending |
| Visibility checkbox | enabled only when preview exists | pending |
| Curb-return tie-in | touches side-slope area without pavement intrusion | pending |
| Ordinary Slope Face overlap | no visible overlap inside Intersection Surface footprint | pending |

## Cross Intersection QA

1. Open `Intersections`.
2. Select `Cross Intersection`.
3. Use `Create Starter Sources`.
4. Confirm primary and secondary through-leg source identity is clear.
5. Confirm four leg/control-area responsibilities are visible in source or review rows.
6. Build Sections.
7. Build Parametric.
8. Confirm the `Intersections` tab has no topology `error` rows.
9. Confirm four curb-return edge groups are present as result contracts.
10. Confirm central pavement zone responsibility is not duplicated by ordinary corridor surface ownership.
11. Confirm curb-return zones do not overlap each other in a self-crossing way.
12. Confirm Slope Face loop rows exist for the participating legs or report actionable warnings.
13. Confirm ready Slope Face loops can be focused in 3D.
14. Confirm ordinary `Slope Face Surface` and `Intersection Slope Face Surface` are separate review/output families.
15. Confirm corridor-clip rows exist for both participating alignments.
16. Confirm drainage-hint rows identify low-point and inlet review candidates.
17. Confirm drainage-hint rows expose same-context Drainage source handoff targets.
18. Open Watertight Solids and confirm planned intersection zone target rows are discoverable.

## Skewed Intersection QA

1. Open `Intersection`.
2. Select `Skewed Intersection - Basic`.
3. Confirm Radius is `11 m` and Control Length is `30 m`.
4. Click `Create Sources`.
5. Confirm `Skew Main Road` and `Skew Crossing Road` Alignment, Profile, Stationing, and Region sources are created.
6. Confirm the secondary Alignment is visibly non-orthogonal to the primary Alignment.
7. Confirm the stored `IntersectionModel` uses `intersection_kind = skewed_intersection`.
8. Confirm source refs include `intersection-preset:skewed_intersection:source-completeness` and `intersection-preset:skewed_intersection:skew-review`.
9. Confirm four corner rows exist and include `preset_skew_corner_geometry_review_required`.
10. Confirm edge-family rows include `preset_skew_edge_family_review_required`.
11. Build Sections.
12. Build Parametric.
13. Confirm topology and edge-network rows carry warning diagnostics rather than silent fallback geometry.
14. Confirm edge-network rows preserve skewed Alignment lineage and do not snap to an orthogonal/global-axis rectangle.
15. Confirm surface-zone rows are source/result rows and do not claim repaired mesh ownership.
16. Confirm corridor-clip rows are present for both participating Alignments.
17. Open Cross Section Viewer.
19. Confirm Intersection Context rows identify the correct active leg and control area near the skewed crossing.
20. Confirm Slope Loop preview/review rows expose source-lineage diagnostics for skew-controlled edge families.
21. Open Watertight Solids.
22. Confirm planned intersection zone targets remain discoverable and no final accepted solid is created from skew mesh repair.

Expected result:

- source status: `warning`
- preview status: `warning` or `accepted` with visible skew diagnostics
- Build Parametric status: reviewable warnings, no topology errors
- Watertight status: planned/review-required only

## Urban Curb/Gutter QA

1. Open `Intersection`.
2. Select `Urban Curb/Gutter - Basic`.
3. Confirm Drainage Mode is `curb_gutter_inlets`.
4. Click `Create Sources`.
5. Confirm `Urban Main Street` and `Urban Side Street` Alignment, Profile, Stationing, and Region sources are created.
6. Confirm the stored `IntersectionModel` uses `intersection_kind = urban_curb_gutter_intersection`.
7. Confirm source refs include `intersection-preset:urban_curb_gutter_intersection:urban-curb-gutter-review`.
8. Confirm edge-family rows include `curb_edge`, `gutter_edge`, and `sidewalk_edge`.
9. Confirm curb/gutter/sidewalk edge rows are draft source rows, not generated output geometry.
10. Confirm diagnostics include:
    - `preset_urban_curb_review_required`
    - `preset_urban_gutter_review_required`
    - `preset_urban_sidewalk_review_required`
11. Confirm drainage policy has `capture_mode = curb_gutter_inlets`.
12. Confirm drainage policy has gutter edge refs, inlet candidate refs, and low-point refs.
13. Confirm preset Drainage source object includes inlet candidate rows.
14. Build Sections.
15. Build Parametric.
16. Confirm pavement, curb, gutter, and sidewalk edge-family intent is visible or reported in `Intersections` contract rows.
17. Confirm drainage-hint rows expose inlet candidate and low-point handoff context.
18. Confirm drainage-hint diagnostics include Drainage source-stage handoff targets and source-lineage status.
19. Confirm Build Parametric warnings are review-required inlet/low-point handoff warnings, not exceptions.
20. Open Cross Section Viewer.
21. Confirm Intersection Context shows drainage source status at urban control-area stations.
22. Open Watertight Solids.
23. Confirm final inlet/outlet solids are not claimed complete by this preset.

Expected result:

- source status: `warning`
- preview status: edge-family preview/review rows visible
- Build Parametric status: drainage and edge-family warnings remain actionable
- Watertight status: planned intersection zone targets only; inlet/outlet Structures remain future source work

## Drainage-Sensitive Sag QA

1. Open `Intersection`.
2. Select `Drainage-Sensitive Sag - Basic`.
3. Confirm Drainage Mode is `sag_low_point_inlets`.
4. Click `Create Sources`.
5. Confirm `Sag Main Road` and `Sag Side Road` Alignment, Profile, Stationing, and Region sources are created.
6. Open or inspect the created Profile sources.
7. Confirm the middle Profile control kind is `sag_low_point`.
8. Confirm the middle Profile elevation is lower than the start and end controls.
9. Confirm the stored `IntersectionModel` uses `intersection_kind = drainage_sag_intersection`.
10. Confirm source refs include `intersection-preset:drainage_sag_intersection:sag-drainage-review`.
11. Confirm grading policy has `low_point_strategy = sag_low_point_review`.
12. Confirm grading diagnostics include:
    - `preset_sag_profile_review_required`
    - `preset_sag_low_point_review_required`
13. Confirm drainage policy has `capture_mode = sag_low_point_inlets`.
14. Confirm drainage policy has low-point refs, inlet candidate refs, and flow-route refs.
15. Confirm drainage diagnostics include:
    - `preset_sag_inlet_review_required`
    - `preset_sag_flow_route_review_required`
    - `preset_sag_hydraulic_sizing_required`
16. Confirm preset Drainage source object includes sag low-point and inlet candidate rows.
17. Confirm the Drainage flow route risk is `critical`.
18. Build Sections.
19. Build Parametric.
20. Confirm edge-network contract rows preserve sag main and side Alignment lineage.
21. Confirm grading-context rows report sag low-point review intent.
22. Confirm drainage-hint rows expose inlet and flow-route handoff context.
23. Confirm drainage-hint diagnostics include Drainage source-stage handoff targets and `source_lineage_status:hint_only` until real Drainage source is accepted.
24. Open Cross Section Viewer.
25. Confirm Intersection Context reports warning source status for Grading and Drainage.
26. Open Watertight Solids.
27. Confirm final simulation/export package is not considered accepted until hydraulic sizing and real inlet/outlet Structures replace hints.

Expected result:

- source status: `warning`
- preview status: source/result preview visible with sag diagnostics
- Build Parametric status: sag grading and drainage handoff warnings visible
- Watertight status: final handoff blocked or review-required until drainage source is accepted

## Roundabout Preset QA

Roundabout is currently a preset-driven first-slice source contract.

It is not yet promoted beyond the first-slice `Intersection` source workflow.

1. Open `Intersection`.
2. Select `Roundabout - Single Lane`.
3. Confirm default Grading Policy is `roundabout_radial_crossfall`.
4. Confirm default Drainage Mode is `outside_gutter`.
5. Click `Create Sources`.
6. Confirm crossing approach Alignment, Profile, Stationing, and Region sources are created.
7. Confirm an `IntersectionModel` source object is created.
8. Confirm preset-owned Superelevation and Drainage handoff source objects are created.
9. Build Sections.
10. Build Parametric.
11. Confirm edge-network rows include the `roundabout` family.
12. Confirm roundabout edge roles include:
    - `central_island_edge`
    - `circulatory_outer_edge`
    - `entry_exit_edge`
13. Confirm surface-zone rows include:
    - `roundabout_central_island`
    - `roundabout_circulatory_pavement`
    - `roundabout_entry_exit_pavement`
14. Confirm grading context rows use `roundabout_radial_crossfall`.
15. Confirm drainage hints report `outside_gutter` mode.
16. Confirm outlet handoff hints are warning rows that require explicit Drainage Elements.
17. Confirm outlet hint diagnostics expose Drainage source-stage handoff targets and hint-only lineage.
18. Confirm no final roundabout triangulation is claimed as complete.

Known acceptable warnings:

- `roundabout_edge_network_first_slice_source_only`
- missing explicit Drainage Element coverage for low-point, inlet, or outlet handoff

Fail conditions:

- no `roundabout` edge-family rows
- no roundabout surface-zone rows
- grading context falls back silently to ordinary road crossfall
- outlet handoff is absent for `outside_gutter` mode

## Y Intersection QA

1. Open `Intersections`.
2. Select `Y Intersection`.
3. Use `Create Starter Sources`.
4. Confirm the skewed/diverging Alignment sources are created.
5. Confirm generated source geometry does not fall back to global-axis rectangular assumptions.
6. Build Sections.
7. Build Parametric.
8. Confirm edge-network contract rows follow the participating Alignment directions.
9. Confirm curb-return policy is applied per leg pair.
10. Confirm surface-zone rows remain non-self-crossing.
11. Confirm Slope Face zone rows have explicit daylight, pavement, and curb-return boundary refs.
12. Confirm Slope Face loop rows do not silently fall back to global-axis rectangular assumptions.
13. Confirm ready Slope Face loops can generate separate `Intersection Slope Face Surface` output.
14. Confirm warning/error Slope Face loops remain diagnostics only.
15. Confirm Slope Loop preview/review rows expose source-lineage status before any loop is accepted for triangulation.
17. Confirm Cross Section Viewer reports the correct active leg and control area at a focused station.
18. Confirm Watertight Solids reports planned intersection zone targets.

## Lane / Shoulder / Side Slope Stitching Regression QA

Purpose:

- prevent a repeat of the original Intersection preset failure where Lane, Shoulder, and Side Slope review geometry stitched across unrelated Alignment scopes.
- confirm Build Parametric review geometry is grouped by source Alignment and control Region, not by global subassembly kind alone.
- keep ordinary `Slope Face Surface` and `Intersection Slope Face Surface` review/output families separate.

Run this regression for at least:

- `T Intersection - Basic`
- `Cross Intersection - Basic`
- one non-orthogonal starter such as `Y Intersection - Basic` or `Skewed Intersection - Basic`

Setup:

1. Open a clean document.
2. Open `Intersection`.
3. Create the selected starter sources.
4. Confirm the created source rows expose participating Alignment refs, control Region refs, and source-completeness diagnostics.
5. Build Sections.
6. Build Parametric.
7. Open Build Parametric review rows and focus the generated review/highlight geometry.
8. Confirm the `Intersections` review rows expose `Source Status`, `Source Diagnostics`, and row notes for the affected Lane, Shoulder, Side Slope, and `slope_face_loop` contexts.
9. Confirm output preview objects that consume intersection contracts expose `ConsumedIntersectionContractSummary`.

Lane checks:

1. Filter or focus Lane review rows.
2. Confirm each Lane preview/highlight belongs to one source Alignment and one compatible control Region span.
3. Confirm no Lane polyline or strip jumps from a primary road to a side road unless it is represented by an explicit Intersection lane-connection or surface-zone contract.
4. Confirm any Lane row that reaches the junction has an explicit lane-connection, edge-family, or surface-zone source/result reference.
5. Record the source Alignment ref, Region/control Region ref, source status, source diagnostics, and row id for any Lane row that reaches the junction.

Shoulder checks:

1. Filter or focus Shoulder review rows.
2. Confirm Shoulder geometry stops, trims, or transitions at the intersection control boundary using explicit source/result rows.
3. Confirm no Shoulder row bridges across another leg just because both legs use the same subassembly kind.
4. Confirm Shoulder review notes identify whether the row is ordinary corridor responsibility or intersection-zone responsibility.
5. Record whether each Shoulder row is ordinary corridor responsibility or intersection-zone responsibility, including any source diagnostics.

Side Slope checks:

1. Filter or focus Side Slope review rows.
2. Confirm Side Slope geometry follows its owning Alignment and does not form diagonal ribbons across unrelated legs.
3. Confirm ordinary Side Slope/Slope Face output is suppressed or clipped inside accepted intersection control areas.
4. Confirm accepted intersection Slope Face geometry comes only from ready `slope_face_loop` rows.
5. Confirm `slope_face_loop` review rows with warnings include `source_lineage=...` and, when applicable, `surface_zone_status=...` in row notes.

Output-family separation checks:

1. Show only ordinary `Slope Face Surface`.
2. Confirm it does not fill pavement/control-area interiors.
3. Hide ordinary `Slope Face Surface`.
4. Show only `Intersection Slope Face Surface`.
5. Confirm it contains only accepted intersection loop triangles.
6. Confirm warning or error Slope Face loops remain diagnostics and do not generate triangles.
7. Confirm `Intersection Slope Face Surface` preview/output properties report consumed Intersection contract summaries, especially `slope_face_loop=...`.
8. Confirm ordinary `Slope Face Surface` review properties report tested, suppressed, and kept triangle counts where available.

Build Parametric lineage checks:

1. In the `Intersections` tab, filter or inspect `slope_face_loop` rows.
2. Confirm each row has a `Source Status` value of `accepted`, `warning`, or `missing`.
3. For warning rows, confirm notes include `source_lineage=source_warning` or another explicit lineage state.
4. For rows driven by warning surface-zone context, confirm notes include `surface_zone_status=warning`.
5. Confirm the row diagnostics identify missing source refs, open loops, low point review, edge-family warning, or surface-zone warning instead of reporting generic mesh repair.
6. Double-click representative rows and confirm focus/highlight uses the review object or boundary loop, not a generated mesh patch as source truth.

Record:

| Date | Preset | Alignment scopes checked | Lane lineage result | Shoulder lineage result | Side Slope lineage result | Ordinary Slope Face counts | Intersection Slope Face lineage | Build Parametric notes checked | Diagnostics | Result |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| pending | `T Intersection - Basic` | pending | pending | pending | pending | pending | pending | pending | pending |  |
| pending | `Cross Intersection - Basic` | pending | pending | pending | pending | pending | pending | pending | pending |  |
| pending | `Y Intersection - Basic` or `Skewed Intersection - Basic` | pending | pending | pending | pending | pending | pending | pending | pending |  |

Fail conditions:

- one Lane, Shoulder, or Side Slope review row connects unrelated Alignment refs without an explicit Intersection source/result contract.
- review geometry is grouped only by subassembly kind and ignores source Alignment or control Region ownership.
- Build Parametric row notes omit source lineage for warning `slope_face_loop` rows.
- Build Parametric hides warning surface-zone status from Slope Face loop review.
- ordinary Slope Face fills the intersection pavement/control-area interior.
- warning or error intersection Slope Face loop rows generate accepted surface triangles.
- missing source refs are hidden by generated mesh repair instead of reported as diagnostics.

## Diagnostic Review

For each starter type, record:

- intersection kind
- number of participating alignments
- number of control areas
- edge-network row count
- surface-zone row count
- Slope Face loop row count
- Slope Face ready loop count
- Slope Face warning loop count
- Slope Face error loop count
- ordinary Slope Face tested/suppressed/kept triangle counts
- intersection Slope Face triangle count
- corridor-clip row count
- drainage-hint row count
- grading-context row count
- outlet handoff count
- missing drainage coverage count
- Watertight intersection target counts
- any `error` diagnostics
- any actionable `warning` diagnostics

Warnings are acceptable only when they tell the user which source relation is missing or which downstream builder is still planned.

Errors are acceptable only for deliberately incomplete test inputs.

## Failure Notes

If edge rows are missing:

1. Check leg rows.
2. Check arm policy refs.
3. Check pavement and daylight edge policy refs.
4. Check source-completeness diagnostics for missing Profile, 3D Centerline, Region, control Region, and policy refs.

If surface zones are missing:

1. Check edge-network status.
2. Check curb-return policy refs.
3. Check control-area refs.
4. Check whether topology reported source-completeness warnings that must be resolved before trusting surface-zone output.

If ordinary Slope Face crosses the junction:

1. Check corridor-clip rows.
2. Check control-area station ranges.
3. Check control Region refs.
4. Check `slope_face_loop` rows.
5. Check ordinary Slope Face loop suppression properties.

If Intersection Slope Face is missing:

1. Check `slope_face_loop` rows in the Build Parametric `Intersections` tab.
2. Confirm at least one loop status is `ready`.
3. Confirm at least one ready loop also reports `generation=surface_candidate:ready`.
4. Double-click the loop row and confirm the loop boundary is closed in 3D.
5. Check unresolved, duplicate, dangling endpoint, open-loop, self-crossing, low-quality fan, or missing-source diagnostics.
6. Open the `Results` tab and confirm the `Intersection Slope Face Surface` row notes include `Recommended Action`.
7. Open the `Visibility` tab and confirm the disabled checkbox tooltip explains why `V1CorridorIntersectionSlopeFaceSurfacePreview` is absent.
8. Confirm the preview object is absent from `04_Parametric Model > Intersections` only when ready-loop generation is blocked.

If Intersection Slope Face appears broken:

1. Hide ordinary `Slope Face Surface`.
2. Show only `Intersection Slope Face Surface`.
3. Confirm warning/error loops did not generate mesh triangles.
4. Confirm the object has nonzero `TriangleCount`, `SurfaceGenerationReadyLoopCount`, and `SourceLoopRefs`.
5. Confirm the surface touches curb-return/side-slope tie-in boundaries without entering central pavement.
6. Confirm the problem is not caused by a hidden ordinary Slope Face object.
7. Record the loop id, loop family, source edge refs, source Applied Section refs, triangle count, and diagnostics.

If Watertight intersection zone targets are missing:

1. Check `IntersectionSurfaceZoneResult`.
2. Confirm the intersection has accepted surface-zone rows.
3. Refresh Watertight Solids target discovery.

## Result Record

Manual QA result should be recorded as:

```text
Date:
FreeCAD version: 1.1.1
Parametric Road version/branch:
Document:
Intersection kind:
Result: pass / warning / fail
Blocking diagnostics:
Notes:
```

## Follow-Up

Future QA should add:

- direct comparison against Civil 3D or OpenRoads sample intersections
- visual screenshots for accepted T, Cross, Y, and Roundabout baseline cases
- watertight solid build checks after intersection zone solid builders are implemented
- drainage flow route checks that consume intersection inlet recommendations
