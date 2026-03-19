<!-- SPDX-License-Identifier: LGPL-2.1-or-later -->
<!-- SPDX-FileNotice: Part of the Corridor Road addon. -->

# Developer Guide

This page is the quick technical map for contributors.

## Code Layout
- `freecad/Corridor_Road/init_gui.py`
- `freecad/Corridor_Road/commands/`
- `freecad/Corridor_Road/objects/`
- `freecad/Corridor_Road/ui/`

![High-level code map diagram or folder tree capture](images/wiki-dev-code-layout.png)


## Key Runtime Policy
- Terrain/design/cut-fill runtime uses DEM-style regular XY grid sampling.
- Daylight terrain source in section generation is mesh based.
- Coordinate handling uses project-level local/world transform policy.

## Main Objects
- `HorizontalAlignment`: horizontal geometry + key stations
- `Stationing`: station list generation
- `ProfileBundle` / `VerticalAlignment`: EG/FG data and vertical geometry
- `Centerline3DDisplay`: sampled centerline rendering
- `SectionSet`: station resolve + section generation + daylight
- `CorridorLoft`: corridor solid generation from sections
- `DesignTerrain` / `CutFillCalc`: grid sampling based terrain/analysis

Object link chain (typical):
`HorizontalAlignment -> Stationing -> ProfileBundle/VerticalAlignment -> Centerline3DDisplay -> SectionSet -> CorridorLoft -> DesignTerrain/CutFillCalc`

## Corridor Loft Stability Notes
- `SectionSet` keeps section frame continuity using previous normal direction.
- Daylight side-width changes are smoothed by `AssemblyTemplate.DaylightMaxWidthDelta`.
- `CorridorLoft.AutoFixSectionOrientation` tries to reverse section point order only when neighboring-section comparison strongly suggests a left/right flip.
- `CorridorLoft.AutoFixedSectionCount` reports how many sections were auto-corrected during build.
- If full loft still fails, adaptive segmented fallback is used and failed ranges are recorded in status.

Practical debugging order:
1. Inspect section wires before inspecting loft output.
2. Reduce section density before changing loft algorithm.
3. Separate base corridor issues from daylight-induced issues.
4. Use ruled loft during diagnosis, then relax settings if stable.

## UI Entry Points
- `cmd_new_project.py`
- `cmd_edit_alignment.py`
- `cmd_generate_stations.py`
- `cmd_generate_centerline3d.py`
- `cmd_generate_sections.py`
- `cmd_generate_corridor_loft.py`
- `cmd_import_pointcloud_dem.py`

## Completion Message Policy
- Stations, 3D Centerline, Sections, and Corridor Loft commands should show completion dialogs on successful run.
- Keep error behavior separate: warnings/errors should not show success dialogs.
- Include simple runtime summary in dialog where possible (count/status).

## Test Samples
- Point cloud: `tests/samples/pointcloud_utm_realistic_hilly.csv`
- Alignment: `tests/samples/alignment_utm_realistic_hilly.csv`

## Documentation Update Policy
1. If command behavior changes, update `README.md` and related wiki page together.
2. If CSV schema changes, update `CSV-Format.md` and sample files together.
3. Add `Last verified with commit` to changed wiki pages.

## Recommended Contribution Flow
1. Reproduce issue using sample files.
2. Patch command/object/ui with minimal scope.
3. Verify with real command flow in FreeCAD.
4. Update docs/wiki draft pages under `docs/wiki`.
5. Sync approved pages to GitHub Wiki repo.

## Debug Checklist For Field Issues
1. Capture command click path and timestamp.
2. Save report view/log message text.
3. Capture source object status fields before and after recompute.
4. Attach minimal CSV reproducer when possible.

---
Last verified with commit: `<fill-after-release>`
