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

## 3. Structure CSV

Recommended header:
`Id,Type,StartStation,EndStation,CenterStation,Side,Offset,Width,Height,BottomElevation,Cover,RotationDeg,BehaviorMode,Notes`

Example:
```csv
Id,Type,StartStation,EndStation,CenterStation,Side,Offset,Width,Height,BottomElevation,Cover,RotationDeg,BehaviorMode,Notes
CULV-01,culvert,120.000,150.000,135.000,center,0.000,6.000,2.500,103.200,1.200,0.000,section_overlay,Box culvert crossing
RW-01,retaining_wall,265.000,340.000,302.500,right,8.000,0.600,4.000,0.000,0.000,0.000,assembly_override,Right-side retaining wall zone
```

Rules:
- `Id`: recommended string identifier
- `Type`: one of `crossing`, `culvert`, `retaining_wall`, `bridge_zone`, `abutment_zone`, `other`
- `StartStation`, `EndStation`, `CenterStation`: numeric station values
- `Side`: one of `left`, `right`, `center`, `both`
- `Width`, `Height`: non-negative numeric values
- `BehaviorMode`: one of `tag_only`, `section_overlay`, `assembly_override`
- `Notes`: optional free text

Recommended sample file:
- `tests/samples/structure_utm_realistic_hilly.csv`

Practical notes:
1. Run `Generate Stations` before using `Edit Structures`, even if the CSV contains valid station values.
2. `culvert`, `crossing`, `bridge_zone`, and `abutment_zone` are usually zone-type records that affect both section sides.
3. `retaining_wall` usually makes sense on only one side.
4. `tag_only` is the safest mode when you want structure-aware station tags without changing section behavior.

> [Screenshot Needed] Edit Structures panel loading a structure CSV file.
> Suggested file: `wiki-csv-structure-import-panel.png`

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
