# Parametric Road

Parametric Road is a FreeCAD workbench for parametric road corridor design, review, and output preparation.

Parametric Road `1.0.9` is the current public v1 release. It continues the v1 workflow reset under the `Parametric Road` user-facing name and improves maintained Intersection presets, Cross Intersection tie-slope behavior, Roundabout-specific surface ownership, and shared breakline review behavior.

The current local FreeCAD runtime for development and manual QA is FreeCAD `1.1.1`.

The v1 workflow is source-driven: design intent is stored in source models, evaluated results are generated from those sources, and review/output panels expose diagnostics and handoff context.

## Start Here

- [Quick Start](./Quick-Start.md)
- [Workflow](./Workflow.md)
- [SubAssembly Designer](./SubAssembly-Designer.md)
- [Intersections](./Intersections.md)
- [Troubleshooting](./Troubleshooting.md)
- [Developer Guide](./Developer-Guide.md)

## Release And Tutorial

- Latest release: https://github.com/ganadara135/CorridorRoad/releases/tag/v1.0.9
- Tutorial video: https://youtu.be/_xpqwnXPUU8
- Forum discussion: https://forum.freecad.org/viewtopic.php?t=103783

## Local FreeCAD Environment

- FreeCAD version: `1.1.1`
- Workbench path: `C:\Users\ganad\AppData\Roaming\FreeCAD\v1-1\Mod\CorridorRoad`
- FreeCAD executable: `D:\Program Files\FreeCAD 1.1\bin\FreeCAD.exe`
- FreeCADCmd executable: `D:\Program Files\FreeCAD 1.1\bin\FreeCADCmd.exe`

## Main V1 Stages

Typical toolbar order:

`Project -> TIN -> Alignment -> Stations/Profile/3D Centerline -> Superelevation -> SubAssembly Designer -> Assembly -> Regions -> Intersection -> Structures -> Drainage -> Applied Sections -> Build Corridor -> Review -> Outputs -> AI Assist`

Main stages:

- Project Setup
- TIN
- Alignment
- Stations
- Profile
- Review Plan/Profile
- 3D Centerline
- Superelevation
- SubAssembly Designer
- Assembly
- Region
- Structures
- Drainage
- Drainage Review
- Applied Sections
- Build Corridor
- Cross Section Viewer
- Earthwork Viewer
- Structure Output
- Outputs & Exchange
- AI Assist
- Watertight Solids (paused compatibility surface)

## Current Scope

Available in the v1 release direction:

- TIN-first terrain workflow
- Alignment, Stations, and Profile workflow
- shared 3D Centerline review for downstream station/offset/elevation context
- Superelevation source editing, station sample review, 3D crossfall bars, and Applied Sections / Build Parametric handoff
- SubAssembly Designer reusable point/link/shape definitions with Assembly placement and Applied Sections evaluation
- Assembly and Region source editing
- Intersections starter sources for T Intersection, Cross Intersection, and Roundabout, with multi-alignment Region review and multi-alignment 3D Centerline preview
- Cross Intersection and Roundabout source-driven surface handoff review, including dedicated intersection/roundabout slope outputs and roundabout ordinary-surface clipping
- Structure source editing, connection points, native drainage-structure previews, and Structure Output packages
- Drainage source editing, Flow Routes, Structure-backed pipe network preview, and Drainage Review
- Applied Sections generation
- Build Corridor preview surfaces, Region Boundary review, Surface Transitions, and diagnostics
- Cross Section, Plan/Profile, and Earthwork review surfaces
- existing Watertight Solids compatibility behavior; active feature development is paused

In progress:

- Advanced hydraulic analysis and automatic pipe sizing are future work.
- Complete drawing-sheet production and full exchange coverage remain incremental.

## Design Rule

Generated Applied Sections, corridor surfaces, review markers, and output packages are results or outputs.

They should not be treated as the durable editing source.
