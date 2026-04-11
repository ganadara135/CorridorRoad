<!-- SPDX-License-Identifier: LGPL-2.1-or-later -->
<!-- SPDX-FileNotice: Part of the Corridor Road addon. -->

# Quick Start

This page gets you from empty document to visible corridor output quickly.

## Goal
Create a minimal but realistic run using sample point cloud and alignment CSV files.

## Prerequisites
- CorridorRoad addon installed under FreeCAD `Mod` path.
- Active FreeCAD document.
- Coordinate setup and terrain coordinate mode understood (`Local` vs `World`).

## Input Files
- `tests/samples/pointcloud_utm_realistic_hilly.csv`
- `tests/samples/alignment_utm_realistic_hilly.csv`
- Optional manual FG starter:
  - `tests/samples/profile_fg_manual_import_basic.csv`
  - `tests/samples/profile_fg_manual_import_aliases.csv`

For the maintained extended sample inventory, see [../PRACTICAL_SAMPLE_SET.md](../PRACTICAL_SAMPLE_SET.md).

## Steps
1. Run `New Project`.
   - Confirm project tree is created.
   - Expected: project container and fixed subfolders are visible.
   - [Screenshot Needed] New project tree created.
   - Suggested file: `wiki-quickstart-step1-new-project.png`
2. Run `Project Setup` and confirm project defaults.
3. If `CRS / EPSG` is filled, keep `Coordinate Workflow = World-first`.
4. If the project stays in local engineering coordinates, use `Coordinate Workflow = Local-first`.
   - The `CRS / EPSG` field is an editable preset-style combo, so you can pick a common EPSG code first and type manually only when needed.
   - Check design standard and coordinate setup lock status.
   - [Screenshot Needed] Project Setup panel.
   - Suggested file: `wiki-quickstart-step2-project-setup.png`
3. Import terrain with `Point Cloud DEM` command using `pointcloud_utm_realistic_hilly.csv`.
   - Verify terrain mesh is generated and visible.
   - [Screenshot Needed] PointCloud DEM import dialog + generated mesh.
   - Suggested file: `wiki-quickstart-step3-pointcloud-dem.png`
4. Open `Alignment` and import `alignment_utm_realistic_hilly.csv`.
   - Alternatively, choose an alignment `Preset` and click `Load Preset` when you want a quick starter geometry instead of a real CSV.
   - `Preset Placement` now defaults to `Center on terrain`, so starter geometry usually lands inside the current terrain extent automatically.
   - If `Coord Input = World (E/N)`, preset rows are converted from local pattern coordinates using the current `Project Setup`.
   - Verify alignment lies inside terrain extent.
   - [Screenshot Needed] Alignment editor with imported rows.
   - Suggested file: `wiki-quickstart-step4-alignment-import.png`
5. Run `Generate Stations` and click `Generate Stations`.
   - Confirm completion message appears.
   - [Screenshot Needed] Stations completion dialog.
   - Suggested file: `wiki-quickstart-step5-stations-complete.png`
6. Open `Edit Profiles` and fill stations from stationing, then save/apply.
   - Check EG values are filled for most stations.
   - If you want a manual FG start without `Edit PVI`, turn off `FG from VerticalAlignment` and use `Import FG CSV` with `profile_fg_manual_import_basic.csv` or `profile_fg_manual_import_aliases.csv`.
   - [Screenshot Needed] Profile table with EG values.
   - Suggested file: `wiki-quickstart-step6-profiles-eg.png`
7. Run `3D Centerline`.
   - Confirm completion message appears and 3D wire is visible.
   - [Screenshot Needed] 3D Centerline completion dialog + wire.
   - Suggested file: `wiki-quickstart-step7-centerline-complete.png`
8. Run `Generate Sections` and click `Generate Sections Now`.
   - Confirm completion message appears and section set is created.
   - [Screenshot Needed] Sections completion dialog.
   - Suggested file: `wiki-quickstart-step8-sections-complete.png`
9. Run `Corridor` and click `Build Corridor`.
   - Confirm completion message appears and corridor object is visible.
   - [Screenshot Needed] Corridor completion dialog + result.
   - Suggested file: `wiki-quickstart-step9-corridor-complete.png`

## Expected Result
- Terrain mesh appears.
- Alignment and station ticks are visible.
- 3D centerline wire is created.
- Section set and corridor are generated.
- Completion dialogs appear after Stations/Centerline/Sections/Corridor commands.

![Final end-to-end result screen](images/wiki-workflow-07-corridor-surfaces-analysis_3.png)

## If Something Looks Wrong
- If EG has blanks, see [Troubleshooting](Troubleshooting#eg-values-are-blank-or-partially-missing).
- If daylight auto does not react, see [Troubleshooting](Troubleshooting#daylight-auto-does-not-apply).
- If a complex imported structure looks right in 3D but earthwork does not match it, see [Troubleshooting](Troubleshooting#external-shape-is-visible-but-earthwork-does-not-match-it).

---
Last verified with commit: `61ba6d5`
