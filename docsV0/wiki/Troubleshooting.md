<!-- SPDX-License-Identifier: LGPL-2.1-or-later -->
<!-- SPDX-FileNotice: Part of the Corridor Road addon. -->

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
4. If the source point cloud is sparse, regenerate the DEM with a larger `CellSize`.
5. After changing `CellSize`, rebuild terrain first, then regenerate profile-related objects.

Why larger `CellSize` can help:
1. A very small DEM cell size preserves detail, but it also exposes sparse gaps in the source point cloud.
2. Those gaps can produce weak DEM coverage, which later appears as blank or `0` EG/profile values at some stations.
3. A moderately larger `CellSize` samples the terrain more coarsely and can reduce those gaps.
4. The tradeoff is that overly large cells can flatten terrain detail, so increase gradually rather than jumping to a very large value.

> [Screenshot Needed] Profile table with EG blank rows example.
> Suggested file: `wiki-troubleshooting-eg-blank.png`

> [Screenshot Needed] DEM import panel with larger `CellSize` used to improve EG coverage.
> Suggested file: `wiki-troubleshooting-eg-blank-cellsize-fix.png`

## DEM cell size tuning
Use DEM cell-size adjustment when terrain coverage is unstable, but the input coordinates and terrain extent are otherwise correct.

Increase `CellSize` when:
1. The point cloud is sparse or irregularly spaced.
2. Profile EG repeatedly shows blank rows or `0` values.
3. The terrain mesh contains many small holes or disconnected-looking areas.

Do not increase `CellSize` blindly when:
1. The alignment is outside terrain coverage.
2. Coordinate mode is mismatched.
3. The terrain object itself failed to generate valid facets.

Recommended tuning workflow:
1. Confirm the problem is not caused by extent or coordinate mismatch.
2. Increase DEM `CellSize` by a modest step.
3. Rebuild the terrain mesh.
4. Regenerate profiles and compare EG coverage.
5. Repeat only until coverage becomes acceptable.

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

## Structure overlays do not appear
Symptoms:
- `Edit Structures` completed, but no station-based structure overlays are visible.
- `Structure Sections` folder is missing or empty.

Checks:
1. Confirm `Generate Stations` was run before `Edit Structures`.
2. Confirm `Generate Sections` was run with `Use linked StructureSet` enabled.
3. Confirm structure station ranges fall inside the current section generation range.
4. Confirm structure rows have positive `Width` and `Height`.
5. Confirm the relevant structure rows are not all `tag_only` if you expected override-driven section behavior.

Actions:
1. Re-open `Edit Structures` and verify the `StructureSet` rows.
2. Re-run `Generate Sections`.
3. Check the project tree under `02_Alignments/.../Structure Sections`.
4. If necessary, increase the visible section range or include structure start/end/center stations explicitly.

Notes:
1. Structure overlays are shown in a separate `Structure Sections` folder on purpose.
2. They are not embedded inside the base section wire because that would break Corridor point consistency.

> [Screenshot Needed] Alignment tree showing populated `Structure Sections`.
> Suggested file: `wiki-troubleshooting-structure-sections-tree.png`

## External shape falls back to a box
Symptoms:
- An `external_shape` row shows only a simple box in 3D.
- `Apply` reports external shape diagnostics.

Checks:
1. Confirm `GeometryMode=external_shape`.
2. Confirm `ShapeSourcePath` points to a real local file.
3. If using `FCStd`, confirm the path uses `C:/path/model.FCStd#ObjectName`.
4. Confirm the referenced FCStd object has a valid `Shape`.

Actions:
1. Use the `ShapeSourcePath` cell color and `External shape row` status text in `Edit Structures`.
2. Re-apply and read the reported status:
   - `not_found`
   - `fcstd_missing_object`
   - `fcstd_object_not_found`
   - `fcstd_missing_shape`
3. Fix the path/object name and apply again.

## Edit Structures shows warnings before Apply
Symptoms:
- The upper table shows tinted rows.
- The validation summary reports warnings or errors before `Apply`.

Interpretation:
1. This is expected and is now part of the workflow.
2. The panel performs first-pass checks on structure type, station order, corridor recommendations, external-shape paths, and station-profile consistency.

Actions:
1. Select the row and read `Selected Structure Details`.
2. Read the first validation message shown in the summary card.
3. Use grouped columns or the details panel to fix the relevant fields.
4. If the issue is profile-related, use the lower table tools:
   - `Sort by Station`
   - `Duplicate Profile Row`
   - `Add Midpoint`
   - `Delete All for Selected`

## External shape is visible, but earthwork does not match it
Symptoms:
- A complex STEP/BREP/FCStd structure is displayed correctly in 3D.
- Sections, grading, or corridor earthwork still follow a simplified culvert / retaining wall / abutment rule.

Interpretation:
1. This is the current intended behavior.
2. `external_shape` is used for display/reference placement.
3. Earthwork is still generated from structure `Type` and basic metadata such as `Width`, `Height`, `BehaviorMode`, and `CorridorMode`.

Actions:
1. Set the correct structure `Type` first, because that still controls current earthwork behavior.
2. Use realistic `Width` and `Height` values even when the actual 3D source comes from `external_shape`.
3. Treat the imported external solid as a reference model until direct shape-based earthwork consumption is implemented.

## Structure 3D solid is on alignment instead of 3D centerline
Symptoms:
- Structure section overlays look correct, but the 3D structure solid appears to sit on the alignment frame instead of the 3D centerline frame.

Checks:
1. Confirm `3D Centerline` was generated after the latest alignment/profile changes.
2. Re-open `Edit Structures` and click `Apply` again.
3. Read `Frame diagnostics` in the completion dialog.

Actions:
1. Re-run `3D Centerline`.
2. Re-apply the `StructureSet`.
3. If the dialog still reports `frame source=alignment`, inspect whether the current project actually has a linked `Centerline3DDisplay`.

## Structure override changes only one side
Symptoms:
- A retaining wall or side-specific structure affects only the left or right side of the section.

Interpretation:
1. This is expected for `retaining_wall` when `Side` is `left` or `right`.
2. The current override policy keeps the opposite side as normal when possible.
3. Zone-type structures such as `culvert`, `crossing`, `bridge_zone`, and `abutment_zone` affect both sides more conservatively.

Action:
1. Check the structure `Type`.
2. Check the structure `Side`.
3. If you only need tagging and overlays, change `BehaviorMode` to `tag_only`.

## Structure boundary still changes too abruptly
Symptoms:
- The section shape looks too sudden at the structure entry or exit even though transition stations are enabled.

Checks:
1. Confirm `Include transition stations` is enabled.
2. Confirm `Auto transition distance` is enabled first.
3. Review the structure `Width` and `Height`; auto transition uses those values as part of its sizing rule.

Actions:
1. Keep `Auto transition distance` on for mixed structure types.
2. If one specific structure still changes too abruptly, either:
   - increase its representative `Width`/`Height` if the current values are too small, or
   - turn off auto mode and use a larger manual `Transition Distance`.
3. Regenerate sections and rebuild the corridor after changing the transition policy.

Interpretation:
1. `retaining_wall` uses a shorter auto transition than `culvert` or `bridge_zone`.
2. `bridge_zone` and `abutment_zone` use longer transition distances by design.

## 3D centerline wire looks zig-zag or wiggly
Symptoms:
- The generated 3D centerline looks segmented, zig-zag, or slightly unstable while zooming or panning.
- Users may suspect the station-based corridor geometry itself is inaccurate.

Interpretation:
1. This is typically a display-side geometry/rendering issue, sometimes amplified by large world-coordinate values.
2. The station-based engineering logic does not use the rendered wire as the design source of truth.
3. Sections, structure frames, and corridor generation still evaluate the underlying alignment/profile model at stations.
4. CorridorRoad already supports project-level world/local transforms (`Project Origin`, `Local Origin`, `North Rotation`) so world-coordinate workflows can be normalized into local model space.
5. The recent visible zig-zag issue was addressed primarily by changing the visible 3D centerline from a polyline-style wire to a spline-based wire.

Actions:
1. Treat the visible wire as a display guide, not as the final proof of engineering smoothness.
2. Confirm `Project Setup` is using a sensible local/world anchor when the source data comes in world coordinates.
3. Rebuild `3D Centerline` and confirm the active wire mode is `SmoothSpline`.
4. Use `Polyline` only when you want a debug/comparison view of the visible wire build.
5. If section/corridor output is numerically and station-wise correct, do not treat visible wire roughness alone as a design failure.
6. If the wire is split more often than expected, inspect the task-panel `Split Sources` summary before assuming a geometry error. Region/structure semantic splits are display-side by design.

## Region Plan rows are hard to read in dark theme
Symptoms:
- `Manage Regions` shows pale or tinted rows but the cell text is hard to read.
- `Station Timeline`, `Base Regions`, `Overrides`, or `Hints` look washed out after switching FreeCAD theme.

Checks:
1. Confirm the panel was opened after the current FreeCAD theme was already active.
2. Confirm the problem is in the grouped workflow tables, not a screenshot viewer or external image viewer.
3. Confirm the issue persists after closing and reopening `Manage Regions`.

Actions:
1. Reopen `Manage Regions` so row tinting is rebuilt from the current Qt palette.
2. Keep FreeCAD on a normal dark or light application palette rather than a partially mixed custom palette if possible.
3. If the issue still persists, report which table is affected:
   - `Station Timeline`
   - `Base Regions`
   - `Overrides`
   - `Hints`

Interpretation:
1. Current row tinting is palette-aware and should keep readable text in both light and dark themes.
2. If text is still unreadable, the issue is likely a theme-specific palette/style conflict rather than missing row data.

## Region Plan changes do not affect generated sections
Symptoms:
- `Manage Regions` looks correct, but `Generate Sections` output does not reflect region boundaries or overrides.

Checks:
1. Confirm `Use linked Region Plan` is enabled in `Generate Sections`.
2. Confirm the intended `Region Plan Source` is selected.
3. Confirm the relevant rows are accepted/enabled:
   - base rows enabled
   - override rows enabled
   - hints accepted if they are meant to become design data
4. Confirm `Include region boundaries` and `Include region transitions` are enabled when extra sampling stations are expected.
5. Confirm `Apply region overrides` is enabled when section behavior, not just station density, should change.

Actions:
1. Re-run `Generate Sections` with the correct region source selected.
2. Accept pending hints before expecting them to affect section output.
3. Check `SectionSet.Status` for region-related warnings or missing-source messages.
4. Verify the expected stations appear in the generated child section list.

## Corridor is twisted or locally flipped
Symptoms:
- Corridor surface twists between nearby stations.
- Some corridor ranges look inverted or folded.
- Full corridor build fails, or only segmented fallback succeeds.
- `Design Grading Surface` looks section-faithful, but `Corridor` looks more distorted or span-driven.

Checks:
1. Confirm `SectionSet` child sections look consistent from one station to the next.
2. Compare against `Design Grading Surface` first. If grading looks correct, the problem is likely in `Corridor` range/shape handling rather than the raw section contract.
3. Check whether the first failed area is near sharp horizontal geometry, sudden FG change, daylight transition, or structure-aware corridor spans.
4. Check `Corridor` status for `adaptive fallback used` and `autoFixed=<count>`.
5. Confirm `Auto-fix flipped sections` is enabled.
6. Confirm `Min Section Spacing` is not too small.

Interpretation:
1. `Design Grading Surface` is the reference for raw section connectivity because it connects neighboring section points directly.
2. `Corridor` should still follow that same ordered section-point contract.
3. If `Corridor` looks more span-driven, folded, or differently mapped while grading looks correct, suspect corridor packaging or connectivity drift inside `Corridor`, not a different intended design result.

Actions:
1. Increase section interval in `Generate Sections`.
2. Increase `Corridor > Min Section Spacing`.
3. Enable `Use ruled surface`.
4. Keep `Auto-fix flipped sections` enabled.
5. Reduce abrupt daylight changes with `Daylight Max Width Delta`.
6. Check profile data for long zero runs, missing EG, or sudden grade spikes.
7. If needed, temporarily disable daylight and confirm whether the base corridor is stable first.

Interpretation guide:
1. If `autoFixed=0` and the corridor still twists, the issue is usually abrupt section shape change rather than simple orientation reversal.
2. If `autoFixed` is high, inspect the related section range because left/right orientation may be unstable there.
3. If only daylight-enabled runs fail, focus on terrain coverage, terrain noise, and daylight width smoothing.

> [Screenshot Needed] Twisted corridor example with status text visible.
> Suggested file: `wiki-troubleshooting-corridor-twist.png`

> [Screenshot Needed] Stable corridor result after spacing/orientation/daylight adjustments.
> Suggested file: `wiki-troubleshooting-corridor-twist-fixed.png`

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
   - Corridor requires SectionSet
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
- For general user/developer questions, please ask in the CorridorRoad project thread on the FreeCAD Forum:
- https://forum.freecad.org/viewtopic.php?t=103783

---
Last verified with commit: `61ba6d5`
