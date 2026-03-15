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
2. They are not embedded inside the base section wire because that would break Corridor Loft point consistency.

> [Screenshot Needed] Alignment tree showing populated `Structure Sections`.
> Suggested file: `wiki-troubleshooting-structure-sections-tree.png`

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

## Corridor Loft is twisted or locally flipped
Symptoms:
- Corridor solid twists between nearby stations.
- Some corridor ranges look inverted or folded.
- Full loft fails, or only segmented fallback succeeds.

Checks:
1. Confirm `SectionSet` child sections look consistent from one station to the next.
2. Check whether the first failed area is near sharp horizontal geometry, sudden FG change, or daylight transition.
3. Check `Corridor Loft` status for `adaptive fallback used` and `autoFixed=<count>`.
4. Confirm `Auto-fix flipped sections` is enabled.
5. Confirm `Min Section Spacing` is not too small.

Actions:
1. Increase section interval in `Generate Sections`.
2. Increase `Corridor Loft > Min Section Spacing`.
3. Enable `Use ruled loft`.
4. Keep `Auto-fix flipped sections` enabled.
5. Reduce abrupt daylight changes with `Daylight Max Width Delta`.
6. Check profile data for long zero runs, missing EG, or sudden grade spikes.
7. If needed, temporarily disable daylight and confirm whether the base corridor is stable first.

Interpretation guide:
1. If `autoFixed=0` and loft still twists, the issue is usually abrupt section shape change rather than simple orientation reversal.
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
- For general user/developer questions, please ask in the CorridorRoad project thread on the FreeCAD Forum:
- https://forum.freecad.org/viewtopic.php?t=103783

---
Last verified with commit: `<fill-after-release>`
