<!-- SPDX-License-Identifier: LGPL-2.1-or-later -->
<!-- SPDX-FileNotice: Part of the Parametric Road addon. -->

# Parametric Road Overview

Parametric Road is a FreeCAD workbench for parametric road corridor design, review, and output preparation.

The current public release is `1.0.1`. This release continues the v1 workflow reset and introduces the user-facing name `Parametric Road` in place of `Corridor Road`, because the project is growing beyond a corridor-surface generator into a broader parametric road-design and simulation-preparation workflow.

## Current V1 Workflow

Typical v1 workflow:

1. Create or open a Parametric Road project.
2. Prepare TIN terrain data.
3. Edit Alignment.
4. Generate Stations.
5. Edit Profile.
6. Review Plan/Profile and generate the shared 3D Centerline.
7. Edit Assembly and Region definitions.
8. Prepare Structures and Drainage source rows.
9. Generate Applied Sections.
10. Build Corridor preview surfaces.
11. Review Cross Sections, Drainage, Plan/Profile, and Earthwork.
12. Prepare Watertight Solids, Structure Output, and exchange handoff data where available.

## Available Areas

- Project setup and v1 project tree routing
- TIN editing and review
- Alignment, station, and profile workflow
- Assembly editor with ditch, side slope, bench, and preset support
- shared 3D Centerline review for station/offset/elevation context
- Region editor with continuous station spans and Assembly assignment
- Structure editor with connection points and native drainage-structure preview details
- Drainage editor with Elements, Policies, Flow Routes, Structure refs, and Flow Network preview
- Applied Sections generation and review handoff
- Build Corridor preview surfaces and diagnostics
- Cross Section Viewer
- Plan/Profile Connection Review
- Earthwork Viewer and v1-native earthwork report pipeline
- Structure editor and Structure Output package workflow
- Watertight Solids final-stage workflow for selected road, component, drainage, and structure solid targets
- Outputs & Exchange entry point
- AI Assist entry point

## In Progress

- Advanced hydraulic analysis, automatic pipe sizing, and full drainage report output are not part of the current release scope.
- Watertight Solid package composition is continuing toward terrain-inclusive simulation handoff.

## Design Direction

Parametric Road v1 follows a source -> evaluation -> result -> output -> presentation structure.

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
- Latest release: https://github.com/ganadara135/CorridorRoad/releases/tag/v1.0.1
- Issues: https://github.com/ganadara135/CorridorRoad/issues
- FreeCAD Forum: https://forum.freecad.org/viewtopic.php?t=103783


## Support
- FreeCAD Forum thread: https://forum.freecad.org/viewtopic.php?t=103783

## Video
- Tutorial video: https://youtu.be/_xpqwnXPUU8


## Screenshots
![Parametric Road screenshot 13](https://github.com/user-attachments/assets/180ea6e4-3444-4810-a350-091fd899e0ba)
![Parametric Road screenshot 14](https://github.com/user-attachments/assets/64e20bd5-941a-4a09-9efa-4d16e808cd84)
![Parametric Road screenshot 15](https://github.com/user-attachments/assets/9712cf4d-1d3a-4443-b393-257c5837e93f)
