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
| `CRS / EPSG` | Coordinate system identifier, for example `EPSG:5186`. | Use this when working with UTM or real-world survey coordinates. It is metadata plus a strong workflow hint for coordinate-sensitive tasks. |
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
3. Leave local origins at zero unless you deliberately want an offset local model.
4. Apply once and confirm imports behave correctly.
5. Lock the setup after the coordinate policy is confirmed.

### Practical Notes
1. If point cloud CSV is in UTM, `Project Setup` should usually be completed before `Import PointCloud DEM`.
2. If alignment and terrain appear shifted, check `Project Origin`, `Local Origin`, and `North Rotation` before changing other tools.
3. `Setup Status` is useful for team workflow, but it does not prevent generation commands by itself.

> [Screenshot Needed] Project Setup panel with coordinate fields filled.
> Suggested file: `wiki-menu-reference-project-setup.png`

## 2. Import PointCloud DEM

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

## 3. Edit Profiles

Use `Edit Profiles` to manage station-based EG/FG profile data.
This panel is where station lists, sampled EG values, manual FG values, and FG-from-VerticalAlignment behavior come together.

Important behavior:
1. The table stores `Station`, `EG`, `FG`, and computed `Delta`.
2. `Apply` can sample EG from the selected terrain before saving.
3. If `FG from VerticalAlignment` is enabled and a vertical alignment exists, the `FG` column becomes read-only and is regenerated from the vertical alignment.
4. If manual FG editing is used, the FG display wire is hidden to avoid showing stale geometry.

### Table Columns

| Column | Meaning | How to use it |
|---|---|---|
| `Station` | Station value along the alignment. | Required. At least 2 valid rows are needed to save a profile bundle. |
| `EG` | Existing ground elevation. | Can be filled from terrain sampling or edited manually. Blank EG values may later be saved as `0` if unresolved. |
| `FG` | Finished grade elevation. | Editable only in manual FG mode. Locked and auto-filled when `FG from VerticalAlignment` is enabled. |
| `Delta (FG-EG)` | Difference between FG and EG. | Read-only diagnostic field. |

### Buttons

| Option | Meaning | How to use it |
|---|---|---|
| `Add Row` | Adds one blank table row. | Use for manual editing. |
| `Remove Row` | Removes the selected row. | If no row is selected, the last row is removed. |
| `Sort by Station` | Sorts valid rows by station. | Use before saving if rows were manually edited out of order. |
| `Fill Stations from Stationing` | Replaces the table with `Stationing.StationValues`. | Use after `Generate Stations`. This is the fastest way to build the profile table. |
| `Fill FG from VerticalAlignment` | Fills FG values from the current `VerticalAlignment`. | Useful after editing PVIs. It only matters when a vertical alignment exists. |

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
6. Click `Apply`.

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

### PVI Table Columns

| Column | Meaning | How to use it |
|---|---|---|
| `PVI Station` | Station of the PVI point. | Required. Rows are sorted by station before use. |
| `PVI Elev` | Elevation at the PVI point. | Required. |
| `Curve Length` | Vertical curve length `L` at that PVI. | Use `0` for no vertical curve at that PVI. Positive values create symmetric vertical curves. |

### Generate FG Options

| Option | Meaning | How to use it |
|---|---|---|
| `Clamp overlapping vertical curves (auto adjust L)` | Automatically shortens curve lengths when adjacent curves would overlap or violate tangent spacing. | Recommended for interactive editing. Turn it off only when you want the tool to reject invalid geometry instead of adjusting it. |
| `Min Tangent` | Minimum required tangent length between adjacent vertical curves. | Increase this when you want to enforce a minimum straight grade segment between curves. |
| `Create ProfileBundle if missing` | Allows FG generation to create a profile bundle if one does not exist yet. | Keep enabled unless you want generation to fail when prerequisites are incomplete. |
| `Keep existing EG values (do not overwrite)` | Preserves current EG values in the profile bundle during FG generation. | Recommended in normal workflows because `Edit PVI` is for FG generation, not terrain resampling. |
| `Preview FG (console)` | Saves the current PVI table, resolves a station list, and prints sample FG elevations to the FreeCAD console. | Use for quick validation before writing data into the profile bundle. |
| `Generate FG Now (apply)` | Saves the vertical alignment, computes FG on the resolved stations, updates the profile bundle, and shows a completion dialog. | Main execution button. |

### Recommended Usage
1. Create or confirm stationing first.
2. Enter PVI rows in station order or click `Sort by Station`.
3. Use `Curve Length = 0` where you want simple grade breaks.
4. Keep `Clamp overlapping vertical curves` enabled unless you are intentionally checking invalid geometry.
5. Click `Generate FG Now (apply)`.
6. Return to `Edit Profiles` with `FG from VerticalAlignment` enabled if you want the profile table locked to the generated FG.

### Practical Notes
1. If no profile bundle exists, FG generation can create one and seed it from the resolved station list.
2. If no station list exists in either `ProfileBundle` or `Stationing`, FG generation cannot proceed.
3. `Keep existing EG values` does not resample terrain. It only protects existing EG data while FG is regenerated.
4. The completion dialog confirms station count and helps show that FG generation has actually finished.

> [Screenshot Needed] Edit PVI panel with PVI table and Generate FG options.
> Suggested file: `wiki-menu-reference-edit-pvi.png`

## 5. Edit Structures

Use `Edit Structures` after `Generate Stations`.
This panel creates or updates the `StructureSet` object that stores structure zones, structure station ranges, and simple 3D reference geometry.

Important behavior:
1. `StartStation`, `EndStation`, and `CenterStation` are station-combo values populated from `Stationing`.
2. `Type`, `Side`, and `BehaviorMode` are controlled lists to keep structure behavior predictable.
3. `Apply` writes the `StructureSet`, updates simple 3D solids, and links the result into `01_Inputs/Structures`.

### Main Controls

| Option | Meaning | How to use it |
|---|---|---|
| `Target StructureSet` | Chooses whether to edit an existing `StructureSet` or create a new one. | Use the existing set in a single-alignment workflow. Create a new one only when you intentionally want a separate structure dataset. |
| `CSV File` | Optional path to a structure CSV file. | Use it when bulk-loading structure records instead of typing rows manually. |
| `Browse CSV` | Opens a file chooser for structure CSV. | Recommended for standard sample/test workflows. |
| `Load CSV` | Reads the CSV and fills the structure table. | Review the table before `Apply`. |
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
| `Notes` | Free-form notes. | Use for documentation and later review. |

### Recommended Usage
1. Generate stations first.
2. Load `tests/samples/structure_utm_realistic_hilly.csv` or enter rows manually.
3. Use `tag_only` for reference structures and `section_overlay`/`assembly_override` only where section behavior should change.
4. Apply and verify that the `StructureSet` appears under `01_Inputs/Structures`.

### Practical Notes
1. A `retaining_wall` should usually use `left` or `right`, not `center`.
2. A `culvert` or `crossing` usually makes more sense with `center` or `both`.
3. If `BottomElevation` is empty, the display system falls back to centerline Z and `Cover`.
4. The 3D solids created here are reference geometry, not final corridor boolean geometry.

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
| `Buffer Before` | Adds an extra station before each structure start. | Useful when you want one section just before entering the structure zone. |
| `Buffer After` | Adds an extra station after each structure end. | Useful when you want one section just after leaving the structure zone. |
| `Add structure tags to child sections` | Adds tags and metadata to child sections at structure-related stations. | Keep enabled if you want labels and tree identification. |
| `Apply structure overrides` | Enables structure-type override logic during section build. | Turn this on when structure zones should constrain daylight/side-slope behavior. |

### Override Policy Summary

| Structure Type | Current Section Override Behavior |
|---|---|
| `crossing` | Affects both sides; keeps loft-safe stub points through the structure zone. |
| `culvert` | Affects both sides; disables daylight through the zone and keeps stub side points. |
| `retaining_wall` | Affects the declared side only; opposite side can remain normal. |
| `bridge_zone` | Affects both sides conservatively. |
| `abutment_zone` | Affects both sides conservatively. |
| `other` | No special type logic beyond the selected `BehaviorMode`. |

### Output To Expect
1. Standard section children continue to appear under `Sections`.
2. Structure overlay objects appear under `Structure Sections`.
3. `SectionSet.Status` reports merged structure count and override hit count.

> [Screenshot Needed] Generate Sections panel with StructureSet options expanded.
> Suggested file: `wiki-menu-reference-generate-sections-structures.png`

## Suggested Reading Order
1. Start with [Quick Start](Quick-Start).
2. Use [Workflow](Workflow) for command order.
3. Use this page when you need field-by-field option meaning.
4. Use [Troubleshooting](Troubleshooting) when sampled EG/FG or structure-aware output is incomplete or inconsistent.

---
Last verified with commit: `<fill-after-release>`
