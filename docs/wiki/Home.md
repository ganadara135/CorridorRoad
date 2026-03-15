# CorridorRoad Wiki

CorridorRoad is a FreeCAD workbench for road corridor design.
This wiki is the practical guide for daily use and development.

## Start Here
- [Quick Start](Quick-Start)
- [Workflow](Workflow)
- [Menu Reference](Menu-Reference)
- [Screenshot Checklist](Screenshot-Checklist)
- [CSV Format](CSV-Format)
- [Troubleshooting](Troubleshooting)
- [Developer Guide](Developer-Guide)

## What You Can Do
- Build alignment/stations/profiles/sections/corridor in one pipeline.
- Import terrain from point cloud CSV using DEM-style grid sampling.
- Run design terrain and cut/fill analysis.

![Workbench overview screen with main toolbar commands visible](images/wiki-home-workbench-overview.png)


## Recommended First Test Data
- `tests/samples/pointcloud_utm_realistic_hilly.csv`
- `tests/samples/alignment_utm_realistic_hilly.csv`
- `tests/samples/structure_utm_realistic_hilly.csv`

Recommended first structure-aware test order:
1. Import the point cloud DEM sample.
2. Import the alignment sample.
3. Generate stations.
4. Load the structure sample in `Edit Structures`.
5. Generate sections and confirm `Structure Sections` appears in the alignment tree.

## How To Use This Wiki
1. Start from [Quick Start](Quick-Start) for first successful run.
2. Use [Workflow](Workflow) when doing full production sequence.
3. Use [Menu Reference](Menu-Reference) when you need detailed meaning for task-panel options.
4. Use [Screenshot Checklist](Screenshot-Checklist) when preparing documentation images.
5. Use [CSV Format](CSV-Format) before importing external survey/alignment data.
6. Open [Troubleshooting](Troubleshooting) when EG/daylight/output issues appear.
7. Use [Developer Guide](Developer-Guide) for code-level changes.

## Questions And Support
- If users or developers have questions about CorridorRoad, please ask in the project thread on the FreeCAD Forum:
- https://forum.freecad.org/viewtopic.php?t=103783
- Use the forum thread for usage questions, bug discussion, and development feedback.

## Core Pipeline
`Terrain (EG) -> Alignment -> Stations -> Structures -> Profiles/PVI -> 3D Centerline -> Sections -> Corridor Loft -> Design Terrain -> Cut/Fill`

![Project tree and pipeline result objects in one view](images/wiki-home-project-tree-pipeline.png)



## Screenshot Insertion Guide
1. Add image files under wiki repo path: `images/`.
2. Use relative markdown links: `![alt](images/<file>.png)`.
3. Keep width around 1600-2200 px for readability on wiki pages.

## Required Environment
- FreeCAD `1.0.2` or newer (recommended)
- Windows 11 (current validation environment)

## Notes
- Daylight terrain source in section workflow is mesh based.
- Runtime terrain/cut-fill sampling follows DEM-style regular XY grid.
- For coordinate-sensitive workflows, confirm Local/World mode before generation commands.
- Structure section overlays are shown in a separate `Structure Sections` tree folder so section display stays loft-safe.

---
Last verified with commit: `<fill-after-release>`
