<!-- SPDX-License-Identifier: LGPL-2.1-or-later -->
<!-- SPDX-FileNotice: Part of the Corridor Road addon. -->

# Screenshot Checklist

This page is a practical capture checklist for CorridorRoad wiki screenshots.
Use it when preparing images for `docs/wiki/images/` and the GitHub Wiki `images/` folder.

## Goal
Capture screenshots that are consistent, readable, and directly matched to the current wiki pages.

## Before You Start
1. Use the current sample files:
   - `tests/samples/pointcloud_utm_realistic_hilly.csv`
   - `tests/samples/alignment_utm_realistic_hilly.csv`
2. Open a clean FreeCAD document when possible.
3. Keep the workbench set to `CorridorRoad`.
4. Expand the project tree so important result objects are visible.
5. Use a window size that shows the full task panel without clipping.
6. Avoid overlapping modal dialogs unless the screenshot is specifically for a completion popup.
7. If possible, keep the UI language consistent across all captures.

## Capture Style Rules
1. Prefer PNG.
2. Keep width around `1600-2200 px`.
3. Capture the full task panel when documenting options.
4. Capture the relevant 3D result together with the task panel when the result matters.
5. Avoid unrelated objects selected in the tree unless selection is part of the explanation.
6. Use the same zoom level for before/after comparisons whenever possible.
7. If a screenshot is for troubleshooting, make sure the failure symptom is clearly visible.

## Recommended Folder And Naming
1. Store local draft images in `docs/wiki/images/`.
2. Use the same relative path in the wiki repo: `images/`.
3. Keep file names exactly aligned with wiki placeholders.

## Capture Order
Follow this order so one project session can produce most screenshots without rework.

1. `New Project`
2. `Project Setup`
3. `PointCloud DEM`
4. `Alignment`
5. `Generate Stations`
6. `Edit Profiles`
7. `Edit PVI`
8. `3D Centerline`
9. `Generate Sections`
10. `Corridor`
11. Troubleshooting examples if needed

## Checklist By Page

### Home
- [ ] `images/wiki-home-workbench-overview.png`
  - Show the CorridorRoad workbench and main toolbar/menu area.
- [ ] `images/wiki-home-project-tree-pipeline.png`
  - Show the project tree with main generated objects visible.

### Quick Start
- [ ] `images/wiki-quickstart-step1-new-project.png`
  - Capture right after `New Project`.
  - Show project tree creation clearly.
- [ ] `images/wiki-quickstart-step2-project-setup.png`
  - Capture `Project Setup` with basic values visible.
- [ ] `images/wiki-quickstart-step3-pointcloud-dem.png`
  - Show `PointCloud DEM` task panel and generated terrain mesh together if possible.
- [ ] `images/wiki-quickstart-step4-alignment-import.png`
  - Show imported alignment table or alignment geometry clearly.
- [ ] `images/wiki-quickstart-step5-stations-complete.png`
  - Show the completion dialog after station generation.
- [ ] `images/wiki-quickstart-step6-profiles-eg.png`
  - Show EG-filled profile table.
- [ ] `images/wiki-quickstart-step7-centerline-complete.png`
  - Show 3D centerline completion popup and centerline wire.
- [ ] `images/wiki-quickstart-step8-sections-complete.png`
  - Show section generation completion popup.
- [ ] `images/wiki-quickstart-step9-corridor-complete.png`
  - Show corridor completion popup and resulting corridor.

### Workflow
- [ ] `images/wiki-workflow-01-project-init.png`
  - Show project tree immediately after setup.
- [ ] `images/wiki-workflow-02-terrain-eg.png`
  - Show DEM source import state or terrain result.
- [ ] `images/wiki-workflow-02-terrain-eg_2.png`
  - Alternate terrain-focused view with mesh visible.
- [ ] `images/wiki-workflow-03-horizontal-alignment.png`
  - Show alignment geometry and key points.
- [ ] `images/wiki-workflow-03-horizontal-alignment_2.png`
  - Alternate alignment view from another zoom or orientation.
- [ ] `images/wiki-workflow-04-stations-profiles.png`
  - Show station-related result objects or profile workflow context.
- [ ] `images/wiki-workflow-04-stations-profiles_2.png`
  - Show EG profile table state.
- [ ] `images/wiki-workflow-04-stations-profiles_3.png`
  - Show FG profile table state.
- [ ] `images/wiki-workflow-05-centerline3d.png`
  - Show 3D centerline wire and completion confirmation.
- [ ] `images/wiki-workflow-06-sections.png`
  - Show Sections task panel.
- [ ] `images/wiki-workflow-06-sections_2.png`
  - Show generated section set or child section result.
- [ ] `images/wiki-workflow-07-corridor-surfaces-analysis.png`
  - Show a failed corridor example with the problem visible.
- [ ] `images/wiki-workflow-07-corridor-surfaces-analysis_2.png`
  - Show a stable corridor result.
- [ ] `images/wiki-workflow-07-corridor-surfaces-analysis_3.png`
  - Show cut/fill or final end-to-end result.
- [ ] `images/wiki-workflow-07a-corridor-loft-stability-options.png`
  - Show `Corridor` options including `Min Section Spacing`, `Use ruled surface`, and `Auto-fix flipped sections`.
- [ ] `images/wiki-workflow-07b-daylight-max-width-delta.png`
  - Show `Generate Sections` options with `Daylight Max Width Delta` visible.

### Menu Reference
- [ ] `images/wiki-menu-reference-project-setup.png`
  - Show all major `Project Setup` fields in one view.
- [ ] `images/wiki-menu-reference-pointcloud-dem.png`
  - Show `PointCloud DEM` options including `Cell Size`, `Aggregation`, and coordinate settings.
- [ ] `images/wiki-menu-reference-edit-profiles.png`
  - Show `Edit Profiles` table and options including terrain source and coord mode.
- [ ] `images/wiki-menu-reference-edit-pvi.png`
  - Show `Edit PVI` table and generation options.

### CSV Format
- [ ] `images/wiki-csv-pointcloud-import-panel.png`
  - Show a valid point cloud CSV selected in the DEM import panel.
- [ ] `images/wiki-csv-alignment-import-result.png`
  - Show alignment CSV import result.
- [ ] `images/wiki-csv-dem-cellsize-tuning.png`
  - Show the DEM panel with `CellSize` highlighted or clearly visible.

### Troubleshooting
- [ ] `images/wiki-troubleshooting-eg-blank.png`
  - Show profile table rows with blank EG values.
- [ ] `images/wiki-troubleshooting-eg-blank-cellsize-fix.png`
  - Show DEM panel where a larger `CellSize` is used to improve coverage.
- [ ] `images/wiki-troubleshooting-daylight-settings.png`
  - Show `Daylight Auto` and terrain selection settings.
- [ ] `images/wiki-troubleshooting-corridor-twist.png`
  - Show a twisted corridor case with useful status text visible if possible.
- [ ] `images/wiki-troubleshooting-corridor-twist-fixed.png`
  - Show the same or similar area after stabilization settings are applied.
- [ ] `images/wiki-troubleshooting-workbench-icon.png`
  - Show the workbench selector area if icon troubleshooting is being documented.

## Capture Session Plan
Use this minimal sequence to gather most images in one run.

1. Create a new project.
2. Fill `Project Setup`.
3. Import the point cloud DEM and capture terrain-related images.
4. Import alignment and capture alignment images.
5. Generate stations and capture completion dialog.
6. Open `Edit Profiles`, fill EG, and capture profile images.
7. Open `Edit PVI`, generate FG, and capture PVI/FG images.
8. Generate 3D centerline, sections, and corridor.
9. Capture final result and any troubleshooting examples.

## After Capture
1. Save images to `docs/wiki/images/`.
2. Copy them to the wiki repo `images/` folder when publishing.
3. Replace remaining placeholder-only entries if the final screenshot now exists.
4. Check markdown image links before pushing.

## Completion Check
- [ ] All required file names exist in `docs/wiki/images/`
- [ ] The same files are copied to the wiki repo `images/`
- [ ] No screenshot is obviously outdated relative to the current UI
- [ ] Completion dialogs are visible where the wiki references them
- [ ] Menu option screenshots match the current task panel wording

---
Last verified with commit: `61ba6d5`
