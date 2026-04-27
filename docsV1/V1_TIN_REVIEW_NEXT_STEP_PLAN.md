# CorridorRoad V1 TIN Review Next Step Plan

Date: 2026-04-24
Branch: `v1-dev`
Status: Active follow-up plan, Phase H-J alignment adapter wiring complete
Depends on:

- `docsV1/V1_MASTER_PLAN.md`
- `docsV1/V1_TIN_CORE_IMPLEMENTATION_PLAN.md`
- `docsV1/V1_TIN_ENGINE_PLAN.md`
- `docsV1/V1_TIN_SAMPLING_CONTRACT.md`

## 1. Purpose

This document defines the next development sequence after the first usable TIN path:

- CSV point cloud selection
- CSV point rows converted into `TINSurface`
- TIN review/result flow opened from the unified `TIN` panel
- XY sampling verified through `TinSamplingService`

The next goal is to make the TIN review flow useful for real project checking before moving into section, drainage, and earthwork consumers.

## 2. Current Baseline

Completed baseline:

- `TINSurface` result contract exists
- `TINBuildService.build_from_csv()` builds a regular point-lattice TIN
- `tests/samples/pointcloud_utm_realistic_hilly.csv` builds into 14,641 vertices and 28,800 triangles
- `tests/samples/pointcloud_tin_mountain_valley_plain.csv` provides a richer terrain sample with mountains, valley, and plain areas
- `TinSamplingService.sample_xy()` samples TIN triangles
- the unified `TIN` panel can select a CSV/sample source and build the base TIN
- `TIN Review` shows summary text, quality rows, provenance rows, and one XY probe
- `TIN Review` now derives source, extents, spacing, and probe extent status from the shared review summary helper
- `TINMeshPreviewMapper` can create a lightweight `Mesh::Feature` preview from `TINSurface` triangles when a FreeCAD document is available
- `TinSectionSamplingService` samples TIN elevations across section offsets using an explicit station/offset-to-XY adapter
- `Cross Section Viewer` can include TIN section terrain sample rows in its Terrain Review table
- `Cross Section Viewer` can draw sampled TIN terrain rows as an inline section polyline preview
- `Cross Section Viewer` can derive the TIN station/offset adapter from `AlignmentEvaluationService` when an `AlignmentModel` is available

Known limitations:

- the review summary is improved but still text-oriented
- section terrain sampling is drawn as a lightweight viewer polyline, not yet as a full CAD section object
- drainage and earthwork consumers are not yet connected to the CSV-built TIN

## 3. Development Strategy

Keep the next slice review-oriented.

Do not start breakline enforcement, LandXML import, volume calculation, or full Delaunay triangulation yet.

The practical order should be:

1. make the review panel easier to trust
2. optionally generate a lightweight FreeCAD mesh preview
3. connect TIN sampling to the first engineering consumer

## 4. Phase H: TIN Review Information Panel

Status: Complete

Goal:

- make the TIN review panel clearly show whether the selected CSV built the expected surface

Scope:

- show source CSV path
- show vertex count and triangle count
- show X min, X max, Y min, Y max, Z min, Z max
- show X spacing and Y spacing
- show current probe X/Y
- show whether probe X/Y is inside the TIN XY extent
- show no-hit guidance when the probe is outside the surface range

Implementation notes:

- read extent and spacing values from `TINSurface.quality_rows`
- keep the source path from `TINSurface.provenance_rows` or `source_refs`
- do not duplicate sampling logic inside the viewer
- keep `TinSamplingService` as the only XY sampling authority

Suggested files:

- `freecad/Corridor_Road/v1/ui/viewers/tin_review_view.py`
- `freecad/Corridor_Road/v1/commands/cmd_review_tin.py`
- `freecad/Corridor_Road/v1/services/mapping/tin_review_summary.py`
- `tests/contracts/v1/test_tin_review_command.py`

Acceptance criteria:

- selected CSV source is visible in the review panel
- extents and spacing are visible without searching the quality table
- probe result clearly says `inside extent` or `outside extent`
- outside-extent no-hit gives a useful message
- existing TIN review tests still pass

## 5. Phase I: FreeCAD Mesh Preview Output

Status: Complete

Goal:

- let the user visually confirm that the CSV-built TIN exists as a 3D triangulated surface

Scope:

- create a lightweight `Mesh::Feature` or equivalent preview object from `TINSurface`
- use TIN vertices and triangle rows directly
- name the object from the surface id or CSV stem
- avoid making the mesh preview the source of truth
- keep `TINSurface` as the source of truth

Implementation notes:

- this should be an optional preview action, not required for sampling
- if mesh generation fails, the review panel should still work
- avoid writing the generated mesh back into the TIN data contract

Suggested files:

- `freecad/Corridor_Road/v1/services/mapping/tin_mesh_preview_mapper.py`
- `freecad/Corridor_Road/v1/commands/cmd_review_tin.py`
- `tests/contracts/v1/test_tin_mesh_preview_mapper.py`

Acceptance criteria:

- CSV-built `TINSurface` can produce a mesh preview object in a FreeCAD document
- mesh facet count matches `TINSurface.triangle_rows`
- review still works without GUI or document mesh creation
- tests can validate mapping without requiring the full GUI

## 6. Phase J: First Engineering Consumer

Status: Terrain Polyline Preview Complete

Goal:

- prove the built TIN can support downstream road-design workflows

Recommended first consumer:

- section terrain line extraction

Reason:

- section extraction is simpler than drainage flow analysis
- it directly validates station/offset sampling
- it becomes useful for corridor, earthwork, and drainage later

Scope:

- accept evaluated station rows or an explicit station/offset adapter
- sample TIN at offsets across a section
- return terrain profile rows
- report no-hit rows explicitly

Implemented initial slice:

- `TinSectionSamplingService.sample_offsets()` accepts a `TINSurface`, station, offset list, and explicit station/offset-to-XY adapter
- each output row includes station, offset, x, y, z, status, face id, confidence, and notes
- no-hit and adapter-error rows keep `z=None` and never fall back to zero elevation
- overall result status reports `ok`, `partial`, `no_hit`, `error`, or `empty`
- `Cross Section Viewer` appends `tin_section_summary` and `tin_section_sample` rows to Terrain Review when a TIN surface and adapter are available
- when a TIN exists but no station/offset adapter is available, the viewer reports a `tin_section_adapter` row instead of silently pretending terrain was sampled
- TIN hit rows are promoted into `SectionGeometryRow(kind="existing_ground_tin")`
- no-hit rows split the terrain polyline into separate segments instead of connecting across missing terrain
- `Cross Section Viewer` renders section geometry rows in a lightweight inline polyline preview
- `Cross Section Viewer` now prefers an explicit adapter, then an `AlignmentModel` adapter, then station rows with x/y as fallback

Suggested files:

- `freecad/Corridor_Road/v1/services/evaluation/tin_section_sampling_service.py` - complete
- `freecad/Corridor_Road/v1/commands/cmd_view_sections.py` - complete
- `freecad/Corridor_Road/v1/ui/viewers/cross_section_viewer.py` - complete
- `freecad/Corridor_Road/v1/models/output/section_output.py`
- `tests/contracts/v1/test_tin_section_sampling_service.py` - complete
- `tests/contracts/v1/test_section_command_bridge.py` - complete

Acceptance criteria:

- [x] a known TIN can be sampled across a section line
- [x] output rows include offset, x, y, z, status, and face id
- [x] no-hit rows do not become zero elevation
- [x] station/offset conversion remains outside TIN interpolation logic
- [x] sampled terrain rows are wired into the Cross Section Viewer Terrain Review payload
- [x] sampled terrain rows are drawn as a graphical terrain polyline
- [x] no-hit rows break geometry segments instead of connecting through missing terrain
- [x] Cross Section/TIN sampling can use `AlignmentEvaluationService.station_offset_adapter()`

## 7. Test Command Guidance

Preferred FreeCAD command-line location:

- `D:\Program Files\FreeCAD 1.0\bin\FreeCADCmd.exe`

Focused validation commands:

```powershell
& "D:\Program Files\FreeCAD 1.0\bin\FreeCADCmd.exe" -c "exec(open(r'tests\contracts\v1\test_tin_build_service.py', 'r', encoding='utf-8').read())"
& "D:\Program Files\FreeCAD 1.0\bin\FreeCADCmd.exe" -c "exec(open(r'tests\contracts\v1\test_tin_sampling_service.py', 'r', encoding='utf-8').read())"
& "D:\Program Files\FreeCAD 1.0\bin\FreeCADCmd.exe" -c "exec(open(r'tests\contracts\v1\test_tin_section_sampling_service.py', 'r', encoding='utf-8').read())"
& "D:\Program Files\FreeCAD 1.0\bin\FreeCADCmd.exe" -c "exec(open(r'tests\contracts\v1\test_tin_review_command.py', 'r', encoding='utf-8').read())"
& "D:\Program Files\FreeCAD 1.0\bin\FreeCADCmd.exe" -c "exec(open(r'tests\contracts\v1\test_tin_mesh_preview_mapper.py', 'r', encoding='utf-8').read())"
& "D:\Program Files\FreeCAD 1.0\bin\FreeCADCmd.exe" -c "exec(open(r'tests\contracts\v1\test_pointcloud_tin_main_command.py', 'r', encoding='utf-8').read())"
```

Add new focused tests as each phase is implemented.

For test files without a `__main__` runner, use an explicit contract runner:

```powershell
& "D:\Program Files\FreeCAD 1.0\bin\FreeCADCmd.exe" -c "ns={}; exec(open(r'tests\contracts\v1\test_section_command_bridge.py', 'r', encoding='utf-8').read(), ns); [fn() for name, fn in sorted(ns.items()) if name.startswith('test_') and callable(fn)]; print('[PASS] v1 section command bridge contract tests completed.')"
```

## 8. Implementation Order

Recommended next coding order:

1. [x] Add TIN extent helpers for review payloads
2. [x] Show source, extents, spacing, and probe extent status in TIN Review
3. [x] Improve no-hit messages for outside-extent probes
4. [x] Add tests for review payload extent behavior
5. [x] Add optional TIN-to-FreeCAD mesh preview mapper
6. [x] Add tests for mesh preview mapping
7. [x] Add first section terrain sampling service
8. [x] Wire sampled TIN terrain rows into Cross Section Viewer
9. [x] Draw sampled TIN terrain as a section polyline
10. [x] Prefer AlignmentModel adapter for Cross Section/TIN station-offset sampling
11. [ ] Connect TIN section terrain rows to the first earthwork calculation slice

## 9. Stop Conditions

Pause and realign if:

- the review panel starts owning sampling or triangulation logic
- mesh preview becomes required for `TINSurface` sampling
- DEM/grid workflow terminology starts replacing TIN terminology
- a downstream service treats no-hit as zero elevation
- Phase H expands into full TIN editing before review clarity is solved

## 10. Definition of Done for Next Slice

The next slice is done when:

- users can open a CSV TIN and immediately understand its range, spacing, source, and sample status
- outside-range probes are clearly explained
- tests cover CSV-backed review payload behavior
- optional mesh preview can be created without making the mesh the source of truth
- section terrain sampling is available without reworking the TIN core
- the Cross Section Viewer can show TIN terrain sample rows in its Terrain Review table
- the Cross Section Viewer can draw a lightweight TIN terrain polyline
- the implementation is ready to connect sampled TIN terrain to earthwork calculations
