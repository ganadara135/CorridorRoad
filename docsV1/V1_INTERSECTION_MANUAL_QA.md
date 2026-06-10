# Parametric Road V1 Intersection Manual QA

Date: 2026-06-10
Status: manual QA procedure; preset and Slope Face loop QA added, execution pending real FreeCAD document

## Purpose

This checklist verifies the edge-network-first Intersection workflow from source creation through Build Parametric review, Cross Section Viewer context, drainage hints, and Watertight Solid target handoff.

## Scope

This QA covers:

- T, Cross, Y, and preset-driven intersection source creation
- separate `Intersection Presets` workflow for T, Cross, and Roundabout starter contracts
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
5. Open Intersections.

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
- diagnostics are `ready` or actionable `warning`
- no Report View traceback appears

## Intersection Presets Smoke QA

Use this smoke test before detailed geometry review.

Run it once for each preset:

- `T Intersection - Basic`
- `Cross Intersection - Basic`
- `Roundabout - Single Lane`

Steps:

1. Open a clean FreeCAD document.
2. Open `Intersection Presets`.
3. Select the preset.
4. Review Design Vehicle, Radius / Diameter, Control Length, Grading Policy, and Drainage Mode.
5. Click `Create Sources`.
6. Confirm the status message reports created Alignment, Profile, Stationing, Region, IntersectionModel, Superelevation, and Drainage source objects.
7. Click `Preview Edge Network`.
8. Confirm the preview follows the generated preset Alignments and control Regions.
9. Confirm no final corridor mesh is created by the preset panel.
10. Open `Intersections`.
11. Confirm the created Intersection source model can be reviewed without traceback.
12. Run `Build Sections`.
13. Open Cross Section Viewer.
14. Confirm Station Navigation includes both primary and secondary Alignment station rows when the intersection has more than one participating Alignment.
15. Confirm Intersection Context rows are visible at primary and secondary control-area stations.
16. Run `Build Parametric`.
17. Open the `Intersections` tab in Build Parametric.
18. Confirm topology, edge-network, surface-zone, slope-face-loop, grading-context, corridor-clip, and drainage-hint rows are visible or represented in the notes/context rows.
19. Confirm warnings are reviewable source/contract warnings, not Python exceptions.

Pass criteria:

- preset source objects are editable
- existing `Intersections` panel remains usable
- Build Sections produces intersection supplemental station context
- Build Parametric does not silently hide missing policy, grading, or drainage handoff context
- generated output can be deleted and rebuilt from source rows

## Intersection Presets Existing Alignment QA

Use this test when the participating Alignments already exist.

1. Create or import a primary Alignment.
2. Create or import a secondary Alignment.
3. Create matching Profile, Stationing, Region, and 3D Centerline sources as needed.
4. Confirm Region source rows are tagged with the target intersection ref.
5. Open `Intersection Presets`.
6. Set `Source Mode` to `Use Existing Alignments`.
7. Select the preset family that matches the intended junction type.
8. Select Primary Alignment.
9. Select Secondary Alignment.
10. Click `Auto Detect`.
11. Confirm detected XY, Primary STA, and Secondary STA are reported.
12. Click `Preview Edge Network`.
13. Confirm the preview follows the selected Alignments.
14. Click `Apply`.
15. Confirm the created `IntersectionModel` stores `source_mode = use_existing_alignments`.
16. Run `Build Sections`.
17. Run `Build Parametric`.

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
7. Click `Preview Edge Network`.
8. Confirm the preview shows separate main and side leg edges.
9. Confirm two curb-return edge groups are visible.
10. Click `Apply`.
11. Build Sections.
12. Open Cross Section Viewer for a main-road station inside the control area.
13. Confirm `Intersection Context` shows active intersection, control area, leg, edge-network, surface-zone, corridor-clip, grading, drainage, and drainage-hint rows.
14. Open Build Parametric.
15. Build outputs.
16. Open the `Intersections` tab.
17. Confirm `topology`, `edge_network`, `surface_zone`, `corridor_clip`, and `drainage_hint` rows are present.
18. Double-click representative edge-network and surface-zone rows.
19. Confirm focus/highlight targets the relevant review object.
20. Show only intersection-related surface outputs.
21. Confirm the central pavement and curb-return zones form a readable T-junction area.
22. Show ordinary Slope Face outputs.
23. Confirm ordinary Slope Face does not fill the control-area pavement interior.
24. Confirm side-road Slope Face responsibility reaches the curb-return boundary through explicit surface-zone rows.
25. Show only `Intersection Slope Face Surface`.
26. Confirm it is generated only from ready Slope Face loop rows.
27. Show only ordinary `Slope Face Surface`.
28. Confirm its review notes or object properties report loop suppression status, ready loop count, tested triangle count, suppressed triangle count, and kept triangle count.
29. Double-click representative `slope_face_loop` rows in the `Intersections` tab.
30. Confirm the selected loop itself is highlighted as one thick yellow closed or ordered boundary line in 3D and no arbitrary mesh repair marker is created.
31. Confirm warning or error loop rows remain diagnostics and do not create intersection Slope Face triangles.
32. Confirm `Intersection Slope Face Loops` and `Intersection Slope Face Surface` preview/output objects are under `04_Parametric Model > Intersections`.
33. Open Watertight Solids.
34. Confirm `Intersection Patch` target remains discoverable.
35. Confirm planned intersection zone targets appear for pavement, subgrade, Slope Face, and curb-return bodies.

## Cross Intersection QA

1. Open `Intersections`.
2. Select `Cross Intersection`.
3. Use `Create Starter Sources`.
4. Confirm primary and secondary through-leg source identity is clear.
5. Confirm four leg/control-area responsibilities are visible in source or review rows.
6. Preview Edge Network.
7. Confirm four curb-return edge groups are created.
8. Build Sections.
9. Build Parametric.
10. Confirm the `Intersections` tab has no topology `error` rows.
11. Confirm central pavement zone responsibility is not duplicated by ordinary corridor surface ownership.
12. Confirm curb-return zones do not overlap each other in a self-crossing way.
13. Confirm Slope Face loop rows exist for the participating legs or report actionable warnings.
14. Confirm ready Slope Face loops can be focused in 3D.
15. Confirm ordinary `Slope Face Surface` and `Intersection Slope Face Surface` are separate review/output families.
16. Confirm corridor-clip rows exist for both participating alignments.
17. Confirm drainage-hint rows identify low-point and inlet review candidates.
18. Open Watertight Solids and confirm planned intersection zone target rows are discoverable.

## Roundabout Preset QA

Roundabout is currently a preset-driven first-slice source contract.

It is not yet promoted into the existing `Intersections` editor's final intersection type workflow.

1. Open `Intersection Presets`.
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
17. Confirm no final roundabout triangulation is claimed as complete.

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
5. Confirm generated preview geometry does not fall back to global-axis rectangular assumptions.
6. Preview Edge Network.
7. Confirm leg edges follow the participating Alignment directions.
8. Confirm curb-return policy is applied per leg pair.
9. Build Sections.
10. Build Parametric.
11. Confirm surface-zone rows remain non-self-crossing.
12. Confirm Slope Face zone rows have explicit daylight, pavement, and curb-return boundary refs.
13. Confirm Slope Face loop rows do not silently fall back to global-axis rectangular assumptions.
14. Confirm ready Slope Face loops can generate separate `Intersection Slope Face Surface` output.
15. Confirm warning/error Slope Face loops remain diagnostics only.
16. Confirm Cross Section Viewer reports the correct active leg and control area at a focused station.
17. Confirm Watertight Solids reports planned intersection zone targets.

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

If surface zones are missing:

1. Check edge-network status.
2. Check curb-return policy refs.
3. Check control-area refs.

If ordinary Slope Face crosses the junction:

1. Check corridor-clip rows.
2. Check control-area station ranges.
3. Check control Region refs.
4. Check `slope_face_loop` rows.
5. Check ordinary Slope Face loop suppression properties.

If Intersection Slope Face is missing:

1. Check `slope_face_loop` rows in the Build Parametric `Intersections` tab.
2. Confirm at least one loop status is `ready`.
3. Double-click the loop row and confirm the loop boundary is closed in 3D.
4. Check unresolved, duplicate, open-loop, self-crossing, or missing-source diagnostics.
5. Confirm the preview objects are under `04_Parametric Model > Intersections`.

If Intersection Slope Face appears broken:

1. Hide ordinary `Slope Face Surface`.
2. Show only `Intersection Slope Face Surface`.
3. Confirm warning/error loops did not generate mesh triangles.
4. Confirm the problem is not caused by a hidden ordinary Slope Face object.
5. Record the loop id, loop family, source edge refs, and diagnostics.

If Watertight intersection zone targets are missing:

1. Check `IntersectionSurfaceZoneResult`.
2. Confirm the intersection has accepted surface-zone rows.
3. Refresh Watertight Solids target discovery.

## Result Record

Manual QA result should be recorded as:

```text
Date:
FreeCAD version:
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
