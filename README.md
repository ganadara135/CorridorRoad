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

