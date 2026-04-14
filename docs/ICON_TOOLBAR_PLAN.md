# Toolbar Icon Plan

This document defines the plan for converting the current CorridorRoad toolbar from text-first commands into an icon-driven toolbar, while keeping menu entries readable and stable.

## Scope

Current state:

- the main toolbar is defined in [freecad/Corridor_Road/init_gui.py](/c:/Users/ganad/AppData/Roaming/FreeCAD/Mod/CorridorRoad/freecad/Corridor_Road/init_gui.py)
- the toolbar originally exposed `17` user-facing commands
- almost every command still returned `Pixmap: ""` from `GetResources()`
- the workbench already has an icon resource folder at [freecad/Corridor_Road/resources/icons](/c:/Users/ganad/AppData/Roaming/FreeCAD/Mod/CorridorRoad/freecad/Corridor_Road/resources/icons)

Planned and now-started change:

- split `PointCloud DEM` into two toolbar commands:
  - `PointCloud DEM`: point cloud + DEM
  - `PointCloud TIN`: point cloud + triangulated network
- for the first implementation stage, `PointCloud TIN` opens a placeholder message:
  - `작업중입니다`

Resulting toolbar count after the split:

- previous: `17`
- target: `18`

## Current Status

- `PR-1`: completed
- `PR-2`: completed
- `PR-3`: completed
- `PR-4`: completed
- `PR-5`: completed

## Goals

1. replace text-only toolbar buttons with recognizable SVG icons
2. keep menu text and tooltips explicit, even if the toolbar becomes icon-first
3. make the icon language consistent across project, alignment, section, corridor, surface, and analysis commands
4. ensure icons remain readable in both FreeCAD dark and light themes
5. introduce the new `PointCloud TIN` command without blocking the icon migration

## Non-Goals

1. this plan does not redesign the internal command architecture
2. this plan does not rename stable command ids unless a new command must be added
3. this plan does not attempt to compress the toolbar by removing commands yet

## Command Inventory

### Target 18-command toolbar

1. `CorridorRoad_NewProject`
2. `CorridorRoad_ProjectSetup`
3. `CorridorRoad_ImportPointCloudDEM`
4. `CorridorRoad_ImportPointCloudTIN`
5. `CorridorRoad_EditAlignment`
6. `CorridorRoad_GenerateStations`
7. `CorridorRoad_EditProfiles`
8. `CorridorRoad_EditPVI`
9. `CorridorRoad_GenerateCenterline3D`
10. `CorridorRoad_EditTypicalSection`
11. `CorridorRoad_EditStructures`
12. `CorridorRoad_EditRegions`
13. `CorridorRoad_GenerateSections`
14. `CorridorRoad_ViewCrossSection`
15. `CorridorRoad_GenerateCorridor`
16. `CorridorRoad_GenerateDesignGradingSurface`
17. `CorridorRoad_GenerateDesignTerrain`
18. `CorridorRoad_GenerateCutFillCalc`

## Icon Language

### Style rules

1. use `SVG` for all toolbar icons
2. prefer simple single-object silhouettes or clean 2-tone geometry
3. avoid tiny internal detail that disappears at small toolbar sizes
4. use a consistent stroke weight and corner style across the full set
5. keep icons readable on dark theme first, without becoming muddy on light theme

### Semantic groups

Project and setup:

- `New Project`: project container, folder, or plus-box metaphor
- `Project Setup`: coordinate axis, gear, or map pin + gear metaphor

Input and base geometry:

- `PointCloud DEM`: point cloud + terrain mesh
- `PointCloud TIN`: point cloud + triangle network
- `Alignment`: plan-view line/curve
- `Stations`: ruler, ticks, or repeated markers
- `Edit Profiles`: profile line
- `Edit PVI`: profile line + editable node
- `3D Centerline`: lifted or 3D line

Section and authoring:

- `Typical Section`: road cross-section glyph
- `Edit Structures`: culvert / box / pipe glyph
- `Edit Regions`: span timeline or layered band glyph
- `Sections`: repeated section slices
- `Cross Section Viewer`: section slice + eye

Generation and analysis:

- `Corridor`: corridor band / strip body
- `Design Grading Surface`: surface mesh / graded face
- `Design Terrain`: terrain merge / layered terrain
- `Cut-Fill Calc`: cut vs fill split, plus/minus, or balanced earthwork glyph

## Resource Structure

Planned icon files in [freecad/Corridor_Road/resources/icons](/c:/Users/ganad/AppData/Roaming/FreeCAD/Mod/CorridorRoad/freecad/Corridor_Road/resources/icons):

1. `new_project.svg`
2. `project_setup.svg`
3. `pointcloud_dem.svg`
4. `pointcloud_tin.svg`
5. `alignment.svg`
6. `stations.svg`
7. `profiles.svg`
8. `pvi.svg`
9. `centerline3d.svg`
10. `typical_section.svg`
11. `structures.svg`
12. `regions.svg`
13. `sections.svg`
14. `cross_section_viewer.svg`
15. `corridor.svg`
16. `design_grading_surface.svg`
17. `design_terrain.svg`
18. `cut_fill.svg`

## Command Wiring Plan

Each command module under [freecad/Corridor_Road/commands](/c:/Users/ganad/AppData/Roaming/FreeCAD/Mod/CorridorRoad/freecad/Corridor_Road/commands) should move from:

- `Pixmap: ""`

to:

- `Pixmap: icon_path("<icon-name>.svg")`

using the shared icon resolver already used by the workbench icon.

## PointCloud Split Plan

### `PointCloud DEM`

Purpose:

- import UTM CSV point cloud data
- generate DEM-oriented terrain output

Icon intent:

- point cloud dots above a simplified terrain face

### `PointCloud TIN`

Purpose:

- import point cloud oriented input for a triangulated surface workflow

Initial implementation behavior:

- the command is visible in toolbar and menu
- when clicked, it shows a message box with:
  - `작업중입니다`

Initial tooltip:

- `Import point cloud data and build triangulated TIN terrain (work in progress)`

Icon intent:

- point cloud dots above a triangle network

## Toolbar UX Policy

1. keep toolbar icon-first
2. keep menu entries text-first
3. do not remove tooltips
4. shorten tooltips where they are too long for quick hover reading
5. preserve current command order unless a stronger workflow grouping is introduced later

Recommended toolbar order after the PointCloud split:

1. project
2. setup
3. point cloud dem
4. point cloud tin
5. alignment
6. stations
7. profiles
8. pvi
9. centerline3d
10. typical section
11. structures
12. regions
13. sections
14. cross section viewer
15. corridor
16. design grading surface
17. design terrain
18. cut-fill calc

## Implementation Sequence

### PR-1. Add icon plan scaffolding

Work:

1. add this plan document
2. confirm final command inventory and naming
3. confirm `PointCloud TIN` placeholder behavior

Done when:

1. the command list is fixed
2. icon filenames are fixed
3. placeholder TIN command scope is agreed

Status:

- completed

### PR-2. Add `PointCloud TIN` command shell

Work:

1. create [cmd_import_pointcloud_tin.py](/c:/Users/ganad/AppData/Roaming/FreeCAD/Mod/CorridorRoad/freecad/Corridor_Road/commands/cmd_import_pointcloud_tin.py)
2. register `CorridorRoad_ImportPointCloudTIN`
3. append it to toolbar and menu
4. when activated, show `작업중입니다`

Done when:

1. toolbar count becomes `18`
2. menu count reflects the new command
3. the placeholder command opens without errors

Status:

- completed

### PR-3. Create first-pass SVG icon set

Work:

1. create the 18 SVG files
2. keep all icons within one visual family
3. review for dark-theme readability first

Done when:

1. every toolbar command has a real icon file
2. no command falls back to an empty pixmap

Status:

- completed

### PR-4. Wire icons to commands

Work:

1. update each command `GetResources()`
2. set `Pixmap` via shared resource lookup
3. verify workbench reload behavior

Done when:

1. all toolbar items show icons
2. command activation still works

Status:

- completed

### PR-5. Tooltip and polish pass

Work:

1. shorten hover text where useful
2. improve icon differentiation for visually similar commands
3. validate against dark and light themes

Done when:

1. toolbar is readable at a glance
2. similar commands are distinguishable without relying only on tooltip text

Status:

- completed

## Validation Checklist

1. workbench loads without command registration errors
2. toolbar shows all target icons
3. menu entries remain readable text
4. `PointCloud TIN` shows `작업중입니다`
5. dark theme readability is acceptable
6. light theme readability is acceptable
7. no icon appears clipped, blurry, or visually off-center

## Risks

1. icons for `Typical Section`, `Sections`, and `Cross Section Viewer` may look too similar if not designed carefully
2. `PointCloud DEM` and `PointCloud TIN` must be distinguishable even at small sizes
3. long tooltips can still make the toolbar feel heavy even after icons are added
4. if every icon is equally dense, the toolbar may become visually noisy rather than clearer

## Recommendation

Next recommended step:

1. observe the toolbar in FreeCAD and collect any remaining icon-confusion pairs
2. refine individual SVGs only where real usage still feels ambiguous

That keeps the toolbar inventory stable before the icon hookup begins.
