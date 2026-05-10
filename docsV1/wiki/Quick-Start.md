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
6. Assembly
7. Structures
8. Region
9. Drainage
10. Applied Sections
11. Build Corridor
12. Review
13. Outputs

Drainage opens a first-slice source editor. It is placed after Region and before Applied Sections so drainage intent can be stored before downstream corridor evaluation.

## 3. Minimal Smoke Workflow

1. Create or open a project.
2. Prepare a TIN terrain source.
3. Create or edit Alignment.
4. Generate Stations.
5. Edit Profile.
6. Create or select an Assembly.
7. Create Regions from Stationing-based `Start STA` values and reference the Assembly.
8. Optionally open Drainage and apply starter drainage source rows.
9. Run Applied Sections.
10. Run Build Corridor.
11. Review Region Boundaries and Surface Transitions in Build Corridor.
12. Open Cross Section Viewer.
13. Open Plan/Profile Connection Review.
14. Open Earthwork Viewer.

## 4. What To Check

- No command registration errors appear.
- Applied Sections are generated before Build Corridor.
- Build Corridor consumes Applied Sections.
- Region Boundaries show continuous source Region ranges.
- Surface Transition `Spacing` and `Sample Count` match the intended transition density.
- Review panels open without traceback errors.
- Drainage opens the source editor and can store a `V1DrainageModel`.
