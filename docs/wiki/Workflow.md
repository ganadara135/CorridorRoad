# Workflow

This page describes the standard end-to-end CorridorRoad workflow.

## 1. Project Initialization
1. `New Project`
2. `Project Setup`

Output:
- Fixed project tree
- Design standard and coordinate setup

Validation:
- Project object links are initialized.
- Length scale and coordinate policy are confirmed before geometry creation.

![Screenshot Needed Project tree immediately after setup](images/wiki-workflow-01-project-init.png)

## 2. Existing Terrain (EG)
1. Run `Import PointCloud DEM`.
2. Load point cloud CSV (UTM or project coordinates).
3. Generate DEM mesh terrain.

Output:
- Mesh terrain object for EG sampling and daylight reference

Validation:
- Terrain mesh has valid facets.
- Terrain coverage encloses the intended alignment area.

![Point cloud DEM source and generated terrain mesh](images/wiki-workflow-02-terrain-eg.png)
![Point cloud DEM source and generated terrain mesh second](images/wiki-workflow-02-terrain-eg_2.png)

## 3. Horizontal Geometry
1. Open `Alignment`.
2. Import CSV or edit table (IP, radius, transition).
3. Apply alignment.

Output:
- Horizontal alignment with key stations

Validation:
- IP/radius/transition interpretation is correct.
- Alignment path is inside terrain bounds.

![Imported alignment geometry and key points](images/wiki-workflow-03-horizontal-alignment.png)
![Imported alignment geometry and key points](images/wiki-workflow-03-horizontal-alignment_2.png)

## 4. Stations and Profiles
1. `Generate Stations`
2. `Edit Profiles` for EG/FG data
3. `Edit PVI` for FG vertical geometry (optional)

Output:
- Stationing object
- Profile bundle and/or vertical alignment

Validation:
- Station list count is reasonable for interval.
- EG fill coverage is acceptable before FG generation.

![stations](images/wiki-workflow-04-stations-profiles.png)
![profile table with EG columns](images/wiki-workflow-04-stations-profiles_2.png)
![profile table with FG columns](images/wiki-workflow-04-stations-profiles_3.png)


## 5. 3D Centerline
1. Run `3D Centerline`.
2. Confirm sampled station count and wire in 3D view.

Output:
- Centerline3D display object

Validation:
- Completion popup appears.
- Sampled station count is non-zero and wire is visible.

[3D centerline wire and completion popup](images/wiki-workflow-05-centerline3d.png)


## 6. Sections
1. Run `Generate Sections`.
2. Choose mode (`Range` or `Manual`).
3. Configure daylight options if needed.
4. Click `Generate Sections Now`.

Output:
- SectionSet with resolved station list and optional child sections

Validation:
- Resolved station count matches mode/configuration.
- Daylight terrain is assigned when Daylight Auto is enabled.

![Sections task panel and generated section set](images/wiki-workflow-06-sections.png)
![Sections task panel and generated section set](images/wiki-workflow-06-sections_2.png)

## 7. Corridor and Surfaces
1. Run `Generate Corridor Loft`.
2. Optionally run `Generate Design Grading Surface`.
3. Optionally run `Generate Design Terrain`.
4. Run `Generate Cut/Fill Calc`.

Output:
- Corridor solid
- Design terrain mesh
- Cut/fill summary

Validation:
- Corridor loft status is OK.
- Design terrain/cut-fill status fields show no blocking error.

## 7A. How To Reduce Corridor Loft Twisting

Corridor loft twisting usually happens when neighboring sections change too abruptly or when section left/right orientation becomes inconsistent between stations.

Recommended settings and workflow:
1. Keep section spacing practical.
2. Avoid very small section interval unless the geometry truly needs it.
3. Increase `Corridor Loft > Min Section Spacing` if many sections are nearly overlapping.
4. Turn on `Use ruled loft` first when testing unstable geometry.
5. Keep `Auto-fix flipped sections` enabled in Corridor Loft.

Daylight-related guidance:
1. If `Daylight Auto` is enabled, avoid large jumps in daylight width between neighboring sections.
2. Use `Daylight Max Width Delta` in the Sections panel to smooth daylight-width changes.
3. If terrain is noisy or sparse, reduce dependence on aggressive daylight behavior until the base corridor is stable.

Profile and section quality guidance:
1. Check that EG/FG/profile data does not contain large zero-value runs or unexpected spikes.
2. Confirm the alignment stays inside terrain coverage.
3. Review child sections in the tree to find the first station where the shape looks reversed or jumps sharply.

Practical order of stabilization:
1. Increase section interval slightly.
2. Increase `Min Section Spacing`.
3. Enable `Use ruled loft`.
4. Keep `Auto-fix flipped sections` enabled.
5. Reduce daylight aggressiveness with `Daylight Max Width Delta`.

What the current code already does:
1. Stabilizes section normal continuity across stations.
2. Smooths daylight width changes using `Daylight Max Width Delta`.
3. Auto-fixes likely flipped section orientation in Corridor Loft when enabled.
4. Falls back to adaptive segmented loft if full loft fails.

> [Screenshot Needed] Corridor Loft options showing `Min Section Spacing`, `Use ruled loft`, and `Auto-fix flipped sections`.
> Suggested file: `wiki-workflow-07a-corridor-loft-stability-options.png`

> [Screenshot Needed] Sections options showing `Daylight Max Width Delta`.
> Suggested file: `wiki-workflow-07b-daylight-max-width-delta.png`

![Corridor loft, failed case](images/wiki-workflow-07-corridor-surfaces-analysis.png)
- this is a failed case. check your profile data. there would be many zero data.
![Corridor loft](images/wiki-workflow-07-corridor-surfaces-analysis_2.png)
![Cut and Fill Analisys](images/wiki-workflow-07-corridor-surfaces-analysis_3.png)


## 8. Quality Check
- Verify station coverage and EG values.
- Verify daylight intersections where required.
- Check status fields for warnings/errors on generated objects.
- Re-run failed stages after fixing source links or coordinate mode.

---
Last verified with commit: `<fill-after-release>`
