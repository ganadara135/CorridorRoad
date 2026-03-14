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

> [Screenshot Needed] Project tree immediately after setup.
> Suggested file: `wiki-workflow-01-project-init.png`

## 2. Existing Terrain (EG)
1. Run `Point Cloud DEM`.
2. Load point cloud CSV (UTM or project coordinates).
3. Generate DEM mesh terrain.

Output:
- Mesh terrain object for EG sampling and daylight reference

Validation:
- Terrain mesh has valid facets.
- Terrain coverage encloses the intended alignment area.

> [Screenshot Needed] Point cloud DEM source and generated terrain mesh.
> Suggested file: `wiki-workflow-02-terrain-eg.png`

## 3. Horizontal Geometry
1. Open `Alignment`.
2. Import CSV or edit table (IP, radius, transition).
3. Apply alignment.

Output:
- Horizontal alignment with key stations

Validation:
- IP/radius/transition interpretation is correct.
- Alignment path is inside terrain bounds.

> [Screenshot Needed] Imported alignment geometry and key points.
> Suggested file: `wiki-workflow-03-horizontal-alignment.png`

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

> [Screenshot Needed] Stations and profile table with EG/FG columns.
> Suggested file: `wiki-workflow-04-stations-profiles.png`

## 5. 3D Centerline
1. Run `3D Centerline`.
2. Confirm sampled station count and wire in 3D view.

Output:
- Centerline3D display object

Validation:
- Completion popup appears.
- Sampled station count is non-zero and wire is visible.

> [Screenshot Needed] 3D centerline wire and completion popup.
> Suggested file: `wiki-workflow-05-centerline3d.png`

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

> [Screenshot Needed] Sections task panel and generated section set.
> Suggested file: `wiki-workflow-06-sections.png`

## 7. Corridor and Surfaces
1. Run `Generate Corridor Loft`.
2. Optionally run `Generate Design Grading Surface`.
3. Run `Generate Design Terrain`.
4. Run `Generate Cut/Fill Calc`.

Output:
- Corridor solid
- Design terrain mesh
- Cut/fill summary

Validation:
- Corridor loft status is OK.
- Design terrain/cut-fill status fields show no blocking error.

> [Screenshot Needed] Corridor loft + design terrain + cut/fill summary.
> Suggested file: `wiki-workflow-07-corridor-surfaces-analysis.png`

## 8. Quality Check
- Verify station coverage and EG values.
- Verify daylight intersections where required.
- Check status fields for warnings/errors on generated objects.
- Re-run failed stages after fixing source links or coordinate mode.

---
Last verified with commit: `<fill-after-release>`
