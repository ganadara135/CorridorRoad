<!-- SPDX-License-Identifier: LGPL-2.1-or-later -->
<!-- SPDX-FileNotice: Part of the Corridor Road addon. -->

# CSV Format

This page defines CSV input format for point cloud, alignment, and structure import.

## File Encoding and Delimiter
- Recommended encoding: UTF-8
- Delimiter: comma (`,`)
- Decimal separator: dot (`.`)
- Keep one header row at top
- Avoid empty header names

## 1. Point Cloud CSV (DEM Source)

Required header:
`easting,northing,elevation`

Example:
```csv
easting,northing,elevation
352000.000,4169000.000,116.000
352005.000,4169000.000,116.021
352010.000,4169000.000,116.041
```

Rules:
- `easting`: float (X)
- `northing`: float (Y)
- `elevation`: float (Z)
- Recommended regular XY sampling for stable DEM mesh generation
- UTM coordinates are supported
- Keep enough density for mesh continuity in design area

Recommended sample file:
- `tests/samples/pointcloud_utm_realistic_hilly.csv`

![PointCloud DEM import panel with valid CSV selected](images/wiki-csv-pointcloud-import-panel.png)

## 2. Alignment CSV

Required header:
`E,N,Radius,TransitionLs`

Example:
```csv
E,N,Radius,TransitionLs
352060.000,4169055.000,0.0,0.0
352130.000,4169125.000,180.0,30.0
352210.000,4169200.000,220.0,35.0
```

Rules:
- `E`: float (IP easting)
- `N`: float (IP northing)
- `Radius`: float (`0` for tangent/no curve)
- `TransitionLs`: float (`0` allowed)
- At least 2 valid rows are required
- Keep alignment extents inside terrain extents for EG sampling stability

Recommended sample file:
- `tests/samples/alignment_utm_realistic_hilly.csv`

![Alignment CSV import result](images/wiki-csv-alignment-import-result.png)

## 2A. Profile FG CSV

Use this format with `Edit Profiles -> Import FG CSV` when you want to start from manual FG values instead of generating FG from `Edit PVI`.

Recommended header:
`Station,FG`

Also accepted header aliases:
- station column: `Station`, `Sta`, `Chainage`, `PK`, `KP`, `Distance`
- FG column: `FG`, `ElevFG`, `DesignElevation`, `DesignGrade`, `FinishedElevation`, `Z`, `Elevation`

Example:
```csv
Station,FG
0.000,118.200
40.000,118.550
80.000,118.980
120.000,119.430
```

Alias example:
```csv
PK,DesignElevation
0.000,118.000
50.000,118.350
100.000,118.820
150.000,119.260
```

Rules:
- one station column and one FG column are required
- station values should be numeric and increasing for readability
- duplicate station rows are allowed in the file, but the last one wins during import
- matching stations update existing profile rows
- stations not yet in the table are appended, then the table is re-sorted
- manual FG import works best after `Fill Stations from Stationing`, but it can also create rows in an empty table

Recommended sample files:
- `tests/samples/profile_fg_manual_import_basic.csv`
- `tests/samples/profile_fg_manual_import_aliases.csv`

Practical notes:
1. If `FG from VerticalAlignment` is currently enabled, the panel asks whether it should switch to manual FG first.
2. `FG Wizard` is the companion tool for generating manual FG values without preparing a CSV file.
3. `Sort by Station` now preserves rows that have FG but blank EG.

## 3. Structure CSV

Recommended header:
`Id,Type,StartStation,EndStation,CenterStation,Side,Offset,Width,Height,BottomElevation,Cover,RotationDeg,BehaviorMode,GeometryMode,TemplateName,WallThickness,FootingWidth,FootingThickness,CapHeight,CellCount,CorridorMode,CorridorMargin,Notes,ShapeSourcePath,ScaleFactor,PlacementMode,UseSourceBaseAsBottom`

Example:
```csv
Id,Type,StartStation,EndStation,CenterStation,Side,Offset,Width,Height,BottomElevation,Cover,RotationDeg,BehaviorMode,GeometryMode,TemplateName,WallThickness,FootingWidth,FootingThickness,CapHeight,CellCount,CorridorMode,CorridorMargin,Notes,ShapeSourcePath,ScaleFactor,PlacementMode,UseSourceBaseAsBottom
CULV-T01,culvert,120.000,150.000,135.000,center,0.000,6.000,2.500,103.200,1.200,0.000,section_overlay,template,box_culvert,0.350,0.000,0.000,0.200,2,notch,0.000,Two-cell box culvert template,,1.000,,
RW-T01,retaining_wall,265.000,340.000,302.500,right,8.000,0.600,4.000,101.800,0.000,0.000,assembly_override,template,retaining_wall,0.450,3.200,0.500,0.150,1,split_only,0.000,Right-side retaining wall template,,1.000,,
EXT-CULV-01,culvert,120.000,150.000,135.000,center,0.000,6.000,2.500,103.200,0.000,0.000,section_overlay,external_shape,,0.000,0.000,0.000,0.000,1,notch,0.000,Replace with your local STEP file,C:/replace-with-your-models/culvert_box.step,1.000,center_on_station,true
EXT-ABUT-01,abutment_zone,470.000,515.000,492.500,both,0.000,14.000,5.000,103.800,0.000,0.000,assembly_override,external_shape,,0.000,0.000,0.000,0.000,1,skip_zone,0.000,Replace with your local FCStd object path,C:/replace-with-your-models/bridge_parts.FCStd#AbutmentBlock,1.000,center_on_station,true
```

Rules:
- `Id`: recommended string identifier
- `Type`: one of `crossing`, `culvert`, `retaining_wall`, `bridge_zone`, `abutment_zone`, `other`
- `StartStation`, `EndStation`, `CenterStation`: numeric station values
- `Side`: one of `left`, `right`, `center`, `both`
- `Width`, `Height`: non-negative numeric values
- `BehaviorMode`: one of `tag_only`, `section_overlay`, `assembly_override`
- `GeometryMode`: one of `box`, `template`, `external_shape`
- `TemplateName`: currently `box_culvert`, `utility_crossing`, `retaining_wall`, `abutment_block`
- `WallThickness`, `FootingWidth`, `FootingThickness`, `CapHeight`, `CellCount`: template-specific fields
- `CorridorMode`: one of `none`, `split_only`, `skip_zone`, `notch`
- `CorridorMargin`: optional non-negative corridor envelope margin
- `Notes`: optional free text
- `ShapeSourcePath`: local `.step`, `.brep`, or `.FCStd#ObjectName` source path when `GeometryMode=external_shape`
- `ScaleFactor`: optional uniform scale for external geometry
- `PlacementMode`: currently `center_on_station` or `start_on_station`
- `UseSourceBaseAsBottom`: `true`/`false` flag for external source Z anchoring

Recommended sample file:
- `tests/samples/structure_utm_realistic_hilly.csv`
- `tests/samples/structure_utm_realistic_hilly_notch.csv`
- `tests/samples/structure_utm_realistic_hilly_template.csv`
- `tests/samples/structure_utm_realistic_hilly_external_shape.csv`
- See `docs/PRACTICAL_SAMPLE_SET.md` for the maintained starter/mixed sample grouping.

Practical notes:
1. Run `Generate Stations` before using `Edit Structures`, even if the CSV contains valid station values.
2. `culvert`, `crossing`, `bridge_zone`, and `abutment_zone` are usually zone-type records that affect both section sides.
3. `retaining_wall` usually makes sense on only one side.
4. `tag_only` is the safest mode when you want structure-aware station tags without changing section behavior.
5. Leave `GeometryMode` empty if you want strict backward-compatible `box` behavior.
6. Use `template / box_culvert` when you want culvert display solids and `Structure Sections` overlays to show wall and cell layout.
7. Use `template / retaining_wall` when you want footing + stem display and overlay shapes.
8. Use `external_shape` when you already have a structure model in `STEP`, `BREP`, or `FCStd` format and want to place that geometry directly.
9. For `FCStd`, use `ShapeSourcePath` in the form `C:/path/model.FCStd#ObjectName`.
10. The repository does not currently bundle sample `.step`, `.brep`, or `.FCStd` files, so the sample `ShapeSourcePath` values are placeholders that must be replaced before use.
11. The upper structure table now defaults to a compact view; use `Selected Structure Details` for most advanced edits.
12. The panel now includes quick-add helpers, structure cloning, grouped column toggles, and built-in structure presets.

> [Screenshot Needed] Edit Structures panel loading a structure CSV file.
> Suggested file: `wiki-csv-structure-import-panel.png`

## 3A. Structure Station-Profile CSV

This is an advanced companion CSV format for variable-size structures.

Current workflow:
- `Edit Structures` now supports a two-table workflow.
- Load the base structure CSV first.
- Then use `Browse Profile CSV` -> `Load Profile CSV`.
- The lower table shows the station-profile rows for the currently selected structure.
- The lower table also supports `Sort by Station`, `Duplicate Profile Row`, `Add Midpoint`, and `Delete All for Selected`.
- The `Profile Preset` controls above the lower table can create starter control points directly from the selected structure row.

Recommended header:
`StructureId,Station,Offset,Width,Height,BottomElevation,Cover,WallThickness,FootingWidth,FootingThickness,CapHeight,CellCount`

Example:
```csv
StructureId,Station,Offset,Width,Height,BottomElevation,Cover,WallThickness,FootingWidth,FootingThickness,CapHeight,CellCount
CULV-V01,120.000,0.000,4.000,2.000,103.300,0.000,0.280,0.000,0.000,0.050,1
CULV-V01,150.000,0.000,6.000,2.600,103.100,0.000,0.320,0.000,0.000,0.120,2
CULV-V01,180.000,0.000,3.800,1.900,102.950,0.000,0.260,0.000,0.000,0.050,1
RW-V01,265.000,7.500,0.550,2.800,101.900,0.000,0.320,2.200,0.450,0.120,1
RW-V01,305.000,8.250,0.700,5.000,101.650,0.000,0.420,3.000,0.600,0.220,1
RW-V01,345.000,9.000,0.600,3.400,101.450,0.000,0.360,2.400,0.500,0.120,1
```

How it is used:
1. Each `StructureId` must match a row in the main structure CSV.
2. At least two profile points are recommended for a variable structure.
3. Profile rows for the same structure should be in ascending station order.
4. Duplicate stations for the same structure should be avoided.

Current runtime consumption:
1. 3D structure display uses station-profile values.
2. `Structure Sections` overlay objects use station-profile values.
3. Section overrides and earthwork use station-profile values.
4. Corridor `notch` handling uses station-profile values.

Current limits:
1. `CellCount` is treated as a step/nearest value, not a continuously interpolated value.
2. `skip_zone` and `split_only` still follow the base structure span (`StartStation`/`EndStation`) rather than profile-point-derived span changes.
3. The current runtime builds variable structures as profile-driven segments, not as a fully continuous taper loft.

Recommended sample files:
- `tests/samples/structure_utm_realistic_hilly_station_profile_headers.csv`
- `tests/samples/structure_utm_realistic_hilly_station_profile_points.csv`
- `tests/samples/structure_utm_realistic_hilly_mixed.csv`
- `tests/samples/structure_utm_realistic_hilly_mixed_profile_points.csv`

> [Screenshot Needed] Structure Sections overlays showing station-profile-driven size changes.
> Suggested file: `wiki-csv-structure-station-profile-overlays.png`

## 3B. Typical Section CSV

Recommended component header:
`Id,Type,Shape,Side,Width,CrossSlopePct,Height,ExtraWidth,BackSlopePct,Offset,Order,Enabled`

`Shape` is currently used by `ditch` rows:
- `v`
- `u`
- `trapezoid`

Backward compatibility:
- if a ditch row omits `Shape`, runtime infers `v` when `ExtraWidth <= 0`
- if a ditch row omits `Shape`, runtime infers `trapezoid` when `ExtraWidth > 0`
- `Shape=u` currently builds a polyline-approximated rounded ditch and ignores `ExtraWidth` / `BackSlopePct`

`Typical Section` now supports direct CSV import.

Current workflow:
1. Open `Typical Section`
2. Either choose a built-in `Preset` or use `Browse CSV`
3. `Load CSV`
4. Use quick-add buttons, mirror buttons, and row-move buttons if needed
5. Review the `Summary` panel
6. `Apply`

Recommended header:
`Id,Type,Shape,Side,Width,CrossSlopePct,Height,ExtraWidth,BackSlopePct,Offset,Order,Enabled`

Example:
```csv
Id,Type,Shape,Side,Width,CrossSlopePct,Height,ExtraWidth,BackSlopePct,Offset,Order,Enabled
LANE-L,lane,,left,3.500,2.0,0.000,0.000,0.000,0.000,10,true
SHL-L,shoulder,,left,1.500,4.0,0.000,0.000,0.000,0.000,20,true
GUT-L,gutter,,left,0.800,6.0,0.000,0.000,0.000,0.000,30,true
DITCH-L,ditch,trapezoid,left,2.000,2.0,1.000,0.700,-10.000,0.000,40,true
BERM-L,berm,,left,1.500,0.0,0.000,1.000,8.000,0.000,50,true
LANE-R,lane,,right,3.500,2.0,0.000,0.000,0.000,0.000,10,true
SHL-R,shoulder,,right,1.500,4.0,0.000,0.000,0.000,0.000,20,true
```

Recommended sample files:
- `tests/samples/typical_section_basic_rural.csv`
- `tests/samples/typical_section_ditch_trapezoid.csv`
- `tests/samples/typical_section_ditch_u.csv`
- `tests/samples/typical_section_ditch_v.csv`
- `tests/samples/typical_section_urban_complete_street.csv`
- `tests/samples/typical_section_with_ditch.csv`
- `tests/samples/typical_section_pavement_basic.csv`

Current notes:
1. `TypicalSectionTemplate` defines the finished-grade top profile.
2. `AssemblyTemplate` still provides corridor depth, side slopes, and daylight defaults.
3. `Save Component CSV` can export the edited component table back to CSV.
4. The editor now supports built-in presets and quick-add component buttons for faster setup.
5. `ExtraWidth` and `BackSlopePct` are now part of the maintained component CSV contract.
6. Type-aware tooltips and cell tinting help distinguish slope-driven rows (`lane`, `shoulder`, `gutter`) from height-driven rows (`curb`, `ditch`).
7. When `Sections` uses a typical section, runtime should report `SectionSchemaVersion=2` and `TopProfileSource=typical_section`.
8. `Corridor` completion/status now reports source schema, top profile source, and points per section.

### 3C. Typical Section Pavement CSV

`Typical Section` also supports a first-pass pavement layer CSV.

Current workflow:
1. Open `Typical Section`
2. `Browse Pavement CSV`
3. `Load Pavement CSV`
4. Review/edit the pavement layer table if needed
5. Optionally use `Save Pavement CSV` to export the edited stack
6. `Apply`

Recommended header:
`Id,Type,Thickness,Enabled`

Example:
```csv
Id,Type,Thickness,Enabled
SURF,surface,0.050,true
BINDER,binder,0.070,true
BASE,base,0.200,true
SUBBASE,subbase,0.250,true
```

Recommended sample file:
- `tests/samples/typical_section_pavement_basic.csv`

Current notes:
1. Pavement layers are stored as data on `TypicalSectionTemplate`.
2. Current supported layer types are `surface`, `binder`, `base`, `subbase`, `subgrade`.
3. Current result fields include `PavementLayerCount`, `EnabledPavementLayerCount`, and `PavementTotalThickness`.
4. These values currently propagate to `SectionSet`, `Corridor`, and `Design Grading Surface`.
5. Pavement preview offset wires were removed; pavement data remains available through the stored layer rows and total thickness summary.

## 4. Import Validation Checklist
1. Header names match exactly.
2. Numeric fields are finite values.
3. Alignment lies within point cloud spatial extent.
4. Coordinate mode (`Local`/`World`) is consistent for terrain usage.
5. Structure station ranges fall inside the generated alignment/stationing range.

## 5. Common Data Issues
- Sparse point cloud causes holes or no-data cells.
- Alignment outside terrain extent causes EG blanks.
- Non-numeric text in numeric columns causes row skips.
- Mixed coordinate frames (local/world mismatch) produce shifted results.
- Structure CSV with invalid `Type`, `Side`, or `BehaviorMode` causes validation warnings.

## 6. DEM Cell Size Tuning

`CellSize` controls how the imported point cloud is sampled into the DEM grid.

How to interpret it:
- Smaller `CellSize` preserves more local terrain detail.
- Smaller `CellSize` also makes sparse areas more visible, which can leave holes or weak coverage in the DEM.
- Larger `CellSize` averages over a wider area and can reduce no-data gaps in sparse point clouds.
- Larger `CellSize` can help reduce blank or zero EG/profile values when the source point cloud is not dense enough.

When to increase `CellSize`:
1. EG values are blank at many stations.
2. Profile data contains long zero-value runs after DEM import.
3. The terrain mesh looks fragmented or contains many small holes.
4. Point spacing in the CSV is visibly wider than the current DEM cell size.

Tradeoff:
1. If `CellSize` is too small, terrain detail is preserved but coverage may be unstable.
2. If `CellSize` is too large, EG/profile coverage may improve, but the terrain becomes smoother and sharp features may be flattened.

Recommended tuning approach:
1. Start near the typical XY point spacing of the source CSV.
2. If EG/profile values contain many blanks or zeros, increase `CellSize` gradually.
3. Rebuild the terrain and regenerate profiles after each change.
4. Stop when coverage becomes stable without excessively flattening the terrain.

Practical note:
- If your point cloud spacing is irregular, it is usually safer to use a slightly larger `CellSize` than the smallest local spacing.
- For early testing, stable EG coverage is often more important than preserving every small terrain variation.

> [Screenshot Needed] PointCloud DEM task panel showing `CellSize` adjustment.
> Suggested file: `wiki-csv-dem-cellsize-tuning.png`

---
Last verified with commit: `<fill-after-release>`
