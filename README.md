# CorridorRoad

CorridorRoad is a FreeCAD workbench for road corridor design.
It covers a practical pipeline from alignment to sections, corridor geometry, design terrain, and cut/fill analysis.

## What This Project Does
- Provides an end-to-end road design workflow:
  - Terrain (EG) -> Horizontal Alignment -> Stationing -> Profiles/PVI -> Centerline3D
  - Assembly -> Sections -> Corridor Loft -> Design Terrain -> Cut/Fill
- Enforces a fixed Civil3D-style project tree schema with automatic object routing.
- Keeps object links and recompute flow organized under a project container.

## Wiki Documentation
- Online Wiki: https://github.com/ganadara135/CorridorRoad/wiki
- Wiki draft source in this repo: `docs/wiki/`
- Wiki page map: `docs/wiki/WIKI_TOC.md`
- Main wiki pages:
1. Home: https://github.com/ganadara135/CorridorRoad/wiki
2. Quick Start: https://github.com/ganadara135/CorridorRoad/wiki/Quick-Start
3. Workflow: https://github.com/ganadara135/CorridorRoad/wiki/Workflow
4. CSV Format: https://github.com/ganadara135/CorridorRoad/wiki/CSV-Format
5. Troubleshooting: https://github.com/ganadara135/CorridorRoad/wiki/Troubleshooting
6. Developer Guide: https://github.com/ganadara135/CorridorRoad/wiki/Developer-Guide

## Questions And Support
- If general users or developers have questions about this project, please ask in the CorridorRoad project thread on the FreeCAD Forum: https://forum.freecad.org/viewtopic.php?t=103783
- Use the project thread for workflow questions, bug reports, usage problems, and development discussion.

## Main Commands
- `New Project`
- `Project Setup`
- `Sample Alignment`
- `Edit Alignment`
- `Generate Stations`
- `Edit Profiles`
- `Edit PVI`
- `Generate Centerline3D`
- `Generate Sections`
- `Generate Corridor Loft`
- `Generate Design Grading Surface`
- `Generate Design Terrain`
- `Generate Cut/Fill Calc`

## Fixed Project Tree Schema
- `CorridorRoad Project`
- `01_Inputs/{Terrains,Survey,Structures}`
- `02_Alignments/ALN_<Name>/{Horizontal,Stationing,VerticalProfiles,Assembly,Sections,Structure Sections,Corridor}`
- `03_Surfaces`
- `04_Analysis`
- `05_References` (optional)

## Current Key Policies
- SectionSet daylight terrain source is `Mesh only`.
- Project Setup is opened from the project context menu.
- `DesignTerrain`/`CutFillCalc` runtime sampling uses a DEM-style regular XY grid (`CellSize` based), with per-cell elevation queried from source mesh triangles.

## Sample Test Data
- Use the following files for realistic point-cloud terrain testing.
- `tests/samples/pointcloud_utm_realistic_hilly.csv`
- `tests/samples/alignment_utm_realistic_hilly.csv`
- `tests/samples/structure_utm_realistic_hilly.csv`
1. Import `pointcloud_utm_realistic_hilly.csv` as DEM terrain source.
2. Import `alignment_utm_realistic_hilly.csv` as horizontal alignment.
3. After `Generate Stations`, load `structure_utm_realistic_hilly.csv` in `Edit Structures`.
4. Run sections and verify `Structure Sections` tree objects, EG coverage, and daylight behavior.

## Loft Twist Reduction Tips
- If `Corridor Loft` twists or folds, first increase section interval and `Min Section Spacing`.
- Turn on `Use ruled loft` and keep `Auto-fix flipped sections` enabled.
- If `Daylight Auto` is used, reduce abrupt side-width changes with `Daylight Max Width Delta`.
- Check section wires first: unstable EG/FG data, terrain holes, or sudden daylight jumps usually appear there before the loft fails.
- Detailed guidance: https://github.com/ganadara135/CorridorRoad/wiki/Workflow and https://github.com/ganadara135/CorridorRoad/wiki/Troubleshooting

## Code Layout
- `freecad/Corridor_Road/commands/`: command entry points (toolbar/menu actions)
- `freecad/Corridor_Road/objects/`: parametric object logic
- `freecad/Corridor_Road/ui/`: TaskPanel UI
- `freecad/Corridor_Road/init_gui.py`: main workbench registration and command loading

## Good Entry Points For Developers
- `freecad/Corridor_Road/init_gui.py`
- `freecad/Corridor_Road/objects/obj_project.py`
- `freecad/Corridor_Road/objects/obj_section_set.py`
- `freecad/Corridor_Road/ui/task_section_generator.py`
- `freecad/Corridor_Road/commands/cmd_*.py`

## Development Environment
- OS: `Windows 11`
- FreeCAD: `1.0.2`

## Install and Run
1. Place this folder under your FreeCAD `Mod` directory.
2. Restart FreeCAD.
3. Select the `CorridorRoad` workbench.

## License
- This project is licensed under `LGPL-2.1-or-later`.
- See [LICENSE](./LICENSE).

## Video
- https://youtu.be/22JhV0dys3E

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
