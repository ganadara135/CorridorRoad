# Parametric Road

Parametric Road is a FreeCAD workbench for parametric road corridor design, review, and output preparation.

Parametric Road `1.0.3` is the current public v1 release. It continues the v1 workflow reset under the `Parametric Road` user-facing name instead of `Corridor Road`.

The v1 workflow is source-driven: design intent is stored in source models, evaluated results are generated from those sources, and review/output panels expose diagnostics and handoff context.

## Start Here

- [Quick Start](./Quick-Start.md)
- [Workflow](./Workflow.md)
- [Troubleshooting](./Troubleshooting.md)
- [Developer Guide](./Developer-Guide.md)

## Release And Tutorial

- Latest release: https://github.com/ganadara135/CorridorRoad/releases/tag/v1.0.3
- Tutorial video: https://youtu.be/_xpqwnXPUU8
- Forum discussion: https://forum.freecad.org/viewtopic.php?t=103783

## Main V1 Stages

Typical toolbar order:

`Project -> TIN -> Alignment -> Stations/Profile/3D Centerline -> Superelevation -> Assembly -> Regions -> Structures -> Drainage -> Applied Sections -> Build Corridor -> Review -> Outputs -> AI Assist -> Watertight Solids`

Main stages:

- Project Setup
- TIN
- Alignment
- Stations
- Profile
- Review Plan/Profile
- 3D Centerline
- Superelevation
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
- Watertight Solids

## Current Scope

Available in the v1 release direction:

- TIN-first terrain workflow
- Alignment, Stations, and Profile workflow
- shared 3D Centerline review for downstream station/offset/elevation context
- Superelevation source editing, station sample review, 3D crossfall bars, and Applied Sections / Build Parametric handoff
- Assembly and Region source editing
- Structure source editing, connection points, native drainage-structure previews, and Structure Output packages
- Drainage source editing, Flow Routes, Structure-backed pipe network preview, and Drainage Review
- Applied Sections generation
- Build Corridor preview surfaces, Region Boundary review, Surface Transitions, and diagnostics
- Cross Section, Plan/Profile, and Earthwork review surfaces
- Watertight Solids final-stage target discovery, validation, build, and simulation package handoff

In progress:

- Advanced hydraulic analysis and automatic pipe sizing are future work.
- Complete drawing-sheet production and full exchange coverage remain incremental.

## Design Rule

Generated Applied Sections, corridor surfaces, review markers, and output packages are results or outputs.

They should not be treated as the durable editing source.
