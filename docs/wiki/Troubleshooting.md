# Troubleshooting

## Recommended diagnosis order
1. Confirm source object existence and links.
2. Confirm coordinate mode consistency (`Local`/`World`).
3. Confirm source geometry coverage (terrain/alignment overlap).
4. Re-run generation command and inspect status messages.

## EG values are blank or partially missing
Symptoms:
- EG column contains many empty rows at stations.

Checks:
1. Confirm alignment is inside terrain coverage.
2. Confirm terrain mesh is valid and has enough facets.
3. Confirm terrain coordinate mode (`Local`/`World`) matches project setup.

Actions:
1. Re-import terrain from dense point cloud CSV.
2. Move or regenerate alignment to stay in terrain range.
3. Regenerate stations and profiles.

> [Screenshot Needed] Profile table with EG blank rows example.
> Suggested file: `wiki-troubleshooting-eg-blank.png`

## Daylight Auto does not apply
Symptoms:
- `Daylight Auto` is checked but side slope does not meet terrain.

Checks:
1. Confirm `Daylight Terrain (Mesh)` is assigned.
2. Confirm section daylight terrain coordinate mode is correct.
3. Confirm terrain mesh has valid facets where sections are sampled.

Actions:
1. Set terrain mesh explicitly in Sections task panel.
2. Match terrain coordinates with terrain object output mode.
3. Regenerate sections after updating settings.

> [Screenshot Needed] Sections panel showing Daylight Auto and terrain selection.
> Suggested file: `wiki-troubleshooting-daylight-settings.png`

## Workbench icon not visible
Symptoms:
- Workbench appears in combo but icon is missing.

Checks:
1. Verify icon resource path in workbench registration.
2. Confirm icon file exists in addon resources.
3. Restart FreeCAD after addon update.

Actions:
1. Fix icon path in `init_gui.py`.
2. Reinstall or refresh addon resources.

> [Screenshot Needed] Workbench selector area with missing icon example.
> Suggested file: `wiki-troubleshooting-workbench-icon.png`

## Completion dialog does not appear
Symptoms:
- Generation completed but no completion popup is shown.

Checks:
1. Confirm command path is the task-panel button flow, not a custom script.
2. Confirm command did not fail before completion step.
3. Check FreeCAD report view for runtime exceptions.

Actions:
1. Retry with default sample data and standard workflow.
2. If reproducible, report command name and exact click path.

## Generate command does not produce expected object
Checks:
1. Confirm prerequisite object exists:
   - Stations requires Alignment
   - Sections requires Centerline3DDisplay and Assembly
   - Corridor Loft requires SectionSet
2. Check object `Status` property for warnings/errors.

Actions:
1. Run upstream commands in order from [Workflow](Workflow).
2. Recompute document and retry.
3. Recreate target object if stale link references remain.

## Where to report
- Open GitHub issue with:
  - FreeCAD version
  - CorridorRoad commit hash
  - Input CSV snippet
  - Error/status message text

---
Last verified with commit: `<fill-after-release>`
