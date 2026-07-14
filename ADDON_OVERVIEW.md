<!-- SPDX-License-Identifier: LGPL-2.1-or-later -->
<!-- SPDX-FileNotice: Part of the Parametric Road addon. -->

# Parametric Road Overview

Parametric Road is a FreeCAD workbench for parametric road corridor design, review, and output preparation.

The current public release is `1.0.9`. This release continues the v1 workflow reset and improves maintained Intersection presets, Cross Intersection tie-slope behavior, Roundabout-specific surface ownership, shared breakline audit, and Build Parametric review behavior.

## Current V1 Workflow

Typical v1 workflow:

1. Create or open a Parametric Road project.
2. Prepare TIN terrain data.
3. Edit Alignment.
4. Generate Stations.
5. Edit Profile.
6. Review Plan/Profile and generate the shared 3D Centerline.
7. Optionally define Superelevation.
8. Edit SubAssembly Designer definitions, Assembly rows, and Region definitions.
9. Define Intersections where multiple Alignments meet.
10. Prepare Structures and Drainage source rows.
11. Generate Applied Sections.
12. Build Parametric preview surfaces.
13. Review Cross Sections, Drainage, Plan/Profile, Earthwork, Intersections, and Breakline Audit diagnostics.
14. Prepare Structure Output and exchange handoff data; Watertight Solid remains compatibility-only while development is paused.

## Available Areas

- Project setup and v1 project tree routing
- TIN editing and review
- Alignment, station, and profile workflow
- shared 3D Centerline review for station/offset/elevation context
- Superelevation source editing and Applied Sections handoff
- SubAssembly Designer and Assembly editor workflow with ditch, side slope, bench, and preset support
- Region editor with continuous station spans and Assembly assignment
- Intersection starter sources, multi-alignment centerline preview, Intersection Slope Face, and Tie Slope review
- Structure editor with connection points and native drainage-structure preview details
- Drainage editor with Elements, Policies, Flow Routes, Structure refs, and Flow Network preview
- Applied Sections generation and review handoff
- Build Parametric preview surfaces, Intersection Tie Slope output, shared breakline audit, and diagnostics
- Cross Section Viewer
- Plan/Profile Connection Review
- Earthwork Viewer and v1-native earthwork report pipeline
- Structure editor and Structure Output package workflow
- Existing Watertight Solids workflow retained as a paused compatibility surface
- Outputs & Exchange entry point
- AI Assist entry point

## In Progress

- Advanced hydraulic analysis, automatic pipe sizing, and full drainage report output are not part of the current release scope.
- Watertight Solid development is paused; no target, topology, simulation, UI, or exchange expansion is active.

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
- Latest release: https://github.com/ganadara135/CorridorRoad/releases/tag/v1.0.9
- Issues: https://github.com/ganadara135/CorridorRoad/issues
- FreeCAD Forum: https://forum.freecad.org/viewtopic.php?t=103783


## Support
- FreeCAD Forum thread: https://forum.freecad.org/viewtopic.php?t=103783

## Video
- Tutorial video: https://youtu.be/_xpqwnXPUU8


## Screenshots
![Parametric Road screenshot 01](https://github.com/user-attachments/assets/83567ce2-ce86-4575-9b81-ba467b878fd0)
![Parametric Road screenshot 02](https://github.com/user-attachments/assets/d5717437-e2a6-412d-99ee-baf4eecd8553)
![Parametric Road screenshot 03](https://github.com/user-attachments/assets/b06d5a1e-04f6-4e41-aee6-b2cec1d45bbd)
![Parametric Road screenshot 13](https://github.com/user-attachments/assets/180ea6e4-3444-4810-a350-091fd899e0ba)
![Parametric Road screenshot 14](https://github.com/user-attachments/assets/64e20bd5-941a-4a09-9efa-4d16e808cd84)
![Parametric Road screenshot 15](https://github.com/user-attachments/assets/9712cf4d-1d3a-4443-b393-257c5837e93f)
