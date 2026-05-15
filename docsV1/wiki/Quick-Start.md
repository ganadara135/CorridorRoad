# Quick Start

This page describes the basic Parametric Road v1 workflow for `1.0.0`.

## 1. Install

1. Place the `CorridorRoad` folder under your FreeCAD `Mod` directory.
2. Restart FreeCAD.
3. Select the `Parametric Road` workbench.

If commands do not appear after an update, restart FreeCAD or reload the workbench.

## 2. Recommended Workflow

Use this order:

1. Project Setup
2. TIN
3. Alignment
4. Stations
5. Profile
6. Review Plan/Profile
7. 3D Centerline
8. Assembly
9. Region
10. Structures
11. Drainage
12. Applied Sections
13. Build Corridor
14. Review
15. Outputs
16. AI Assist
17. Watertight Solids

Drainage opens a source editor with Elements, Policies, and Flow Routes. It is placed after Region and Structures so Drainage Elements can reference Region ownership and Structure connection points before downstream corridor evaluation.

## 3. Minimal Smoke Workflow

1. Create or open a project.
2. Prepare a TIN terrain source.
3. Create or edit Alignment.
4. Generate Stations.
5. Edit Profile.
6. Open Review Plan/Profile, then generate or refresh 3D Centerline.
7. Create or select an Assembly.
8. Create Regions from Stationing-based `Start STA` values and reference the Assembly.
9. Optionally open Structures and apply Structure source rows.
10. Optionally open Drainage and apply drainage source rows.
11. Run Applied Sections.
12. Run Build Corridor.
13. Review Region Boundaries and Surface Transitions in Build Corridor.
14. Open Cross Section Viewer.
15. Open Drainage Review or show the Flow Network if Structure-backed drainage is present.
16. Open Earthwork Viewer.
17. Open Watertight Solids after Build Corridor when solid targets are needed.

## 4. What To Check

- No command registration errors appear.
- Applied Sections are generated before Build Corridor.
- Build Corridor consumes Applied Sections.
- Region Boundaries show continuous source Region ranges.
- Surface Transition `Spacing` and `Sample Count` match the intended transition density.
- Review panels open without traceback errors.
- Drainage opens the source editor and can store a `V1DrainageModel`.
- Structure-backed Drainage Flow Routes can resolve to connection-point based pipe previews.
- Watertight Solids remains gated until Build Corridor prerequisites are ready.
