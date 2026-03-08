# CorridorRoad

CorridorRoad is a FreeCAD workbench for road corridor design.
It covers a practical pipeline from alignment to sections, corridor geometry, design terrain, and cut/fill analysis.

## What This Project Does
- Provides an end-to-end road design workflow:
  - Terrain (EG) -> Horizontal Alignment -> Stationing -> Profiles/PVI -> Centerline3D
  - Assembly -> Sections -> Corridor Loft -> Design Terrain -> Cut/Fill
- Enforces a fixed Civil3D-style project tree schema with automatic object routing.
- Keeps object links and recompute flow organized under a project container.

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
- `02_Alignments/ALN_<Name>/{Horizontal,Stationing,VerticalProfiles,Assembly,Sections,Corridor}`
- `03_Surfaces`
- `04_Analysis`
- `05_References` (optional)

## Current Key Policies
- SectionSet daylight terrain source is `Mesh only`.
- Project Setup is opened from the project context menu.

## Code Layout
- `commands/`: command entry points (toolbar/menu actions)
- `objects/`: parametric object logic
- `ui/`: TaskPanel UI
- `InitGui.py`: workbench registration and command loading

## Good Entry Points For Developers
- `InitGui.py`
- `objects/obj_project.py`
- `objects/obj_section_set.py`
- `ui/task_section_generator.py`
- `commands/cmd_*.py`

## Install and Run
1. Place this folder under your FreeCAD `Mod` directory.
2. Restart FreeCAD.
3. Select the `CorridorRoad` workbench.

## Image List
<img width="753" height="381" alt="Image" src="https://github.com/user-attachments/assets/8afd06ad-2e84-46fe-b8a7-0ca4490f2902" />

<img width="690" height="492" alt="Image" src="https://github.com/user-attachments/assets/da25c711-88a1-4101-acd5-1353fba72ea4" />

<img width="695" height="392" alt="Image" src="https://github.com/user-attachments/assets/e243fb11-cb56-49db-bb64-dbd0af535c8d" />

<img width="726" height="622" alt="Image" src="https://github.com/user-attachments/assets/5638bace-9e6a-4c35-9524-6c66f2f2d36d" />

<img width="814" height="550" alt="Image" src="https://github.com/user-attachments/assets/4f3bf538-04e1-47c2-a3e6-a2139192a48a" />

<img width="846" height="469" alt="Image" src="https://github.com/user-attachments/assets/a6735b8f-b71e-4085-92ef-a06bc5931c7d" />

<img width="556" height="456" alt="Image" src="https://github.com/user-attachments/assets/22571089-b91b-438f-8e32-ede0a823812b" />

<img width="614" height="376" alt="Image" src="https://github.com/user-attachments/assets/999d9e0c-54ee-4fd1-9b63-c287724899ba" />

<img width="1026" height="261" alt="Image" src="https://github.com/user-attachments/assets/88beb6f7-ce66-41e5-bd5d-db4112e6b95c" />

<img width="649" height="564" alt="Image" src="https://github.com/user-attachments/assets/32d4e2ab-c05e-438d-ad8d-a4705bb12825" />
