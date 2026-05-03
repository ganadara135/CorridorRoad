<!-- SPDX-License-Identifier: LGPL-2.1-or-later -->
<!-- SPDX-FileNotice: Part of the Corridor Road addon. -->

# CorridorRoad

CorridorRoad is a FreeCAD workbench for corridor-style road design, review, and output preparation.

## Support CorridorRoad

CorridorRoad is developed as an open-source road design workbench for FreeCAD. If this project saves you time, helps your civil design workflow, or you want to support continued v1 development, please consider sponsoring the project:

[Sponsor CorridorRoad on GitHub](https://github.com/sponsors/ganadara135)

Sponsorship helps fund focused work on the v1 workflow, documentation, testing, and practical road-design features that are difficult to sustain through spare-time development alone.

The current release direction is CorridorRoad `1.0.0`, the first v1 workflow release. v1 focuses on source-driven corridor modeling: design intent is stored in source models, evaluated results are generated from those sources, and review/output panels expose diagnostics without turning generated geometry into the editing source.

## What This Project Does

CorridorRoad v1 provides a staged road corridor workflow:

1. Prepare project and TIN terrain data.
2. Edit Alignment.
3. Generate Stations.
4. Edit Profile.
5. Define Assembly, Structures, and Regions.
6. Prepare Drainage references where applicable.
7. Generate Applied Sections.
8. Build Corridor preview surfaces.
9. Review Cross Sections, Plan/Profile, and Earthwork.
10. Prepare structure output and exchange handoff data where available.

The workbench is built around a v1 source -> evaluation -> result -> output -> presentation structure.

- Source intent belongs in Alignment, Profile, Assembly, Region, Structure, and Drainage models.
- Applied Sections and Corridor surfaces are generated results.
- Review panels expose context, diagnostics, and handoff actions.
- Output packages preserve source traceability.

## Wiki Documentation

- Online Wiki: https://github.com/ganadara135/CorridorRoad/wiki
- Quick Start: https://github.com/ganadara135/CorridorRoad/wiki/Quick-Start
- Workflow: https://github.com/ganadara135/CorridorRoad/wiki/Workflow
- Troubleshooting: https://github.com/ganadara135/CorridorRoad/wiki/Troubleshooting
- Developer Guide: https://github.com/ganadara135/CorridorRoad/wiki/Developer-Guide

For v1 design and implementation planning, see `docsV1/`.

Important v1 references:

- `docsV1/V1_MASTER_PLAN.md`
- `docsV1/V1_RELEASE_1_0_0_PLAN.md`
- `docsV1/V1_SECTION_MODEL.md`
- `docsV1/V1_REGION_MODEL.md`
- `docsV1/V1_STRUCTURE_GEOMETRY_CONTRACT.md`
- `docsV1/V1_EARTHWORK_IMPLEMENTATION_PLAN.md`
- `docsV1/V1_DRAINAGE_IMPLEMENTATION_PLAN.md`

## Questions And Support

- FreeCAD Forum thread: https://forum.freecad.org/viewtopic.php?t=103783
- GitHub Issues: https://github.com/ganadara135/CorridorRoad/issues
- Use the forum thread for workflow questions, usage discussion, and development direction.
- Use GitHub Issues for reproducible bugs and release blockers.

## Latest Release

- Current release target: `v1.0.0`
- Planned tag: `v1.0.0`
- GitHub Releases: https://github.com/ganadara135/CorridorRoad/releases
- Release plan: `docsV1/V1_RELEASE_1_0_0_PLAN.md`

## Main Commands

- `Project Setup`
- `TIN`
- `Alignment`
- `Stations`
- `Profile`
- `Assembly`
- `Structures`
- `Region`
- `Drainage`
- `Applied Sections`
- `Build Corridor`
- `Cross Section Viewer`
- `Plan/Profile Connection Review`
- `Earthwork Viewer`
- `Structure Output`
- `Outputs & Exchange`
- `AI Assist`

Current toolbar order is organized around the v1 workflow:

`Project -> TIN -> Alignment -> Stations/Profile -> Assembly/Structures/Region -> Drainage -> Applied Sections -> Build Corridor -> Review -> Outputs`

Drainage currently has a toolbar/menu entry and planning document. The full Drainage Editor is still under development.

## Current V1 Areas

- Project setup and v1 project tree routing
- TIN editing and review
- Alignment editing
- Station generation
- Profile editing with PVI rows, CSV support, and auto interpolation
- Assembly editor with ditch, side slope, bench, and preset support
- Structure editor for bridge, culvert, retaining wall, and related source intent
- Region editor with assembly, structure, and drainage references
- Applied Sections result generation
- Build Corridor preview surfaces and diagnostics
- Cross Section Viewer
- Plan/Profile Connection Review
- Earthwork Viewer and v1-native earthwork report path
- Structure Output packages and export-readiness diagnostics
- Outputs & Exchange entry point
- AI Assist entry point

## In Progress

- Drainage editing is planned but not complete in `1.0.0`.
- Drainage currently appears through Assembly ditch shapes, Applied Section `ditch_surface` rows, Build Corridor drainage diagnostics, and the planned `DrainageModel` workflow.
- Advanced hydraulic analysis, automatic pipe sizing, complete drawing-sheet production, and full exchange output coverage are outside the current release scope.

## Install And Run

1. Place this folder under your FreeCAD `Mod` directory.
2. Restart FreeCAD.
3. Select the `CorridorRoad` workbench.

Recommended FreeCAD version:

- FreeCAD `1.0.x`
- Python `3.10+`

## Release And Versioning Policy

- `main` is the release/stable branch.
- Development work may continue on a separate development branch.
- Package metadata is stored in `package.xml`.
- Release notes are recorded in `CHANGELOG.md`.
- Release tags should use `vX.Y.Z`, for example `v1.0.0`.

Release procedure summary:

1. Freeze feature work.
2. Run automated and manual validation.
3. Update `package.xml`.
4. Update `CHANGELOG.md`.
5. Update Wiki pages.
6. Tag the release.
7. Publish the GitHub Release.

## Developer Notes

Important code entry points:

- `freecad/Corridor_Road/init_gui.py`
- `freecad/Corridor_Road/v1/commands/`
- `freecad/Corridor_Road/v1/models/source/`
- `freecad/Corridor_Road/v1/models/result/`
- `freecad/Corridor_Road/v1/models/output/`
- `freecad/Corridor_Road/v1/services/`
- `freecad/Corridor_Road/v1/ui/`

Testing guidance:

- Use the FreeCAD Python executable when tests depend on FreeCAD modules.
- Prefer focused v1 contract tests and service tests for release validation.

## License

- This project is licensed under `LGPL-2.1-or-later`.
- See [LICENSE](./LICENSE).

## Video

- https://youtu.be/P0kiPREy2qE

## Screenshots
![CorridorRoad screenshot 01](https://github.com/user-attachments/assets/8afd06ad-2e84-46fe-b8a7-0ca4490f2902)
![CorridorRoad screenshot 02](https://github.com/user-attachments/assets/da25c711-88a1-4101-acd5-1353fba72ea4)
![CorridorRoad screenshot 03](https://github.com/user-attachments/assets/e243fb11-cb56-49db-bb64-dbd0af535c8d)
![CorridorRoad screenshot 04](https://github.com/user-attachments/assets/5638bace-9e6a-4c35-9524-6c66f2f2d36d)
![CorridorRoad screenshot 05](https://github.com/user-attachments/assets/4f3bf538-04e1-47c2-a3e6-a2139192a48a)
![CorridorRoad screenshot 06](https://github.com/user-attachments/assets/a6735b8f-b71e-4085-92ef-a06bc5931c7d)
![CorridorRoad screenshot 07](https://github.com/user-attachments/assets/22571089-b91b-438f-8e32-ede0a823812b)
![CorridorRoad screenshot 08](https://github.com/user-attachments/assets/999d9e0c-54ee-4fd1-9b63-c287724899ba)
![CorridorRoad screenshot 09](https://github.com/user-attachments/assets/88beb6f7-ce66-41e5-bd5d-db4112e6b95c)
![CorridorRoad screenshot 10](https://github.com/user-attachments/assets/32d4e2ab-c05e-438d-ad8d-a4705bb12825)
![CorridorRoad screenshot 11](https://github.com/user-attachments/assets/71d0cb7d-50e9-4c66-be81-727b0e0840b6)
![CorridorRoad screenshot 12](https://github.com/user-attachments/assets/9712cf4d-1d3a-4443-b393-257c5837e93f)
![CorridorRoad screenshot 13](https://github.com/user-attachments/assets/64e20bd5-941a-4a09-9efa-4d16e808cd84)
