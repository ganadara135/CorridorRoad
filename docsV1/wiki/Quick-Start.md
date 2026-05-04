# Quick Start

This page describes the basic CorridorRoad v1 workflow for `1.0.0`.

## 1. Install

1. Place the `CorridorRoad` folder under your FreeCAD `Mod` directory.
2. Restart FreeCAD.
3. Select the `CorridorRoad` workbench.

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

Drainage currently opens an under-development message. It is placed after Region and before Applied Sections so the v1 workflow has the correct future position.

## 3. Minimal Smoke Workflow

1. Create or open a project.
2. Prepare a TIN terrain source.
3. Create or edit Alignment.
4. Generate Stations.
5. Edit Profile.
6. Create or select an Assembly.
7. Create Regions from Stationing-based `Start STA` values and reference the Assembly.
8. Optionally open Drainage and confirm the planned-stage message.
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
- Drainage clearly reports that it is still under development.
