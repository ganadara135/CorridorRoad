# CorridorRoad

CorridorRoad is a FreeCAD workbench for corridor-style road design, review, and output preparation.

CorridorRoad `1.0.0` is the first v1 workflow release. The v1 workflow is source-driven: design intent is stored in source models, evaluated results are generated from those sources, and review/output panels expose diagnostics and handoff context.

## Start Here

- [Quick Start](./Quick-Start.md)
- [Workflow](./Workflow.md)
- [Troubleshooting](./Troubleshooting.md)
- [Developer Guide](./Developer-Guide.md)

## Main V1 Stages

Typical toolbar order:

`Project -> TIN -> Alignment -> Stations/Profile -> Assembly/Structures/Region -> Drainage -> Applied Sections -> Build Corridor -> Review -> Outputs`

Main stages:

- Project Setup
- TIN
- Alignment
- Stations
- Profile
- Assembly
- Structures
- Region
- Drainage
- Applied Sections
- Build Corridor
- Cross Section Viewer
- Plan/Profile Connection Review
- Earthwork Viewer
- Structure Output
- Outputs & Exchange
- AI Assist

## Current Scope

Available in the v1 release direction:

- TIN-first terrain workflow
- Alignment, Stations, and Profile workflow
- Assembly and Region source editing
- Structure source editing and Structure Output packages
- Applied Sections generation
- Build Corridor preview surfaces, Region Boundary review, Surface Transitions, and diagnostics
- Cross Section, Plan/Profile, and Earthwork review surfaces

In progress:

- Drainage has a toolbar/menu entry and planning document.
- The full Drainage Editor is not complete in `1.0.0`.
- Advanced hydraulic analysis and automatic pipe sizing are future work.

## Design Rule

Generated Applied Sections, corridor surfaces, review markers, and output packages are results or outputs.

They should not be treated as the durable editing source.
