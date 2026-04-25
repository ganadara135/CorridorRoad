# CorridorRoad V1 TIN Core Implementation Plan

Date: 2026-04-24
Branch: `v1-dev`
Status: Active implementation plan, Phase A-G first slice complete
Depends on:

- `docsV1/V1_MASTER_PLAN.md`
- `docsV1/V1_TIN_ENGINE_PLAN.md`
- `docsV1/V1_TIN_DATA_SCHEMA.md`
- `docsV1/V1_TIN_SAMPLING_CONTRACT.md`
- `docsV1/V1_IMPLEMENTATION_PHASE_PLAN.md`

## 1. Purpose

This document defines the near-term implementation plan for the first usable v1 TIN core.

It exists to turn the TIN design documents into a practical coding sequence focused on:

- normalized TIN surface data
- reliable XY elevation sampling
- explicit hit/no-hit/diagnostic behavior
- contract tests before UI work
- a thin review path after the core is trustworthy

## 2. Current Baseline

Current implementation state:

- `freecad/Corridor_Road/v1/services/evaluation/tin_sampling_service.py` exists
- `TinSamplingService.sample_xy()` now performs triangle-based XY sampling
- `TinSamplingService.sample_station_offset()` now delegates through an explicit station/offset adapter
- `TinSamplingService.station_offset_adapter_from_rows()` can build an adapter from evaluated station `station/x/y` rows
- `freecad/Corridor_Road/v1/models/result/tin_surface.py` defines the initial reusable TIN data contract
- `tests/contracts/v1/test_tin_sampling_service.py` covers the first sampling contract behavior
- `freecad/Corridor_Road/v1/commands/cmd_review_tin.py` builds and shows the thin TIN review payload
- `freecad/Corridor_Road/v1/ui/viewers/tin_review_view.py` provides a minimal review panel with one XY probe
- `freecad/Corridor_Road/commands/cmd_import_pointcloud_tin.py` now enters the v1 TIN review path with a safe fallback
- `tests/contracts/v1/test_tin_review_command.py` covers the thin review command behavior
- `freecad/Corridor_Road/v1/services/builders/tin_build_service.py` builds a first-slice `TINSurface` from CSV point input
- `tests/samples/pointcloud_utm_realistic_hilly.csv` is used as the first real TIN build sample
- `tests/contracts/v1/test_tin_build_service.py` verifies CSV point-cloud build counts, quality rows, and sampling compatibility
- `CorridorRoad_ImportPointCloudTIN` now opens a CSV file picker and passes the selected file into the v1 TIN review flow

## 3. Core Decision

Build the TIN core before building a full TIN UX.

The first UX should be a thin verification surface only after the core can answer simple sampling questions correctly.

Recommended emphasis:

- 70 percent core functionality
- 30 percent minimal review and diagnostics support

## 4. Initial Scope

The first implementation slice should include:

- `TINSurface` data contract
- vertex and triangle rows
- quality and provenance placeholders
- XY point-in-triangle hit detection
- barycentric Z interpolation
- boundary and no-hit diagnostics
- focused contract tests

The first implementation slice should not include:

- full Delaunay triangulation
- breakline enforcement
- clipping and merge algorithms
- LandXML import/export
- full FreeCAD task-panel UX
- volume calculation

## 5. Target Code Placement

Recommended code placement:

- `freecad/Corridor_Road/v1/models/result/tin_surface.py`
- `freecad/Corridor_Road/v1/services/evaluation/tin_sampling_service.py`
- `tests/contracts/v1/test_tin_sampling_service.py`

Optional follow-up placement:

- `freecad/Corridor_Road/v1/services/builders/tin_build_service.py`
- `freecad/Corridor_Road/v1/services/mapping/surface_output_mapper.py`
- `freecad/Corridor_Road/v1/ui/viewers/tin_review_view.py`

## 6. Proposed Data Contracts

### 6.1 TINVertex

Recommended fields:

- `vertex_id`
- `x`
- `y`
- `z`
- `source_point_ref`
- `notes`

### 6.2 TINTriangle

Recommended fields:

- `triangle_id`
- `v1`
- `v2`
- `v3`
- `triangle_kind`
- `quality_ref`
- `notes`

### 6.3 TINSurface

Recommended fields:

- `schema_version`
- `project_id`
- `surface_id`
- `surface_kind`
- `label`
- `vertex_rows`
- `triangle_rows`
- `boundary_refs`
- `void_refs`
- `quality_rows`
- `provenance_rows`
- `unit_context`
- `coordinate_context`
- `source_refs`
- `diagnostic_rows`

### 6.4 TinSampleResult

Recommended fields:

- `surface_ref`
- `query_kind`
- `x`
- `y`
- `z`
- `found`
- `status`
- `face_id`
- `confidence`
- `notes`

## 7. Implementation Phases

### 7.1 Phase A: TIN data contract

Status: Complete

Goal:

- introduce a minimal reusable `TINSurface` result contract

Tasks:

- add `models/result/tin_surface.py`
- export `TINSurface` from `models/result/__init__.py`
- keep the contract independent from FreeCAD UI classes

Acceptance criteria:

- a `TINSurface` can be instantiated with vertices and triangles
- the model preserves identity, kind, provenance, and diagnostics fields
- no viewer or exchange code is required to use it

### 7.2 Phase B: XY sampling core

Status: Complete

Goal:

- make `TinSamplingService.sample_xy()` return real hit/no-hit results

Tasks:

- let `sample_xy()` accept a `TINSurface` object directly
- retain compatibility with named `surface_ref` where practical
- implement point-in-triangle checks
- implement barycentric interpolation
- reject degenerate triangles with diagnostics
- return no-hit explicitly instead of treating it as `z=0`

Acceptance criteria:

- sampling inside one triangle returns interpolated Z
- sampling inside a two-triangle square returns interpolated Z
- sampling outside all triangles returns `found=False` and `status=no_hit`
- degenerate triangles do not crash sampling

### 7.3 Phase C: Contract tests

Status: Complete

Goal:

- lock the core behavior before UX work starts

Tasks:

- add `tests/contracts/v1/test_tin_sampling_service.py`
- test one-triangle sampling
- test two-triangle square sampling
- test boundary point behavior
- test no-hit behavior
- test degenerate triangle behavior

Acceptance criteria:

- tests run without FreeCAD GUI
- tests validate the shared v1 sampling contract
- failures identify geometry or diagnostic behavior clearly

### 7.4 Phase D: Station/offset adapter

Status: Complete for evaluated station-row adapter; full alignment geometry evaluation remains outside TIN sampling

Goal:

- prepare `sample_station_offset()` without inventing duplicate alignment logic

Tasks:

- keep station/offset sampling as a thin adapter
- accept an optional station-to-XY callback or evaluated alignment result
- delegate final elevation lookup to `sample_xy()`
- keep missing alignment context explicit

Acceptance criteria:

- station/offset queries do not silently reinterpret station as X and offset as Y unless marked as fallback
- alignment-context failure is reported as `status=error` or `status=fallback`
- evaluated station rows can provide the station-to-XY adapter without duplicating alignment geometry evaluation

### 7.5 Phase E: Thin review UX

Status: Complete for first slice

Goal:

- add a small review surface only after core sampling passes

Tasks:

- show surface identity
- show vertex and triangle counts
- show quality diagnostics
- allow one XY probe where practical
- display hit/no-hit, face id, confidence, and Z

Acceptance criteria:

- UX consumes TIN contracts and sampling service
- UX does not own sampling logic
- UX remains a review tool, not the terrain source of truth
- PointCloud TIN opens the v1 review bridge when available

### 7.6 Phase F: CSV point-cloud TIN build

Status: Complete for regular point-lattice CSV input

Goal:

- turn real CSV point input into the shared `TINSurface` contract

Tasks:

- add `TINBuildService`
- read CSV columns `easting`, `northing`, and `elevation`
- build one `TINVertex` per unique XY point
- split each complete lattice cell into two `TINTriangle` rows
- add quality rows for counts, extents, elevation range, and spacing
- allow TIN review command payloads to be built from a CSV path

Acceptance criteria:

- `tests/samples/pointcloud_utm_realistic_hilly.csv` builds into 14,641 vertices
- the same sample builds into 28,800 triangles
- resulting `TINSurface` can be sampled through `TinSamplingService`
- incomplete lattices fail explicitly rather than producing partial geometry

### 7.7 Phase G: PointCloud TIN CSV entry point

Status: Complete for first file-picker flow

Goal:

- let users open a CSV point cloud through the existing `PointCloud TIN` command

Tasks:

- add a CSV file picker to `CorridorRoad_ImportPointCloudTIN`
- default the picker to `tests/samples` when available
- pass selected `csv_path` into `show_v1_tin_review()`
- derive a stable `surface_id` from the CSV file name
- keep cancellation safe by falling back to the existing review path

Acceptance criteria:

- selecting `pointcloud_utm_realistic_hilly.csv` opens the CSV-backed TIN review flow
- cancellation does not crash the command
- command bridge tests can inject a CSV path without GUI

## 8. Test Command Guidance

Preferred FreeCAD command-line location:

- `D:\Program Files\FreeCAD 1.0\bin\FreeCADCmd.exe`

Recommended focused validation command once tests exist:

```powershell
& "D:\Program Files\FreeCAD 1.0\bin\FreeCADCmd.exe" -c "exec(open(r'tests\contracts\v1\test_tin_sampling_service.py', 'r', encoding='utf-8').read())"
& "D:\Program Files\FreeCAD 1.0\bin\FreeCADCmd.exe" -c "exec(open(r'tests\contracts\v1\test_tin_build_service.py', 'r', encoding='utf-8').read())"
& "D:\Program Files\FreeCAD 1.0\bin\FreeCADCmd.exe" -c "exec(open(r'tests\contracts\v1\test_tin_review_command.py', 'r', encoding='utf-8').read())"
& "D:\Program Files\FreeCAD 1.0\bin\FreeCADCmd.exe" -c "exec(open(r'tests\contracts\v1\test_pointcloud_tin_main_command.py', 'r', encoding='utf-8').read())"
```

If the test is pure Python and the local Python runtime is available, a direct Python run is acceptable, but FreeCADCmd should be preferred for addon-compatible validation.

## 9. Risks

Main risks:

- overbuilding triangulation before the sampling contract is proven
- letting `sample_station_offset()` duplicate alignment evaluation logic
- treating no-hit as elevation zero
- hiding degenerate triangle failures
- building a polished import panel before the data contract is reliable

## 10. Stop Conditions

Pause and realign if:

- sampling behavior requires UI state to work
- multiple consumers start implementing their own triangle hit logic
- tests need a real FreeCAD document before the core contract exists
- the first slice expands into clipping, merge, import, and UX at the same time

## 11. Next Implementation Order

Recommended immediate coding order:

1. [x] Add `TINSurface`, `TINVertex`, and `TINTriangle`
2. [x] Export the TIN result model
3. [x] Update `TinSamplingService.sample_xy()` to accept and sample a `TINSurface`
4. [x] Add focused contract tests
5. [x] Run tests with `FreeCADCmd.exe`
6. [x] Add station/offset adapter behavior
7. [x] Add thin review UX only after the core passes
8. [x] Add CSV point-cloud TIN build service for the realistic sample
9. [x] Add PointCloud TIN CSV file-picker entry point

## 12. Definition of Done for First Slice

The first TIN core slice is done when:

- TIN data can be represented without viewer or import code
- XY sampling returns real interpolated Z values
- no-hit and degenerate cases are explicit
- contract tests cover the basic sampling behavior
- CSV point-cloud samples can be converted into `TINSurface`
- a thin review command can show surface identity, counts, quality rows, and one XY probe
- downstream section, drainage, and earthwork code has one shared sampling service to call

This creates the technical floor for profile extraction, applied-section terrain interaction, drainage low-point review, and earthwork comparison.
