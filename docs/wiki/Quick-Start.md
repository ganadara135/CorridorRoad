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

## Steps
1. Run `New Project`.
   - Confirm project tree is created.
   - Expected: project container and fixed subfolders are visible.
   - [Screenshot Needed] New project tree created.
   - Suggested file: `wiki-quickstart-step1-new-project.png`
2. Run `Project Setup` and confirm project defaults.
   - Check design standard and coordinate setup lock status.
   - [Screenshot Needed] Project Setup panel.
   - Suggested file: `wiki-quickstart-step2-project-setup.png`
3. Import terrain with `Point Cloud DEM` command using `pointcloud_utm_realistic_hilly.csv`.
   - Verify terrain mesh is generated and visible.
   - [Screenshot Needed] PointCloud DEM import dialog + generated mesh.
   - Suggested file: `wiki-quickstart-step3-pointcloud-dem.png`
4. Open `Alignment` and import `alignment_utm_realistic_hilly.csv`.
   - Verify alignment lies inside terrain extent.
   - [Screenshot Needed] Alignment editor with imported rows.
   - Suggested file: `wiki-quickstart-step4-alignment-import.png`
5. Run `Generate Stations` and click `Generate Stations`.
   - Confirm completion message appears.
   - [Screenshot Needed] Stations completion dialog.
   - Suggested file: `wiki-quickstart-step5-stations-complete.png`
6. Open `Edit Profiles` and fill stations from stationing, then save/apply.
   - Check EG values are filled for most stations.
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
9. Run `Generate Corridor Loft` and click `Build Corridor Loft`.
   - Confirm completion message appears and corridor object is visible.
   - [Screenshot Needed] Corridor Loft completion dialog + result.
   - Suggested file: `wiki-quickstart-step9-corridor-complete.png`

## Expected Result
- Terrain mesh appears.
- Alignment and station ticks are visible.
- 3D centerline wire is created.
- Section set and corridor loft are generated.
- Completion dialogs appear after Stations/Centerline/Sections/Corridor commands.

![Final end-to-end result screen](images/wiki-workflow-07-corridor-surfaces-analysis_3.png)

## If Something Looks Wrong
- If EG has blanks, see [Troubleshooting](Troubleshooting#eg-values-are-blank-or-partially-missing).
- If daylight auto does not react, see [Troubleshooting](Troubleshooting#daylight-auto-does-not-apply).
- If a complex imported structure looks right in 3D but earthwork does not match it, see [Troubleshooting](Troubleshooting#external-shape-is-visible-but-earthwork-does-not-match-it).

---
Last verified with commit: `<fill-after-release>`
