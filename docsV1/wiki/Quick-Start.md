# Quick Start

This page describes the basic Parametric Road v1 workflow for `1.0.5`.

## 1. Install

1. Place the `CorridorRoad` folder under your FreeCAD `Mod` directory.
2. Restart FreeCAD.
3. Select the `Parametric Road` workbench.

If commands do not appear after an update, restart FreeCAD or reload the workbench.

Tutorial video: https://youtu.be/_xpqwnXPUU8

## 2. Recommended Workflow

Use this order:

1. Project Setup
2. TIN
3. Alignment
4. Stations
5. Profile
6. Review Plan/Profile
7. 3D Centerline
8. Superelevation
9. SubAssembly Designer
10. Assembly
11. Region
12. Structures
13. Drainage
14. Applied Sections
15. Build Corridor
16. Review
17. Outputs
18. AI Assist
19. Watertight Solids

Drainage opens a source editor with Elements, Policies, and Flow Routes. It is placed after Region and Structures so Drainage Elements can reference Region ownership and Structure connection points before downstream corridor evaluation.

Superelevation is optional, but when used it should be applied before Applied Sections.

SubAssembly Designer is optional when using existing presets, but it should be used before Assembly when reusable section definitions or closed shape rows are needed.

For Intersections, see [Intersections](./Intersections.md). Use `Use Existing Alignments` when the road sources already exist, or `Create Starter Sources` when you want a starter junction created for you.

## 3. Minimal Smoke Workflow

1. Create or open a project.
2. Prepare a TIN terrain source.
3. Create or edit Alignment.
4. Generate Stations.
5. Edit Profile.
6. Open Review Plan/Profile, then generate or refresh 3D Centerline.
7. Optionally open Superelevation, load a preset, validate, show samples, and apply.
8. Optionally open SubAssembly Designer, create reusable definitions, and apply the library.
9. Create or select an Assembly and place Subassembly definitions.
10. Create Regions from Stationing-based `Start STA` values and reference the Assembly.
11. Optionally open Intersections. Use `Create Starter Sources` for a starter junction; it creates participating sources and a multi-alignment 3D Centerline.
12. Optionally open Structures and apply Structure source rows.
13. Optionally open Drainage and apply drainage source rows.
14. Run Applied Sections.
15. Run Build Corridor.
16. Review Region Boundaries and Surface Transitions in Build Corridor.
17. Open Cross Section Viewer.
18. Open Drainage Review or show the Flow Network if Structure-backed drainage is present.
19. Open Earthwork Viewer.
20. Open Watertight Solids after Build Corridor when solid targets are needed.

## 4. What To Check

- No command registration errors appear.
- Applied Sections are generated before Build Corridor.
- Build Corridor consumes Applied Sections.
- Superelevation changes require rebuilding Applied Sections before Build Corridor.
- SubAssembly Designer definitions are evaluated through Applied Sections, not directly by Build Corridor.
- Region Boundaries show continuous source Region ranges.
- For Intersections starter data, Region Boundaries show primary-road and side-road Region rows with Alignment context.
- 3D Centerline shows all participating starter Alignments before Applied Sections are built.
- Surface Transition `Spacing` and `Sample Count` match the intended transition density.
- Review panels open without traceback errors.
- Drainage opens the source editor and can store a `V1DrainageModel`.
- Structure-backed Drainage Flow Routes can resolve to connection-point based pipe previews.
- Watertight Solids remains gated until Build Corridor prerequisites are ready.
