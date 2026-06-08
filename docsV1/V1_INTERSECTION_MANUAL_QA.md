# Parametric Road V1 Intersection Manual QA

Date: 2026-06-07
Status: manual QA procedure; execution pending real FreeCAD document

## Purpose

This checklist verifies the edge-network-first Intersection workflow from source creation through Build Parametric review, Cross Section Viewer context, drainage hints, and Watertight Solid target handoff.

## Scope

This QA covers:

- T, Cross, and Y starter intersection source creation
- multi-alignment 3D Centerline handoff
- Applied Sections with active intersection context
- Build Parametric `Intersections` review rows
- surface-zone responsibility for pavement, curb-return, and Slope Face zones
- ordinary corridor clipping contracts
- drainage low-point and inlet recommendation hints
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
- diagnostics are `ready` or actionable `warning`
- no Report View traceback appears

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
25. Open Watertight Solids.
26. Confirm `Intersection Patch` target remains discoverable.
27. Confirm planned intersection zone targets appear for pavement, subgrade, Slope Face, and curb-return bodies.

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
13. Confirm corridor-clip rows exist for both participating alignments.
14. Confirm drainage-hint rows identify low-point and inlet review candidates.
15. Open Watertight Solids and confirm planned intersection zone target rows are discoverable.

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
13. Confirm Cross Section Viewer reports the correct active leg and control area at a focused station.
14. Confirm Watertight Solids reports planned intersection zone targets.

## Diagnostic Review

For each starter type, record:

- intersection kind
- number of participating alignments
- number of control areas
- edge-network row count
- surface-zone row count
- corridor-clip row count
- drainage-hint row count
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
- visual screenshots for accepted T, Cross, and Y baseline cases
- watertight solid build checks after intersection zone solid builders are implemented
- drainage flow route checks that consume intersection inlet recommendations
