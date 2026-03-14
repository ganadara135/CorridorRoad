# CSV Format

This page defines CSV input format for point cloud and alignment import.

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

> [Screenshot Needed] PointCloud DEM import panel with valid CSV selected.
> Suggested file: `wiki-csv-pointcloud-import-panel.png`

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

> [Screenshot Needed] Alignment CSV import result (geometry over terrain).
> Suggested file: `wiki-csv-alignment-import-result.png`

## 3. Import Validation Checklist
1. Header names match exactly.
2. Numeric fields are finite values.
3. Alignment lies within point cloud spatial extent.
4. Coordinate mode (`Local`/`World`) is consistent for terrain usage.

## 4. Common Data Issues
- Sparse point cloud causes holes or no-data cells.
- Alignment outside terrain extent causes EG blanks.
- Non-numeric text in numeric columns causes row skips.
- Mixed coordinate frames (local/world mismatch) produce shifted results.

---
Last verified with commit: `<fill-after-release>`
