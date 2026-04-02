<!-- SPDX-License-Identifier: LGPL-2.1-or-later -->
<!-- SPDX-FileNotice: Part of the Corridor Road addon. -->

# Menu Reference

This page explains the main task panels used early in the CorridorRoad workflow.
The goal is to clarify what each option means, when to change it, and how it affects downstream commands.

## 1. Project Setup

Use `Project Setup` immediately after `New Project`, before importing alignment or terrain data.
This panel defines project-wide scale, coordinate conversion, and design-standard metadata.

Important behavior:
1. `Project Setup` does not move or transform existing geometry automatically.
2. It changes how CorridorRoad interprets `Local` and `World` coordinates.
3. For that reason, it is best to finalize these values before importing terrain or alignment data.

### Option Reference

| Option | Meaning | How to use it |
|---|---|---|
| `Target Project` | Selects which `CorridorRoadProject` object will be updated. | Normally leave this on the active project created by `New Project`. |
| `Length Scale` | Internal units per meter. `1.0` means meter-native. Larger values such as `1000.0` mean the model uses millimeter-like internal units. | Set this once at the start of the project. Other tools such as DEM import and PVI scaling follow this value. Changing it after data already exists can create inconsistencies. |
| `Design Standard` | Stores the selected road design standard on the project. | Use the standard that should control alignment/design checks. Even if the current stage is mostly geometric, keep this consistent for later validation work. |
| `CRS / EPSG` | Coordinate system identifier, for example `EPSG:5186`. The panel now exposes this through an editable preset-style combo box. | Use the built-in CRS/EPSG presets for common coordinate systems, or type a custom EPSG code directly when the project uses a different CRS. |
| `Coordinate Workflow` | Recommended coordinate-input policy for downstream task panels. | `World-first` is recommended when `CRS / EPSG` is set. `Local-first` is recommended when the project stays in local engineering coordinates. `Custom` keeps the project metadata but stops pushing one policy as the main recommendation. |
| `Auto-apply recommended modes in task panels` | Controls whether task panels should use the workflow recommendation as their initial coordinate mode. | Keep this enabled for a consistent project-wide policy. Turn it off only when each task panel should decide its own coordinate mode manually. |
| `Horizontal Datum` | Horizontal datum text metadata. | Optional. Fill it when the survey or project requires explicit datum documentation. |
| `Vertical Datum` | Vertical datum text metadata. | Optional. Fill it when elevations must be traceable to a known datum. |
| `Project Origin E` | World easting origin of the project anchor point. | Use this when converting between local model coordinates and world coordinates. |
| `Project Origin N` | World northing origin of the project anchor point. | Same role as `Project Origin E`, but for northing. |
| `Project Origin Z` | World elevation origin of the project anchor point. | Use when local Z must map to real-world elevation. |
| `Local Origin X` | Local model X corresponding to the chosen world origin. | Usually `0` for a new project, unless you intentionally anchor a shifted local coordinate system. |
| `Local Origin Y` | Local model Y corresponding to the chosen world origin. | Same role as `Local Origin X`. |
| `Local Origin Z` | Local model Z corresponding to the chosen world origin. | Same role as `Local Origin X`, but for elevation. |
| `North Rotation` | Rotation from local model axes to world north, in degrees, positive counter-clockwise around Z. | Leave `0` if local X/Y already aligns with the world frame. Use a nonzero value only when the project coordinate frame is intentionally rotated. |
| `Lock coordinate setup` | Prevents accidental edits to the stored coordinate setup. | After coordinate values are verified, turn this on to protect the project. To edit locked values later, uncheck the lock and apply again. |
| `Setup Status` | Project workflow status such as `Uninitialized`, `Initialized`, or `Validated`. | Use this as a human-readable project state marker. It is not a full validator by itself. |
| `Refresh Context` | Reloads the currently selected project values into the panel. | Use this if you changed properties elsewhere and want the panel to reflect the current state. |
| `Apply Setup` | Writes the current values back to the project object and recomputes the document. | Use after confirming scale and coordinate values. |

### Recommended Usage
1. Set `Length Scale` first.
2. Enter `CRS / EPSG` and origin values if the workflow uses real-world coordinates.
3. Confirm `Coordinate Workflow`.
4. In most survey/UTM jobs, use `World-first`.
5. In simple local test files, use `Local-first`.
6. Leave local origins at zero unless you deliberately want an offset local model.
7. Apply once and confirm imports behave correctly.
8. Lock the setup after the coordinate policy is confirmed.

### Practical Notes
1. If point cloud CSV is in UTM, `Project Setup` should usually be completed before `Import PointCloud DEM`.
2. If alignment and terrain appear shifted, check `Project Origin`, `Local Origin`, and `North Rotation` before changing other tools.
3. If `Auto-apply recommended modes in task panels` is enabled, `Import PointCloud DEM`, `Alignment`, `Edit Profiles`, `Generate Sections`, `Design Terrain`, and `Cut/Fill Calc` will start from the workflow recommendation.
4. `Setup Status` is useful for team workflow, but it does not prevent generation commands by itself.

> [Screenshot Needed] Project Setup panel with coordinate fields filled.
> Suggested file: `wiki-menu-reference-project-setup.png`

## 2. Edit Alignment

Use `Edit Alignment` to create or update the horizontal alignment from table rows, CSV input, sketch geometry, or built-in starter presets.

Important behavior:
1. The alignment table always stores the values currently shown in the panel coordinate mode.
2. Built-in presets are defined as local pattern rows.
3. If `Coord Input = World (E/N)`, `Load Preset` converts those local preset rows through the active `Project Setup`.
4. `Preset Placement` defaults to `Center on terrain`, so starter geometry tries to land inside the current terrain extent instead of staying near `(0,0)`.
5. CSV import remains the main path for real survey or design data; presets are meant for quick starts and test geometry.

### Alignment Source Options

| Option | Meaning | How to use it |
|---|---|---|
| `Alignment` | Selects which `HorizontalAlignment` object will be edited. | Choose an existing alignment or let `Apply Alignment` create one when none exists and creation is enabled. |
| `Sketch` | Selects a sketch for sketch-based row generation. | Use when you already drafted a path in a FreeCAD sketch and want starter IP rows from it. |
| `Load from Sketch` | Reads the selected sketch into the alignment table. | Good for fast concept geometry. Review radii and transitions after loading. |
| `CSV` / `Browse CSV` / `Load from CSV` | Reads alignment rows from a CSV file. | Use this for real project data or repeatable exchange files. |
| `Preset` | Built-in starter geometry such as `Simple Tangent`, `Single Curve`, `S-C-S Curve`, `Reverse Curve`, or `Sample Local Alignment`. | Use when you want to start from a known local-pattern geometry instead of a blank table. |
| `Load Preset` | Loads the selected preset into the alignment table. | In `Local (X/Y)` mode the preset rows are inserted directly. In `World (E/N)` mode they are converted using the active `Project Setup`. |
| `Preset Placement` | Controls where preset rows are placed before they are written into the table. | `Center on terrain` is the default and is the best choice for sample/test workflows. `Pattern only` keeps the original local pattern location. `Center on project origin` is a safe fallback when no terrain exists yet. |
| `Coord Input` | Declares whether the table currently represents local or world coordinates. | Keep this consistent with the source you are loading or the way you want presets to be converted. |
| `Save CSV` | Writes the current table rows back to a CSV file. | Useful after starting from a preset and refining it into reusable project data. |

### Practical Notes
1. Presets are best thought of as pattern starters, not authoritative survey coordinates.
2. If the project uses `World-first`, preset loading is still safe because the conversion uses `Project Origin`, `Local Origin`, and `North Rotation`.
3. `Center on terrain` will fall back to `Center on project origin` when no terrain can be resolved.
4. If a preset still lands outside the expected area, check `Coord Input`, `Preset Placement`, and `Project Setup` rotation/origin values first.

> [Screenshot Needed] Alignment editor showing the Preset combo, Load Preset, and Coord Input.
> Suggested file: `wiki-menu-reference-alignment-preset.png`

## 3. Import PointCloud DEM

Use `Import PointCloud DEM` to turn point cloud CSV data into a DEM-style mesh terrain for EG sampling, daylight reference, and terrain-based analysis.

Important behavior:
1. If a `PointCloudDEM` object already exists, this panel updates that object instead of creating a second terrain object.
2. The DEM is built by regular XY grid sampling, not TIN.
3. DEM quality depends strongly on `Cell Size`, input coordinate mode, and source point density.

### CSV Source Options

| Option | Meaning | How to use it |
|---|---|---|
| `CSV File` | Path to the point cloud CSV file. | Select a CSV with `easting,northing,elevation` or supported aliases. |
| `Input Coords` | Declares whether the CSV values are `World` coordinates or `Local` project coordinates. | Use `World` for UTM or survey ENZ input. Use `Local` only when the CSV is already in project XY/Z coordinates. |
| `Output Mesh Coords` | Chooses whether the generated terrain mesh is stored in `Local` or `World` coordinates. | `Local` is the safer default for internal modeling. Use `World` only when a downstream workflow explicitly expects world-coordinate terrain geometry. |
| `Delimiter` | CSV delimiter mode. | `Auto` is usually fine. Force a delimiter only when auto-detection misreads the file. |
| `CSV has header row` | Tells the importer whether the first row is a header. | Keep enabled for normal CSV files. Disable only for raw data files with no header row. |
| `Coordinate Setup` | Read-only hint showing the active coordinate context. | Use it as a sanity check before import, especially when using `World` coordinates. |
| `Refresh Context` | Reloads project and DEM object state into the panel. | Useful after changing project setup or DEM properties elsewhere. |

Practical default note:
1. When `Project Setup` is `World-first`, a new DEM import panel now defaults `Input Coords` to `World`.
2. When `Project Setup` is `Local-first`, it defaults to `Local`.

### DEM Options

| Option | Meaning | How to use it |
|---|---|---|
| `Cell Size (scaled)` | DEM grid resolution in internal project units. Smaller cells keep more detail; larger cells smooth more. | Start near the source point spacing. Increase it if EG/profile values contain many blanks or zeros due to sparse point cloud coverage. |
| `Aggregation` | How multiple points inside the same DEM cell are reduced to one elevation. | `Mean` is general-purpose. `Median` is better when outliers exist. `Min` and `Max` are specialized and can bias the terrain downward or upward. |
| `Max Cells` | Safety limit for estimated grid size. | If import fails with too many estimated cells, increase `Cell Size` rather than simply raising this limit. |
| `Auto update on parameter changes` | If enabled, changing DEM properties can trigger recompute behavior. If disabled, the object is marked as needing recompute. | Keep enabled during normal interactive work. Turn it off only when you want to stage several changes before rebuilding. |

### Run Controls

| Option | Meaning | How to use it |
|---|---|---|
| `Import CSV and Build DEM` | Runs the import, creates or updates the `PointCloudDEM` object, and builds the mesh. | Main execution button. |
| `Status` | Current importer state. | Read it for `OK`, `ERROR`, or `CANCELED` messages. |
| `Progress` | Import/build progress bar. | Useful for large CSV files. |
| `Cancel` | Requests cancellation during a long import. | Use if the input file or settings are clearly wrong. |

### Recommended Usage
1. Set `Input Coords` to match the CSV.
2. Keep `Output Mesh Coords` consistent with the rest of the project, usually `Local`.
3. Start with a practical `Cell Size`, not the smallest possible value.
4. Build the DEM and inspect both the mesh coverage and the completion message.
5. If EG/profile data later contains many blanks or zeros, rebuild with a slightly larger `Cell Size`.

### Practical Notes
1. A very small `Cell Size` can preserve detail but also expose holes in sparse point clouds.
2. `Median` can be more stable than `Mean` when the CSV contains bad high/low spikes.
3. `Min` and `Max` are usually for envelope-like cases, not for neutral terrain reconstruction.
4. The completion dialog reports points used, skipped rows, estimated grid size, and no-data counts. Use that information when diagnosing poor EG coverage.

> [Screenshot Needed] PointCloud DEM panel with source and DEM options visible.
> Suggested file: `wiki-menu-reference-pointcloud-dem.png`

## 4. Edit Profiles

Use `Edit Profiles` to manage station-based EG/FG profile data.
This panel is where station lists, sampled EG values, manual FG values, and FG-from-VerticalAlignment behavior come together.

Important behavior:
1. The table stores `Station`, `EG`, `FG`, and computed `Delta`.
2. `Apply` can sample EG from the selected terrain before saving.
3. If `FG from VerticalAlignment` is enabled and a vertical alignment exists, the `FG` column becomes read-only and is regenerated from the vertical alignment.
4. If manual FG editing is used, the FG display wire is hidden to avoid showing stale geometry.
5. `Import FG CSV` and `FG Wizard` both write manual FG values. If FG is currently locked to `VerticalAlignment`, the panel asks whether it should switch to manual FG first.
6. The table-action buttons are split into two rows on purpose so long labels stay readable in narrower task panels.

### Table Columns

| Column | Meaning | How to use it |
|---|---|---|
| `Station` | Station value along the alignment. | Required. At least 2 valid rows are needed to save a profile bundle. |
| `EG` | Existing ground elevation. | Can be filled from terrain sampling or edited manually. Blank EG values may later be saved as `0` if unresolved. |
| `FG` | Finished grade elevation. | Editable only in manual FG mode. Locked and auto-filled when `FG from VerticalAlignment` is enabled. |
| `Delta (FG-EG)` | Difference between FG and EG. | Read-only diagnostic field. |

### Buttons

Current layout:
1. Top row: `Add Row`, `Remove Row`, `Sort by Station`, `Fill Stations from Stationing`
2. Bottom row: `Fill FG from VerticalAlignment`, `Import FG CSV`, `FG Wizard`

| Option | Meaning | How to use it |
|---|---|---|
| `Add Row` | Adds one blank table row. | Use for manual editing. |
| `Remove Row` | Removes the selected row. | If no row is selected, the last row is removed. |
| `Sort by Station` | Sorts rows by station. | Use before saving if rows were manually edited out of order. Rows with FG but blank EG are preserved. |
| `Fill Stations from Stationing` | Replaces the table with `Stationing.StationValues`. | Use after `Generate Stations`. This is the fastest way to build the profile table. |
| `Fill FG from VerticalAlignment` | Fills FG values from the current `VerticalAlignment`. | Useful after editing PVIs. It only matters when a vertical alignment exists. |
| `Import FG CSV` | Imports `Station` + `FG` pairs from CSV/text and writes them into manual FG. | Existing matching stations are updated. Imported stations that do not exist yet are appended, then the table is re-sorted. |
| `FG Wizard` | Generates manual FG values over a selected station range. | Supports `EG + constant offset`, `EG + start/end offset ramp`, and `absolute FG interpolation`. |

### Options

| Option | Meaning | How to use it |
|---|---|---|
| `Create ProfileBundle if missing` | Allows the panel to create a new `ProfileBundle` automatically. | Keep enabled in normal workflows. Disable it only if you want strict control and expect the object to exist already. |
| `FG from VerticalAlignment (lock FG column)` | Uses the `VerticalAlignment` object as the FG source of truth and locks the FG table column. | Recommended when FG should follow PVI design. Turn it off only when you intentionally want manual FG editing. |
| `Show EG wire (ProfileBundle)` | Controls EG profile wire visibility. | Turn off if the EG wire clutters the view. |
| `Show FG wire (Finished Grade (FG))` | Controls FG display wire visibility. | When using FG from VA, keep this on so the 3D/profile display matches the computed FG. |
| `EG Z Offset` | Vertical display offset for the EG wire. | Use only for visual separation in profile view. It does not change stored EG data. |
| `FG Z Offset` | Vertical display offset for the FG wire. | Use only for display clarity. |
| `EG Terrain Source` | Terrain object used to sample EG values. | Choose the `PointCloudDEM` terrain or another valid mesh/shape source. |
| `EG Terrain Coords` | Declares how the selected terrain should be sampled: `Local` or `World`. | Match this to the terrain object. For `PointCloudDEM`, this often auto-syncs from `OutputCoords`. |
| `Use Selected Terrain` | Takes the currently selected mesh/shape from the 3D view or tree and sets it as the EG terrain source. | Fastest way to avoid choosing the wrong terrain object in the combo. |
| `Apply` | Samples EG if possible, then saves stations/EG/FG/display settings to the `ProfileBundle` and related display objects. | Main save button. |

### Recommended Usage
1. Run `Generate Stations` first.
2. Open `Edit Profiles`.
3. Click `Fill Stations from Stationing`.
4. Choose the DEM terrain as `EG Terrain Source`.
5. Keep `FG from VerticalAlignment` enabled if FG should be driven by `Edit PVI`.
6. If you want a non-PVI starting point, switch to manual FG and use `Import FG CSV` or `FG Wizard`.
7. Click `Apply`.

### Practical Notes
1. If EG sampling fails or coverage is poor, first verify terrain extent and coordinate mode.
2. If EG remains blank in the table, unresolved blanks can become `0` on save. Fix terrain sampling before treating those values as valid.
3. If you manually edit FG while FG-from-VA is off, the FG wire is hidden on purpose so the display does not misrepresent the table data.
4. `EG Terrain Coords` should usually match the terrain's actual storage mode, not just the coordinate mode of the input CSV.

> [Screenshot Needed] Edit Profiles panel with terrain source, coord mode, and profile table.
> Suggested file: `wiki-menu-reference-edit-profiles.png`

## 4. Edit PVI

Use `Edit PVI` to define vertical alignment geometry and generate FG values from it.
This tool creates or updates the `VerticalAlignment` object and then writes computed FG values into the profile bundle.

Important behavior:
1. `Vertical Alignment (PVI)` is now shown in 3D view by default.
2. The station list used for FG generation comes from `ProfileBundle.Stations` if available, otherwise from `Stationing.StationValues`.
3. `Generate FG Now (apply)` updates both the `VerticalAlignment` and the `ProfileBundle`.
4. The left side of the panel now includes an inline input guide and a live grade/curve preview summary so users can understand what each PVI row means before generation.
5. If no existing vertical alignment is found, the panel now auto-loads a starter PVI from the resolved station range.

### PVI Table Columns

| Column | Meaning | How to use it |
|---|---|---|
| `PVI Station` | Station of the PVI point. | Required. Rows are sorted by station before use. |
| `PVI Elev` | Elevation at the PVI point. | Required. |
| `Curve Length` | Vertical curve length `L` at that PVI. | Use `0` for no vertical curve at that PVI. Positive values create a symmetric vertical curve centered on that PVI. It is not the distance to the next row. |

### Generate FG Options

| Option | Meaning | How to use it |
|---|---|---|
| `Clamp overlapping vertical curves (auto adjust L)` | Automatically shortens curve lengths when adjacent curves would overlap or violate tangent spacing. | Recommended for interactive editing. Turn it off only when you want the tool to reject invalid geometry instead of adjusting it. |
| `Min Tangent` | Minimum required tangent length between adjacent vertical curves. | Increase this when you want to enforce a minimum straight grade segment between curves. |
| `Create ProfileBundle if missing` | Allows FG generation to create a profile bundle if one does not exist yet. | Keep enabled unless you want generation to fail when prerequisites are incomplete. |
| `Keep existing EG values (do not overwrite)` | Preserves current EG values in the profile bundle during FG generation. | Recommended in normal workflows because `Edit PVI` is for FG generation, not terrain resampling. |
| `Load Starter PVI` | Rebuilds the table with starter PVI rows based on the resolved station range. | Use when you want a safe starting point after clearing the table or when there is no saved vertical alignment yet. |
| `Clear to Blank` | Clears valid PVI input rows and restores a blank starter-sized table. | Use when you want to type the vertical alignment from scratch. |
| `Preview FG (console)` | Saves the current PVI table, resolves a station list, and prints sample FG elevations to the FreeCAD console. | Use for quick validation before writing data into the profile bundle. |
| `Generate FG Now (apply)` | Saves the vertical alignment, computes FG on the resolved stations, updates the profile bundle, and shows a completion dialog. | Main execution button. |

### Recommended Usage
1. Create or confirm stationing first.
2. Let the panel auto-load the starter PVI, or click `Load Starter PVI`.
3. Read the inline guide:
   - `PVI Station` = where the incoming and outgoing grades meet
   - `PVI Elev` = finished-grade elevation at that station
   - `Curve Length` = total vertical-curve length centered on that PVI
4. Use `Clear to Blank` if you want to start from an empty table instead.
5. Enter PVI rows in station order or click `Sort by Station`.
6. Use `Curve Length = 0` where you want simple grade breaks.
7. Check the live summary under the table to confirm grades and BVC/EVC ranges look reasonable.
8. Keep `Clamp overlapping vertical curves` enabled unless you are intentionally checking invalid geometry.
9. Click `Generate FG Now (apply)`.
10. Return to `Edit Profiles` with `FG from VerticalAlignment` enabled if you want the profile table locked to the generated FG.

### Practical Notes
1. If no profile bundle exists, FG generation can create one and seed it from the resolved station list.
2. If no station list exists in either `ProfileBundle` or `Stationing`, FG generation cannot proceed.
3. `Keep existing EG values` does not resample terrain. It only protects existing EG data while FG is regenerated.
4. The completion dialog confirms station count and helps show that FG generation has actually finished.

> [Screenshot Needed] Edit PVI panel with PVI table and Generate FG options.
> Suggested file: `wiki-menu-reference-edit-pvi.png`

## 5. Edit Structures

Use `Edit Structures` after `Generate Stations`.
This panel creates or updates the `StructureSet` object that stores structure zones, structure station ranges, and 3D/reference geometry.

Important behavior:
1. `StartStation`, `EndStation`, and `CenterStation` are station-combo values populated from `Stationing`.
2. `Type`, `Side`, and `BehaviorMode` are controlled lists to keep structure behavior predictable.
3. `Apply` writes the `StructureSet`, updates 3D solids, and links the result into `01_Inputs/Structures`.
4. `Apply` also reports external-shape fallback diagnostics and frame diagnostics when placement had to use `alignment` instead of `centerline3d`.
5. The upper table now starts in a compact `Basic` view and exposes advanced fields mainly through `Selected Structure Details`.

### Main Controls

| Option | Meaning | How to use it |
|---|---|---|
| `Target StructureSet` | Chooses whether to edit an existing `StructureSet` or create a new one. | Use the existing set in a single-alignment workflow. Create a new one only when you intentionally want a separate structure dataset. |
| `CSV File` | Optional path to a structure CSV file. | Use it when bulk-loading structure records instead of typing rows manually. |
| `Browse CSV` | Opens a file chooser for structure CSV. | Recommended for standard sample/test workflows. |
| `Load CSV` | Reads the CSV and fills the structure table. | Review the table before `Apply`. |
| `Browse Shape` | Opens a file chooser for the selected row's external shape source. | Supports `.step`, `.brep`, and `.FCStd`. For `FCStd`, append `#ObjectName` in `ShapeSourcePath`. |
| `Pick FCStd Object` | Opens an object picker for the selected `.FCStd` source. | After selecting the `.FCStd` file, use this to choose a shape-bearing object and automatically fill `ShapeSourcePath` as `path.FCStd#ObjectName`. |
| `Browse Profile CSV` | Opens a file chooser for station-profile control-point CSV data. | Use after loading or defining the base structure rows. |
| `Load Profile CSV` | Reads the station-profile CSV and stores control points for later apply. | Load the base structure CSV first, then the profile CSV. |
| `Columns: Template / External Shape / Advanced` | Reveals grouped upper-table columns on demand. | Keep them off for overview work; turn them on temporarily for focused editing. |
| `Add Common Structure` | Inserts a starter row for the selected structure type. | Useful for quickly adding one culvert, crossing, wall, abutment, bridge zone, or external-shape placeholder. |
| `Clone Selected` | Duplicates the selected structure row and shifts it forward in station. | Also duplicates station-profile points linked to that structure ID. |
| `Preset` + `Load Preset` | Loads a built-in structure set preset. | Good for testing drainage, wall, mixed, or variable-size workflows without starting from a blank table. |
| `Profile Preset` + `Load Profile Preset` | Generates starter station-profile rows for the currently selected structure row. | Use this when one structure needs quick variable-size control points without preparing a separate profile CSV first. |
| `Apply` | Saves the table into the active `StructureSet`, validates it, recomputes the document, and shows a status message. | Main execution button. |

### Table Columns

| Column | Meaning | How to use it |
|---|---|---|
| `Id` | Structure identifier. | Use a stable readable ID like `CULV-01` or `RW-02`. |
| `Type` | Structure classification. | Allowed values are `crossing`, `culvert`, `retaining_wall`, `bridge_zone`, `abutment_zone`, `other`. |
| `StartStation` | Structure influence start station. | Select from the generated station list when possible. |
| `EndStation` | Structure influence end station. | Must be greater than or equal to `StartStation`. |
| `CenterStation` | Main representative station for labeling and midpoint behavior. | Usually set to the center of the structure zone. |
| `Side` | Which side of the alignment the structure belongs to. | Use `left`, `right`, `center`, or `both`. |
| `Offset` | Lateral offset from the centerline. | Positive/negative placement depends on the resolved local section frame. Use `0` for center crossings. |
| `Width` | Structure width or influence width. | Used for both simple 3D display and section overlay envelope. |
| `Height` | Structure height or influence height. | Used for display and overlay envelope. |
| `BottomElevation` | Explicit bottom elevation for display/overlay. | Use this when the structure invert or footing elevation is known. |
| `Cover` | Cover depth used when bottom elevation is not specified. | Useful for culverts or buried crossings. |
| `RotationDeg` | Rotation about the local vertical axis. | Leave `0` unless the structure should be rotated relative to alignment normal/tangent. |
| `BehaviorMode` | Controls how the structure participates in section generation. | `tag_only` adds metadata only, `section_overlay` adds section-aware overlay behavior, `assembly_override` also enables section override logic. |
| `GeometryMode` | Controls how the structure is displayed in 3D and in `Structure Sections` overlays. | `box` keeps the simple rectangular fallback. `template` enables parametric structure geometry. |
| `TemplateName` | Selects the template when `GeometryMode=template`. | Current values are `box_culvert`, `utility_crossing`, `retaining_wall`, and `abutment_block`. |
| `ShapeSourcePath` | Local source path for `GeometryMode=external_shape`. | First-pass supported formats are `.step` / `.stp`, `.brep` / `.brp`, and `.FCStd#ObjectName`. |
| `ScaleFactor` | Uniform scale applied to external geometry before placement. | Keep `1.0` unless the source model units require adjustment. |
| `PlacementMode` | Chooses whether the external model is centered or start-anchored at the selected station. | Use `center_on_station` for symmetric models and `start_on_station` for start-based models. |
| `UseSourceBaseAsBottom` | Controls whether the source model bottom (`ZMin`) is aligned to the resolved structure bottom. | Keep `true` for most imported solids. |
| `WallThickness` | Template wall thickness. | Used by both `box_culvert` and `retaining_wall`. |
| `FootingWidth` | Retaining-wall footing width. | Mainly used by the `retaining_wall` template. |
| `FootingThickness` | Retaining-wall footing thickness. | Mainly used by the `retaining_wall` template. |
| `CapHeight` | Optional top cap height. | Used by both templates when a raised top cap is needed. |
| `CellCount` | Number of culvert cells. | Used by the `box_culvert` template. Minimum practical value is `1`. |
| `CorridorMode` | Controls how the structure should be consumed by `Corridor Loft`. | `none` ignores corridor-level changes, `split_only` only splits loft spans, `skip_zone` omits the corridor body across the active structure span, and `notch` uses a notch-aware loft profile. In the current implementation, `notch` is mainly intended for `culvert` and `crossing`. |
| `CorridorMargin` | Expands the corridor skip envelope beyond start/end station. | Use a small positive margin only when the skipped corridor zone should be slightly wider than the structure station range. |
| `Notes` | Free-form notes. | Use for documentation and later review. |

### Recommended Usage
1. Generate stations first.
2. Load `tests/samples/structure_utm_realistic_hilly.csv` or enter rows manually.
3. Use `tests/samples/structure_utm_realistic_hilly_notch.csv` when you want a focused `CorridorMode=notch` starter.
4. Use `tag_only` for reference structures and `section_overlay`/`assembly_override` only where section behavior should change.
5. Choose `GeometryMode=template` when you want parametric structure display instead of the simple rectangular fallback.
6. Apply and verify that the `StructureSet` appears under `01_Inputs/Structures`.
7. If you use `GeometryMode=external_shape`, replace placeholder sample paths with real local `.step`, `.brep`, or `.FCStd#ObjectName` sources before `Apply`.
8. If `Apply` reports `frame source=alignment`, run `3D Centerline` again and re-apply the structure set.
9. For `FCStd`, the easiest path is `Browse Shape` -> `Pick FCStd Object`.
10. `GeometryMode=external_shape` is currently for realistic structure display/reference placement plus proxy-earthwork reporting; it is not direct boolean consumption.
11. Use `Selected Structure Details` for most advanced edits instead of turning on every table column.
12. The validation summary now reports row-level warnings and errors before apply.
13. See `docs/PRACTICAL_SAMPLE_SET.md` for the maintained starter and mixed sample bundles.

### Practical Notes
1. A `retaining_wall` should usually use `left` or `right`, not `center`.
2. A `culvert` or `crossing` usually makes more sense with `center` or `both`.
3. If `BottomElevation` is empty, the display system falls back to centerline Z and `Cover`.
4. The 3D solids created here are reference geometry, not final corridor boolean geometry.
5. `CorridorMode` is now the main way to tell `Corridor Loft` whether a structure should only stabilize segmentation or actually omit a corridor span.
6. `GeometryMode=template` currently improves 3D display and `Structure Sections` overlay quality first; it does not yet imply full corridor boolean consumption.
7. `GeometryMode=external_shape` currently supports first-pass placement of local `STEP`/`BREP` files and `FCStd#ObjectName` links, and falls back to safe `box` geometry if the source cannot be loaded.
8. `ShapeSourcePath` cell color is part of the workflow: green means the source file exists, red means the path or FCStd object reference still needs attention.
9. Even when `external_shape` is displayed correctly, current earthwork still uses the structure `Type` and simple dimensional fields rather than the true imported solid.
10. The selected-structure summary now reports the interpreted earthwork behavior and the current validation state.
11. Upper-table context changes are now driven by explicit row press/click; the workflow no longer depends on hover.

### Advanced: Station-Profile Data
The runtime now supports variable-size structures driven by station control points, and `Edit Structures` now exposes this through a second linked table.

Current status:
1. The upper table edits base structure header rows.
2. The lower table shows station-profile control points for the currently selected structure row.
3. `Load Profile CSV` populates the same backing data used by the lower table.
4. The runtime already consumes station-profile values for:
   - 3D structure display
   - `Structure Sections` overlays
   - section overrides / earthwork
   - corridor `notch` handling
5. The lower table now also supports `Sort by Station`, `Duplicate Profile Row`, `Add Midpoint`, and `Delete All for Selected`.
6. A `Profile Preset` row above the lower table can generate starter control points directly from the currently selected structure span and dimensions.

Current practical workflow:
1. Use `tests/samples/structure_utm_realistic_hilly_station_profile_headers.csv` as the base structure-header reference.
2. Use `tests/samples/structure_utm_realistic_hilly_station_profile_points.csv` as the companion station-profile reference.
3. Or use `tests/samples/structure_utm_realistic_hilly_mixed.csv` and `tests/samples/structure_utm_realistic_hilly_mixed_profile_points.csv` for one combined multi-structure test set.
4. Select a structure in the upper table to inspect or edit only that structure's profile rows in the lower table.

### Current Template Support

| Template | Current behavior |
|---|---|
| `box_culvert` | Builds an outer culvert shell with internal cell voids in 3D display and shows cell-aware section overlays in `Structure Sections`. |
| `retaining_wall` | Builds footing + stem + optional cap in 3D display and shows matching retaining-wall section overlays. |

> [Screenshot Needed] Edit Structures panel with sample rows loaded.
> Suggested file: `wiki-menu-reference-edit-structures.png`

## 6. Generate Sections: Structure Options

The `Generate Sections` panel now includes structure-aware options that work with `StructureSet`.

### Structure Integration Options

| Option | Meaning | How to use it |
|---|---|---|
| `Use linked StructureSet` | Enables station merge and structure-aware section generation from `StructureSet`. | Turn this on when structures should influence section station selection or overlays. |
| `Structure Source` | Chooses the source `StructureSet`. | Normally use the active project structure set. |
| `Include start/end stations` | Adds structure start and end stations into the section station list. | Keep enabled in most workflows. |
| `Include center stations` | Adds structure center stations into the section station list. | Keep enabled when you want a clear mid-structure section. |
| `Include transition stations` | Adds transition stations before and after each structure zone. | Keep enabled in most workflows so section shape changes do not happen too abruptly at structure boundaries. |
| `Auto transition distance` | Derives transition distance automatically from structure type and size. | Recommended default. It reduces manual tuning when different structure types need different boundary spacing. |
| `Transition Distance` | Manual fallback distance used for transition stations when auto mode is off. | Turn off auto mode only when you need to force one fixed distance for all structure records. |
| `Add structure tags to child sections` | Adds tags and metadata to child sections at structure-related stations. | Keep enabled if you want labels and tree identification. |
| `Apply structure overrides` | Enables structure-type override logic during section build. | Turn this on when structure zones should constrain daylight/side-slope behavior. |

### Corridor Loft Structure Options

| Option | Meaning | How to use it |
|---|---|---|
| `Use structure corridor modes` | Reads `CorridorMode` from the linked `StructureSet` during corridor build. | Keep enabled if structures should affect the corridor body, not just sections. |
| `Default structure corridor mode` | Fallback mode used when a structure record does not specify `CorridorMode`. | `split_only` is the safe default. Use `skip_zone` only when missing corridor modes should still create corridor gaps. |
| `Notch transition scale` | Scales how gradually a notch ramps in and out around transition stations. | Start with `1.0`. Increase it for a longer, softer notch transition; reduce it if the notch should reach full effect more quickly. |

Recommended user policy:
1. `culvert`, `crossing` -> `notch`
2. `bridge_zone`, `abutment_zone` -> `skip_zone`
3. `retaining_wall` -> `split_only`

### Override Policy Summary

| Structure Type | Current Section Override Behavior |
|---|---|
| `crossing` | Affects both sides; replaces daylight-driven side slopes with short flat berm-like side segments through the active zone. |
| `culvert` | Affects both sides; behaves like a crossing and keeps a wider flat berm around the structure envelope instead of full daylight slopes. |
| `retaining_wall` | Affects only the declared side; replaces that side with a short steep wall-like segment while the opposite side can stay normal. |
| `bridge_zone` | Affects both sides conservatively; trims side-slope reach and disables daylight so the section remains loft-stable near the zone. |
| `abutment_zone` | Affects both sides conservatively; trims side-slope reach and disables daylight so the section remains loft-stable near the zone. |
| `other` | No special type logic beyond the selected `BehaviorMode`. |

### Auto Transition Distance Rules

When `Auto transition distance` is enabled, the current default rules are:

| Structure Type | Auto Rule |
|---|---|
| `culvert`, `crossing` | `max(5 m, 0.75 x Width, 1.50 x Height)` |
| `retaining_wall` | `max(3 m, 0.50 x Width, 1.00 x Height)` |
| `bridge_zone`, `abutment_zone` | `max(10 m, 0.50 x Width, 1.00 x Height)` |
| `other` | `max(5 m, 0.50 x Width, 1.00 x Height)` |

Interpretation:
1. Crossing-like structures use a moderate transition so section shape and daylight do not change too abruptly at entry and exit.
2. Retaining walls usually need a shorter transition because only one side is typically constrained.
3. Bridge and abutment zones use longer transition spacing because their influence is usually wider and more conservative.
4. If project `Length Scale` is not meter-native, the actual stored internal distance scales automatically.

When to override manually:
1. The structure boundary still looks too abrupt even with auto mode on.
2. The structure influence should be much tighter than its displayed width.
3. You want a uniform transition distance for all structures in a specific test case.

### Output To Expect
1. Standard section children continue to appear under `Sections`.
2. Structure overlay objects appear under `Structure Sections`.
3. `SectionSet.Status` reports merged structure count and override hit count.
4. `CorridorLoft` can report `Notch-aware stations` and `Closed profile schema` when a notch-aware loft profile is used.

> [Screenshot Needed] Generate Sections panel with StructureSet options expanded.
> Suggested file: `wiki-menu-reference-generate-sections-structures.png`

## 6A. Generate Sections: Side Slopes and Bench

`Generate Sections` can also build earthwork-style side slopes directly from the linked `AssemblyTemplate`.

### Side Slope / Bench Options

| Option | Meaning | How to use it |
|---|---|---|
| `Use side slopes` | Adds left/right side-slope wings outside the main carriageway/top profile. | Turn this on when the section should extend beyond the finished-grade top width. |
| `Side Width Left/Right` | Horizontal reach of the side slope before daylight or fixed-width termination. | Use larger values for wider cut/fill wings. |
| `Side Slope Left/Right (%)` | Base side-slope gradient used for the wing. | Positive values slope downward outward in fill-like conditions. |
| `Use Left Bench` / `Use Right Bench` | Enables benching on that side. | Turn this on when that side should use one or more terrace rows. |
| `Left Bench Rows` / `Right Bench Rows` | Table-based bench editor with `Drop`, `Width`, `Slope`, and `Post-Slope` columns. | Add one row per terrace. Single-bench and multi-bench cases use the same table workflow. |
| `Daylight Auto (SectionSet)` | Searches for terrain intersection automatically. | When a bench is enabled, daylight is applied only on the post-bench slope segment. |

### Practical Notes

1. Current bench support is still conservative, but it now supports multi-bench terrace stacks on each side through the unified `Left Bench Rows` and `Right Bench Rows` editors.
2. Structure override modes still take precedence. If a structure trims/stubs a side, the bench on that side is disabled for that section.
3. Bench input is now one unified row list per side. Users no longer need to think in terms of “primary bench” versus “extra bench”.
4. With `Daylight Auto`, terrain is checked along the whole bench path. If terrain is reached before a later bench starts, that section can shorten the terrace stack or skip the remaining benches.
5. `SectionSet.Status` reports `bench=left/right/both`, `benchSections=N`, and daylight-specific counters such as `benchDayAdj=N` and `benchDaySkip=N`. `BenchSummaryRows` also report whether the configured side is `single` or `multi`.
6. Bench output is part of the open section wire contract, so downstream `CorridorLoft` and grading surfaces consume the expanded profile automatically.

## 6B. Cross Section Viewer

`Cross Section Viewer` is the first dedicated 2D station-review panel for `SectionSet`.

### Current Scope

1. It reads section geometry directly from `SectionSet`.
2. It renders one station at a time in a separate 2D viewer instead of asking the user to interpret the section only in 3D.
3. It can follow `SectionSlice` and `SectionStructureOverlay` selection from the tree or 3D view.
4. It can optionally draw structure overlay wires on top of the base section linework.

### Main Controls

| Option | Meaning | How to use it |
|---|---|---|
| `Section Set` | Chooses the `SectionSet` to inspect. | Use this when multiple section sets exist in one document. |
| `Station` | Chooses one generated section station. | This is the main selector for the active cross-section. |
| `Sync with 3D selection` | Follows `SectionSlice` or `SectionStructureOverlay` selection automatically. | Keep this enabled for the recommended hybrid workflow. |
| `Show structure overlays` | Toggles structure overlay linework in the 2D viewer. | Turn this off when you only want to read the road/earthwork section shape. |
| `Show labels` | Shows component labels, station title, and any remaining in-graphic notes. | Keep this on during review and turn it off only when you want a very clean line-only view. |
| `Show dimensions` | Shows section width dimensions for the current station. | Keeps the overall width dimension and any active drawing-rule dimensions in the lower band. |
| `Show diagnostics` | Expands the lower summary panel with component/bench/structure/daylight report rows and status-derived tokens. | Use this when checking bench/daylight/structure behavior without opening raw object properties. |
| `Show typical components` | Shows labels and guides for `Typical Section` components such as `lane`, `shoulder`, `ditch`, and `berm`. | Turn this off when you want to isolate slope/daylight interpretation only. |
| `Show side-slope components` | Shows labels and guides for `side_slope`, `cut_slope`, `fill_slope`, and `bench` rows. | Useful when checking earthwork transitions without the standard-section overlay. |
| `Show daylight markers` | Shows terrain-connection markers and labels for daylight rows. | Turn this off when the slope-end markers clutter the section drawing. |
| `Use Selected Section` | Forces the viewer to adopt the currently selected `SectionSet`, `SectionSlice`, or `SectionStructureOverlay`. | Fastest way to jump from 3D context into 2D review. |
| `Refresh Context` | Reloads available section sets and current station rows. | Use this after regenerating sections. |
| `Previous` / `Next` | Moves to the neighboring station in the active set. | Useful for stepping through a corridor station by station. |
| `Fit View` | Re-frames the current 2D cross-section drawing. | Use this after panning or zooming. |
| `Export PNG` | Saves the currently rendered section scene as a PNG image. | Use this for quick review snapshots or issue discussions. |
| `Export SVG` | Saves the current section as a vector SVG built from the viewer payload. | Use this when you want a lightweight scalable review graphic. |
| `Export Sheet SVG` | Saves a print-style SVG sheet with the section drawing, title block, and review summary. | Use this when you want a cleaner review sheet for markup or sharing. |

### Practical Notes

1. This first version focuses on `station navigation + clean 2D linework + structure overlay`.
2. Bench and side-slope breakpoints are shown through the same `SectionSet` wire that downstream grading uses.
3. The dashed vertical marker is the roadway centerline in section space.
4. `Show typical components`, `Show side-slope components`, and `Show daylight markers` let you isolate the three main section scopes.
5. `Show diagnostics` expands the lower summary with payload/report rows derived from `SectionSet` result contracts.
6. `Show dimensions` keeps the lower-band width annotation strategy used by the viewer and SVG exports.
7. `Export PNG` writes the current scene as rendered, `Export SVG` writes a compact vector export, and `Export Sheet SVG` writes a print-style review sheet with a summary panel.
8. More detailed engineering dimensions are still future work in the viewer roadmap.

## 6C. Typical Section

`Typical Section` is the component-based editor for finished-grade top-profile composition.

### CSV Options

| Option | Meaning | How to use it |
|---|---|---|
| `Preset` | Built-in starter configuration such as `2-Lane Rural`, `Urban Complete Street`, or `Road With Ditch`. | Choose a preset when you want a fast starting point before manual edits. |
| `Load Preset` | Loads the selected built-in preset into the component table. | Useful when you want to start from a known cross-section pattern instead of a blank table. |
| `Component CSV` | Path to the typical-section component CSV. | Select one of the sample files or your own CSV. |
| `Browse CSV` | Opens a file chooser for a typical-section CSV. | Recommended first step for sample-driven testing. |
| `Load CSV` | Reads the CSV and fills the component table. | Review or adjust rows before `Apply`. |
| `Save Component CSV` | Writes the current component table back to CSV. | Use when you want to keep an edited template as a reusable file. |
| `Pavement CSV` | Path to the pavement-layer CSV for the same typical section. | Use when you want to track pavement thickness data with the section template. |
| `Pavement Preset` | Built-in pavement-layer starter stack such as `Asphalt Basic`, `Asphalt Thin`, or `Concrete Road`. | Use this when you want to fill the pavement-layer table quickly without a separate CSV file. |
| `Load Pavement Preset` | Loads the selected pavement-layer preset into the pavement table. | Best for quick trials before refining layer thicknesses manually or saving them to CSV. |
| `Browse Pavement CSV` | Opens a file chooser for a pavement-layer CSV. | Select the sample pavement CSV or your own layer stack file. |
| `Load Pavement CSV` | Reads the pavement CSV and fills the lower pavement table. | Review or adjust layers before `Apply`. |
| `Save Pavement CSV` | Writes the current pavement-layer table back to CSV. | Use when you want to reuse the same pavement stack in another template. |
| `Apply` | Saves the component rows into the active `TypicalSectionTemplate`. | Main execution button. |

### Editing Buttons

| Option | Meaning | How to use it |
|---|---|---|
| `Add Lane` / `Add Shoulder` / `Add Curb` / `Add Ditch` / `Add Berm` | Inserts a pre-filled component row with sensible defaults. | Fastest way to build a section without starting from a blank row. |
| `Add Row` | Adds a blank component row. | Use for uncommon component combinations or detailed manual input. |
| `Remove Row` | Removes the selected component row. | If no row is selected, remove the last row. |
| `Move Up` / `Move Down` | Reorders the selected component row in the table. | Useful when the visual build order should change without retyping `Order`. |
| `Mirror Left -> Right` | Copies the selected left-side row to the right side. | Best for lane/shoulder/gutter/ditch/berm rows when building symmetric sections. |
| `Mirror Right -> Left` | Copies the selected right-side row to the left side. | Use for the reverse direction when the right side is already defined. |
| `Sort by Order` | Sorts rows by `Order`, then side/id. | Use after large edits or imports to restore predictable build order. |
| `Add Layer` / `Remove Layer` | Adds or removes pavement-layer rows. | Use after setting up the top profile when pavement data should also be tracked. |

### Supported CSV Columns

| Column | Meaning |
|---|---|
| `Id` | Component identifier |
| `Type` | `lane`, `shoulder`, `median`, `sidewalk`, `bike_lane`, `curb`, `green_strip`, `gutter`, `ditch`, `berm` |
| `Side` | `left`, `right`, `center`, `both` |
| `Width` | Component width |
| `CrossSlopePct` | Cross slope (%) |
| `Height` | Vertical step / sag depth depending on component |
| `ExtraWidth` | Secondary width used by advanced components such as curb face run, ditch bottom width, or berm taper width |
| `BackSlopePct` | Secondary slope used by advanced components such as curb top/back slope, ditch outer slope, or berm taper slope |
| `Offset` | Additional local lateral offset before the component |
| `Order` | Per-side build order |
| `Enabled` | Boolean enable flag |

### Sample CSV Files

- `tests/samples/typical_section_basic_rural.csv`
- `tests/samples/typical_section_urban_complete_street.csv`
- `tests/samples/typical_section_with_ditch.csv`
- `tests/samples/typical_section_pavement_basic.csv`

### Current Notes

1. `curb` currently creates a vertical step plus top width.
2. `curb` also uses `ExtraWidth` and `BackSlopePct` for face/top shaping.
3. `ditch` now uses `ExtraWidth` for flat-bottom width and `BackSlopePct` for the outer slope.
4. `berm` now uses `ExtraWidth` and `BackSlopePct` for outer taper behavior.
5. Mid-slope earthwork benching is now handled in `Generate Sections` side-slope controls, not as a `Typical Section` top-profile component type.
6. Pavement layers are currently data-only and tracked as total thickness/result metadata.
7. The panel now includes a `Summary` group that reports current component count, top width, edge types, and pavement total thickness before `Apply`.
8. Type-aware tooltips and cell tinting are used to show whether `CrossSlopePct` or `Height` is the more important field for each component type.
7. To consume the template in actual section generation, use `Generate Sections` with `Use Typical Section Template`.

## Suggested Reading Order
1. Start with [Quick Start](Quick-Start).
2. Use [Workflow](Workflow) for command order.
3. Use this page when you need field-by-field option meaning.
4. Use [Troubleshooting](Troubleshooting) when sampled EG/FG or structure-aware output is incomplete or inconsistent.

---
Last verified with commit: `<fill-after-release>`
