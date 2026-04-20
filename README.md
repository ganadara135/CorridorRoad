<!-- SPDX-License-Identifier: LGPL-2.1-or-later -->
<!-- SPDX-FileNotice: Part of the Corridor Road addon. -->

# CorridorRoad

CorridorRoad is a FreeCAD workbench for corridor style road design.
It covers a practical pipeline from alignment to sections, corridor geometry, design terrain, and cut/fill analysis.

## What This Project Does
- Provides an end-to-end road design workflow:
  - Terrain (EG) -> Horizontal Alignment -> Stationing -> Profiles/PVI -> Centerline3D
  - Assembly -> Sections -> Corridor Loft -> Design Terrain -> Cut/Fill
- Enforces a fixed Civil3D-style project tree schema with automatic object routing.
- Keeps object links and recompute flow organized under a project container.
- Uses a project-level local/world coordinate transform policy so world-coordinate inputs can be normalized into local engineering model space.

## Wiki Documentation
- Online Wiki: https://github.com/ganadara135/CorridorRoad/wiki
- Wiki draft source in this repo: `docs/wiki/`
- Wiki page map: `docs/wiki/WIKI_TOC.md`
- Mixed workflow support/validation matrix: `docs/MIXED_WORKFLOW_VALIDATION_MATRIX.md`
- Main wiki pages:
1. Home: https://github.com/ganadara135/CorridorRoad/wiki
2. Quick Start: https://github.com/ganadara135/CorridorRoad/wiki/Quick-Start
3. Workflow: https://github.com/ganadara135/CorridorRoad/wiki/Workflow
4. CSV Format: https://github.com/ganadara135/CorridorRoad/wiki/CSV-Format
5. Troubleshooting: https://github.com/ganadara135/CorridorRoad/wiki/Troubleshooting
6. Developer Guide: https://github.com/ganadara135/CorridorRoad/wiki/Developer-Guide

## Questions And Support
- If general users or developers have questions about this project, please ask in the CorridorRoad project thread on the FreeCAD Forum: https://forum.freecad.org/viewtopic.php?t=103783
- Use the project thread for workflow questions, bug reports, usage problems, and development discussion.

## Latest Release
- Current stable release: `v0.2.7`
- GitHub Release: https://github.com/ganadara135/CorridorRoad/releases/tag/v0.2.7

## Main Commands
- `New Project`
- `Project Setup`
- `Sample Alignment`
- `Edit Alignment`
- `Generate Stations`
- `Edit Profiles`
- `Edit PVI`
- `3D Centerline`
- `Typical Section`
- `Edit Structure`
- `Sections`
- `Cross Section Viewer`
- `Build Corridor`
- `Generate Design Grading Surface`
- `Generate Design Terrain`
- `Generate Cut/Fill Calc`

`Cross Section Viewer` reviews generated `SectionSet` stations in a dedicated 2D panel with component, side-slope, daylight, and export support.

## Fixed Project Tree Schema
- `CorridorRoad Project`
- `01_Inputs/{Terrains,Survey,Structures}`
- `02_Alignments/ALN_<Name>/{Horizontal,Stationing,VerticalProfiles,3D Centerline,Assembly,Regions,Sections,Structure Sections,Corridor}`
- `03_Surfaces`
- `04_Analysis`
- `05_References` (optional)

## Current Key Policies
- SectionSet daylight terrain source is `Mesh only`.
- Project Setup is opened from the project context menu.
- Project Setup stores both world origin and local origin:
  - `Project Origin E/N/Z`
  - `Local Origin X/Y/Z`
  - `North Rotation`
- World-coordinate workflows are intended to convert into project-local model space as early as possible, instead of carrying large global coordinates through the full modeling/display pipeline.
- `Project Setup` now stores a `Coordinate Workflow` recommendation:
  - `World-first`
  - `Local-first`
  - `Custom`
- Recommended default behavior:
  - if `CRS / EPSG` is set, workflow defaults to `World-first`
  - if `CRS / EPSG` is blank, workflow defaults to `Local-first`
- When `Auto-apply recommended modes in task panels` is enabled, input panels such as `Import PointCloud DEM`, `Alignment`, `Edit Profiles`, `Generate Sections`, `Design Terrain`, and `Cut/Fill Calc` use that workflow as their initial coordinate-mode recommendation.
- `Alignment` now supports built-in presets for quick starts:
  - `Simple Tangent`
  - `Single Curve`
  - `S-C-S Curve`
  - `Reverse Curve`
  - `Sample Local Alignment`
- Alignment presets are authored as local-pattern rows.
- If `Alignment` is currently in `World (E/N)` mode, `Load Preset` converts those local preset rows to world coordinates using the active `Project Setup`.
- `DesignTerrain`/`CutFillCalc` runtime sampling uses a DEM-style regular XY grid (`CellSize` based), with per-cell elevation queried from source mesh triangles.
- `3D Centerline` is a display object (`Centerline3DDisplay`) and is not the engineering source of truth for section/corridor evaluation.
- Current 3D centerline display policy:
  - default visible wire mode is `SmoothSpline`
  - `Polyline` remains available as a debug/comparison mode
  - semantic boundary markers may be shown for regions/structures without breaking the main wire into tree-level segment objects
- The recent visible zig-zag / wiggly 3D centerline issue was addressed on the display side by switching the visible line build from a polyline-style representation to a spline-based representation, while keeping station-based engineering logic unchanged.

## Release And Versioning Policy
- Addon listing remains branch-based.
- The catalog should continue to track the stable branch, not individual release tags.
- Recommended branch roles:
  - `ganada` = ongoing development branch
  - `main` = release/stable branch
- Release procedure:
  1. continue feature work on `ganada`
  2. when a release is ready, merge or squash `ganada` into `main`
  3. update `package.xml` version on `main`
  4. update `CHANGELOG.md` on `main`
  5. create an annotated Git tag from `main`
  6. create the GitHub Release from that tag
- Recommended tag naming:
  - `vX.Y.Z`
  - example: `v0.6.0`
- Important note:
  - if addon listing stays branch-based, each new release does not require changing the catalog just because a new tag/release was created
  - a catalog PR is only needed when repository/branch/subdirectory tracking changes

## Sample Test Data
- Use the following files for realistic practical-workflow testing.
- The maintained sample inventory and scenario bundles are documented in [PRACTICAL_SAMPLE_SET.md](/c:/Users/ganad/AppData/Roaming/FreeCAD/Mod/CorridorRoad/docs/PRACTICAL_SAMPLE_SET.md).
- `tests/samples/pointcloud_utm_realistic_hilly.csv`
- `tests/samples/alignment_utm_realistic_hilly.csv`
- `tests/samples/profile_fg_manual_import_basic.csv`
- `tests/samples/profile_fg_manual_import_aliases.csv`
- `tests/samples/structure_utm_realistic_hilly.csv`
- `tests/samples/structure_utm_realistic_hilly_notch.csv`
- `tests/samples/structure_utm_realistic_hilly_template.csv`
- `tests/samples/structure_utm_realistic_hilly_external_shape.csv`
- `tests/samples/structure_utm_realistic_hilly_station_profile_headers.csv`
- `tests/samples/structure_utm_realistic_hilly_station_profile_points.csv`
- `tests/samples/structure_utm_realistic_hilly_mixed.csv`
- `tests/samples/structure_utm_realistic_hilly_mixed_profile_points.csv`
- `tests/samples/typical_section_basic_rural.csv`
- `tests/samples/typical_section_urban_complete_street.csv`
- `tests/samples/typical_section_with_ditch.csv`
- `tests/samples/typical_section_pavement_basic.csv`
1. Import `pointcloud_utm_realistic_hilly.csv` as DEM terrain source.
2. Import `alignment_utm_realistic_hilly.csv` as horizontal alignment.
3. After `Generate Stations`, use `profile_fg_manual_import_basic.csv` or `profile_fg_manual_import_aliases.csv` in `Edit Profiles -> Import FG CSV` when you want a manual FG starting point without `Edit PVI`.
4. After `Generate Stations`, load `structure_utm_realistic_hilly.csv` in `Edit Structures`.
5. Run sections and verify `Structure Sections` tree objects, EG coverage, and daylight behavior.
6. Build `Corridor Loft` with `Use structure corridor modes` enabled to test `skip_zone` handling from the same structure CSV.
7. Load `structure_utm_realistic_hilly_template.csv` when you want to test template structure display (`box_culvert`, `retaining_wall`) and template-aware `Structure Sections` overlays.
8. Load `structure_utm_realistic_hilly_external_shape.csv` when you want to test `GeometryMode=external_shape`. Replace the sample `ShapeSourcePath` values with your own local `.step`, `.brep`, or `.FCStd#ObjectName` sources first.
9. Use the `station_profile_headers` + `station_profile_points` samples when you want to test variable-size structures driven by station control points.
10. Use the `mixed` + `mixed_profile_points` samples when you want one combined test set that includes `culvert`, `crossing`, `retaining_wall`, `abutment_zone`, `bridge_zone`, `other`, and one `external_shape` placeholder row.
11. Use `typical_section_basic_rural.csv` when you want a simple lane + shoulder test for `Typical Section`.
12. Use `typical_section_urban_complete_street.csv` when you want an urban test with `median`, `bike_lane`, `curb`, `sidewalk`, and `green_strip`.
13. Use `typical_section_with_ditch.csv` when you want to test `gutter`, `ditch`, and `berm` in both `Sections` and `Corridor Loft`.
14. Use `typical_section_pavement_basic.csv` when you want to test the first-pass pavement layer stack for `Typical Section`.
15. Use `typical_section_ditch_v.csv`, `typical_section_ditch_trapezoid.csv`, and `typical_section_ditch_u.csv` when you want focused ditch-shape samples for `Typical Section`.
16. For the maintained Long-Term practical regression bundle, run `tests/regression/run_practical_scope_smokes.ps1`.

## Typical Section CSV
- `Typical Section` now supports direct CSV import through `Browse CSV` -> `Load CSV`.
- The panel now also supports:
  - `Load Preset`
  - roadside helper buttons such as `Add Rural Ditch Pair` and `Add Urban Edge Pair`
  - `Move Up`, `Move Down`
  - `Mirror Left -> Right`, `Mirror Right -> Left`
  - `Save Component CSV`, `Save Pavement CSV`
  - `Refresh Preview` for 3D live preview updates
  - `Show Preview Wire` / `Show PavementDisplay` preview visibility toggles
  - a live `Summary` panel for component count, top width, edge types, and pavement total
- Current CSV columns:
  - `Id`
  - `Type`
  - `Shape`
  - `Side`
  - `Width`
  - `CrossSlopePct`
  - `Height`
  - `ExtraWidth`
  - `BackSlopePct`
  - `Offset`
  - `Order`
  - `Enabled`
- Current sample files:
  - `tests/samples/typical_section_basic_rural.csv`
  - `tests/samples/typical_section_ditch_trapezoid.csv`
  - `tests/samples/typical_section_ditch_u.csv`
  - `tests/samples/typical_section_ditch_v.csv`
  - `tests/samples/typical_section_urban_complete_street.csv`
  - `tests/samples/typical_section_with_ditch.csv`
  - `tests/samples/typical_section_pavement_basic.csv`
- `Typical Section` also supports pavement-layer CSV import through `Browse Pavement CSV` -> `Load Pavement CSV`.
- Pavement CSV columns:
  - `Id`
  - `Type`
  - `Thickness`
  - `Enabled`
- Editing notes:
  - `Shape` is currently used by `ditch`; leave it blank for other component types
  - `lane`, `shoulder`, `median`, `sidewalk`, `bike_lane`, `green_strip`, and `gutter` emphasize `CrossSlopePct`
  - `curb` uses `Height` for curb rise, `Width` for top width, `ExtraWidth` for face/gutter run, and `BackSlopePct` for the top/back slope
  - `ditch` uses `Shape=v` for a V-bottom ditch, `Shape=trapezoid` for a flat-bottom/open trapezoid ditch, and `Shape=u` for a rounded U-like ditch
  - `ditch Shape=u` is currently generated as a stable polyline approximation and ignores `ExtraWidth` / `BackSlopePct`
  - if `ditch` `Shape` is blank, runtime infers `v` when `ExtraWidth <= 0` and `trapezoid` when `ExtraWidth > 0`
  - `ditch` uses `Width` for total span, `Height` for depth, `ExtraWidth` for flat bottom width, and `BackSlopePct` for the outer-side slope
  - `Sections`, `Cross Section Viewer`, and report rows now preserve ditch `Shape` on station-local component segments, so focused ditch modes stay readable downstream
  - `berm` uses `Width` for bench width and can extend with `ExtraWidth` + `BackSlopePct` for an outer taper
  - `bench` is reserved for future earthwork mid-slope benching terminology
- Current runtime intent:
  - `Typical Section Template` defines the finished-grade top profile.
  - `AssemblyTemplate` still provides corridor depth, side slopes, and daylight defaults.
  - `Sections` reports `schema=2` and `topProfile=typical_section` when a typical section drives the top profile.
  - `TypicalSectionPavementDisplay` now acts as the first separate pavement geometry/report object, with enabled layer ids, layer types, thicknesses, and summary rows.
  - `Sections`, `Design Grading Surface`, and `Corridor Loft` now carry `PavementTotalThickness`, pavement layer report rows, and advanced-component counts.
  - Status text now surfaces `typicalAdvanced=...` and `pavLayers=...` when a richer typical section is active.
  - `Corridor Loft` completion/status now reports `Points per section`, `Source section schema`, `Top profile source`, pavement layer counts, and advanced typical-component counts.
- Execution-plan/status reference:
  - `docs/TYPICAL_SECTION_EXECUTION_PLAN.md`

## Template Structures
- `Edit Structures` now supports `GeometryMode=box|template`.
- Current template types:
  - `box_culvert`
  - `retaining_wall`
- Template fields currently supported:
  - `TemplateName`
  - `WallThickness`
  - `FootingWidth`
  - `FootingThickness`
  - `CapHeight`
  - `CellCount`
- Use `tests/samples/structure_utm_realistic_hilly_template.csv` to test the current template workflow.
- Existing rows with no `GeometryMode` still fall back to simple `box` geometry for backward compatibility.

## External Shape Structures
- `Edit Structures` now also supports `GeometryMode=external_shape`.
- Current first-pass supported source formats:
  - `.step`, `.stp`
  - `.brep`, `.brp`
  - `.FCStd#ObjectName`
- New external-shape fields:
  - `ShapeSourcePath`
  - `ScaleFactor`
  - `PlacementMode`
  - `UseSourceBaseAsBottom`
- Use `tests/samples/structure_utm_realistic_hilly_external_shape.csv` as the starter CSV.
- For `FCStd`, use `ShapeSourcePath` in the form `C:/path/model.FCStd#ObjectName`.
- A practical workflow for `FCStd` is:
  1. `Browse Shape` to select the `.FCStd` file
  2. `Pick FCStd Object` to choose the internal shape-bearing object
- The sample file contains placeholder paths. Replace them with real local model files and object names before `Apply`.
- If an external source cannot be loaded, the row falls back to safe `box` display geometry instead of breaking recompute.
- Earthwork note:
  - `GeometryMode=external_shape` currently improves structure display and reference placement.
  - `Sections`, `Design Grading Surface`, and `Corridor Loft` can now consume an indirect bounding-box proxy from the imported shape when the source loads successfully.
  - Earthwork is still driven by structure `Type`, `BehaviorMode`, `CorridorMode`, and simplified dimensions; the imported shape only contributes that bounded proxy envelope.
  - The imported `STEP` / `BREP` / `FCStd` solid is not yet consumed directly as the earthwork-cutting shape.
  - Explicit station-profile values still override the indirect proxy when they are present.
- Current type-driven earthwork intent:
  - `culvert`, `crossing` -> notch / flat side-segment crossing rules
  - `retaining_wall` -> one-side retaining-wall section rule
  - `bridge_zone`, `abutment_zone` -> trim / split / skip rules

## Station-Profile Structures
- `StructureSet` now also supports optional station-profile control-point data for variable-size structures.
- Current station-profile fields:
  - `StructureId`
  - `Station`
  - `Offset`
  - `Width`
  - `Height`
  - `BottomElevation`
  - `Cover`
  - `WallThickness`
  - `FootingWidth`
  - `FootingThickness`
  - `CapHeight`
  - `CellCount`
- Current implementation scope:
  - 3D structure display uses station-profile values
  - `Structure Sections` overlays use station-profile values
  - section overrides / earthwork use station-profile values
  - corridor notch handling uses station-profile values
- Current user-flow note:
  - `Edit Structures` now provides a second table for station-profile rows
  - load the base header CSV first, then load the profile CSV
  - selecting a structure in the upper table filters the lower table to that structure's profile rows
  - the upper table now defaults to a compact `Basic` column view, while `Selected Structure Details` handles advanced fields
  - use `Columns: Template / External Shape / Advanced` when you want to temporarily reveal grouped columns in the upper table
  - use `Add Common Structure`, `Clone Selected`, and the built-in structure `Preset` loader for faster setup
  - the lower profile table now supports `Sort by Station`, `Duplicate Profile Row`, `Add Midpoint`, and `Delete All for Selected`
  - row validation is shown directly in the upper table, and the panel now reports an overall validation summary
  - use `tests/samples/structure_utm_realistic_hilly_station_profile_headers.csv` and `tests/samples/structure_utm_realistic_hilly_station_profile_points.csv` for focused testing
  - use `tests/samples/structure_utm_realistic_hilly_mixed.csv` and `tests/samples/structure_utm_realistic_hilly_mixed_profile_points.csv` for combined multi-structure testing

## Loft Twist Reduction Tips
- If `Corridor Loft` twists or folds, first increase section interval and `Min Section Spacing`.
- Turn on `Use ruled loft` and keep `Auto-fix flipped sections` enabled.
- If structures are active in sections, keep `Split at structure zones` enabled so the loft can break at structure boundaries instead of forcing one continuous span.
- Keep `Auto transition distance` enabled in structure-aware sections unless you have a clear reason to force one manual distance for all structure types.
- Current structure override intent: `culvert/crossing` create short flat berm-like side sections, `retaining_wall` creates a short steep wall-side section, and `bridge/abutment` zones trim both sides conservatively.
- For corridor-level structure handling, use `split_only` first, `skip_zone` only when a full gap is intended, and `notch` mainly for `culvert` / `crossing` when the corridor should stay continuous and use a notch-aware loft profile.
- Current `notch` behavior is not just a visual boolean cut. When possible it switches the loft to a notch-aware closed-profile schema and ramps the notch through transition stations.
- Recommended user policy:
  - `culvert`, `crossing` -> `notch`
  - `bridge_zone`, `abutment_zone` -> `skip_zone`
  - `retaining_wall` -> `split_only`
- If `Daylight Auto` is used, reduce abrupt side-width changes with `Daylight Max Width Delta`.
- Check section wires first: unstable EG/FG data, terrain holes, or sudden daylight jumps usually appear there before the loft fails.
- Detailed guidance: https://github.com/ganadara135/CorridorRoad/wiki/Workflow and https://github.com/ganadara135/CorridorRoad/wiki/Troubleshooting

## Code Layout
- `freecad/Corridor_Road/commands/`: command entry points (toolbar/menu actions)
- `freecad/Corridor_Road/objects/`: parametric object logic
- `freecad/Corridor_Road/ui/`: TaskPanel UI
- `freecad/Corridor_Road/init_gui.py`: main workbench registration and command loading

## Good Entry Points For Developers
- `freecad/Corridor_Road/init_gui.py`
- `freecad/Corridor_Road/objects/obj_project.py`
- `freecad/Corridor_Road/objects/obj_section_set.py`
- `freecad/Corridor_Road/ui/task_section_generator.py`
- `freecad/Corridor_Road/commands/cmd_*.py`

## Development Environment
- OS: `Windows 11`
- FreeCAD: `1.0.2`

## Install and Run
1. Place this folder under your FreeCAD `Mod` directory.
2. Restart FreeCAD.
3. Select the `CorridorRoad` workbench.

## License
- This project is licensed under `LGPL-2.1-or-later`.
- See [LICENSE](./LICENSE).

## Video
- https://youtu.be/P0kiPREy2qE

## Screenshots
![CorridorRoad screenshot 01](https://github.com/user-attachments/assets/8afd06ad-2e84-46fe-b8a7-0ca4490f2902)
![CorridorRoad screenshot 02](https://github.com/user-attachments/assets/da25c711-88a1-4101-acd5-1353fba72ea4)
![CorridorRoad screenshot 03](https://github.com/user-attachments/assets/e243fb11-cb56-49db-bb64-dbd0af535c8d)
![CorridorRoad screenshot 04](https://github.com/user-attachments/assets/5638bace-9e6a-4c35-9524-6c66f2f2d36d)
![CorridorRoad screenshot 05](https://github.com/user-attachments/assets/4f3bf538-04e1-47c2-a3e6-a2139192a48a)
![CorridorRoad screenshot 06](https://github.com/user-attachments/assets/a6735b8f-b71e-4085-92ef-a06bc5931c7d)
![CorridorRoad screenshot 07](https://github.com/user-attachments/assets/22571089-b91b-438f-8e32-ede0a823812b)
![CorridorRoad screenshot 08](https://github.com/user-attachments/assets/999d9e0c-54ee-4fd1-9b63-c287724899ba)
![CorridorRoad screenshot 09](https://github.com/user-attachments/assets/88beb6f7-ce66-41e5-bd5d-db4112e6b95c)
![CorridorRoad screenshot 10](https://github.com/user-attachments/assets/32d4e2ab-c05e-438d-ad8d-a4705bb12825)
![CorridorRoad screenshot 11](https://github.com/user-attachments/assets/71d0cb7d-50e9-4c66-be81-727b0e0840b6)
![CorridorRoad screenshot 12](https://github.com/user-attachments/assets/9712cf4d-1d3a-4443-b393-257c5837e93f)
![CorridorRoad screenshot 13](https://github.com/user-attachments/assets/64e20bd5-941a-4a09-9efa-4d16e808cd84)



