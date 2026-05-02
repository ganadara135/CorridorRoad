<!-- SPDX-License-Identifier: LGPL-2.1-or-later -->
<!-- SPDX-FileNotice: Part of the Corridor Road addon. -->

# CorridorRoad Overview

CorridorRoad is a FreeCAD workbench for corridor-style road design, review, and output preparation.

The current development focus is the v1 workflow reset: clear source models, evaluated results, review viewers, and output packages instead of editing generated geometry directly.

## Current V1 Workflow

Typical v1 workflow:

1. Create or open a CorridorRoad project.
2. Prepare TIN terrain data.
3. Edit Alignment.
4. Generate Stations.
5. Edit Profile.
6. Edit Assembly and Region definitions.
7. Optionally prepare Structures and Drainage references.
8. Generate Applied Sections.
9. Build Corridor preview surfaces.
10. Review Cross Sections, Plan/Profile, and Earthwork.
11. Prepare Structure Output and exchange handoff data where available.

## Available Areas

- Project setup and v1 project tree routing
- TIN editing and review
- Alignment, station, and profile workflow
- Assembly editor with ditch, side slope, bench, and preset support
- Region editor with assembly, structure, and drainage references
- Applied Sections generation and review handoff
- Build Corridor preview surfaces and diagnostics
- Cross Section Viewer
- Plan/Profile Connection Review
- Earthwork Viewer and v1-native earthwork report pipeline
- Structure editor and Structure Output package workflow
- Outputs & Exchange entry point
- AI Assist entry point

## In Progress

- Drainage has a toolbar/menu entry and a planning document, but the full Drainage Editor is still under development.
- Drainage currently appears mainly through Assembly ditch shapes, Applied Section `ditch_surface` points, Build Corridor drainage diagnostics, and planned `DrainageModel` integration.
- Advanced hydraulic analysis, automatic pipe sizing, and full drainage report output are not part of the current release scope.

## Design Direction

CorridorRoad v1 follows a source -> evaluation -> result -> output -> presentation structure.

- Source intent belongs in models such as Alignment, Profile, Assembly, Region, Structure, and Drainage.
- Applied Sections and Corridor surfaces are generated results.
- Review viewers expose diagnostics and handoff context.
- Output packages preserve source traceability for later exchange and reporting.

## Documentation

Primary v1 design documents are in `docsV1/`.

Key references:

- `docsV1/V1_MASTER_PLAN.md`
- `docsV1/V1_SECTION_MODEL.md`
- `docsV1/V1_REGION_MODEL.md`
- `docsV1/V1_STRUCTURE_GEOMETRY_CONTRACT.md`
- `docsV1/V1_EARTHWORK_IMPLEMENTATION_PLAN.md`
- `docsV1/V1_DRAINAGE_IMPLEMENTATION_PLAN.md`

Online project resources:

- Wiki: https://github.com/ganadara135/CorridorRoad/wiki
- Releases: https://github.com/ganadara135/CorridorRoad/releases
- Issues: https://github.com/ganadara135/CorridorRoad/issues
- FreeCAD Forum: https://forum.freecad.org/viewtopic.php?t=103783


## Support
- FreeCAD Forum thread: https://forum.freecad.org/viewtopic.php?t=103783

## Video
- https://youtu.be/P0kiPREy2qE


## Screenshots
![CorridorRoad screenshot 13](https://github.com/user-attachments/assets/180ea6e4-3444-4810-a350-091fd899e0ba)
![CorridorRoad screenshot 14](https://github.com/user-attachments/assets/64e20bd5-941a-4a09-9efa-4d16e808cd84)
![CorridorRoad screenshot 15](https://github.com/user-attachments/assets/9712cf4d-1d3a-4443-b393-257c5837e93f)
