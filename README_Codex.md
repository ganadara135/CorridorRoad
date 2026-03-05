# CorridorRoad Workbench - Codex Context

This repository is a FreeCAD Workbench (Python) for road corridor design.

## Project Goal (Pipeline)
Terrain (EG) -> Horizontal Alignment -> Stations -> Profiles (Data/EG) -> FG Profile (from PVI) -> Delta Profile -> 3D Centerline -> Assembly -> Sections -> Corridor/Loft (Solid) + DesignGradingSurface (Mesh) -> DesignTerrain (Mesh) -> Cut-Fill Calc -> Cut/Fill Volume

## Current Implementation Scope
### Implemented
- Sample Horizontal Alignment command (`Sample Alignment`)
- Practical alignment editing:
  - Tangent + circular curves + transition curves (S-C-S)
  - Criteria checks (radius / tangent / transition length)
  - Actionable guidance messages
- Station generation from alignment
- EG terrain sampling and profile data editing (`Edit Profiles (Data/EG)`)
- VerticalAlignment (PVI) engine and FG sampling
- FG display as dedicated object (`Finished Grade (FG)`)
- ProfileBundle storage (Stations/ElevEG/ElevFG/ElevDelta) and EG display
- 3D centerline generation from H+V integration (`Centerline3D`)
- Assembly template + section generation (`AssemblyTemplate`, `SectionSet`)
- Corridor loft generation (`CorridorLoft`, solid mode)
- Design grading surface generation (`DesignGradingSurface`, mesh mode)
- Design terrain generation (`DesignTerrain`, mesh mode)
- Existing/Design surface comparison phase-1 (`CutFillCalc`, mesh-based)
- Large-scene performance guardrails + estimate UX for `DesignTerrain`/`CutFillCalc`
- Shared utility modularization:
  - doc lookup/link helpers (`objects/doc_query.py`, `objects/project_links.py`)
  - profile/FG UI helpers (`ui/common/profile_fg_helpers.py`)
  - quality/estimate UI helpers (`ui/common/perf_quality.py`)
  - shared surface sampling core (`objects/surface_sampling_core.py`)

### Not Yet Implemented
- Assembly/subassembly detailed modeling
- Advanced surface comparison options (multi-source/advanced clipping)

## Core Architecture Rules (MUST)
### 1) VerticalAlignment (PVI)
- Role: data/engine only
- Owns:
  - `PVIStations`, `PVIElevations`, `CurveLengths`
  - `ClampOverlaps`, `MinTangent`
  - `elevation_at_station(station)`
  - Vertical curve solving (BVC/EVC + clamp)
- Displays:
  - PVI polyline only (`ShowPVIWire`)
- Must NOT own/display FG wire properties.

### 2) Finished Grade (FG) - FGDisplay object
- Role: display only
- Tree label: `Finished Grade (FG)`
- Properties:
  - `SourceVA` (Link to VerticalAlignment)
  - `ShowWire` (bool)
  - `CurvesOnly` (bool)
  - `ZOffset` (float)
- Builds FG shape from `SourceVA` using tangent lines and Bezier vertical-curve segments.

### 3) ProfileBundle
- Role: station-based profile storage + EG display
- Stores:
  - `Stations[]`, `ElevEG[]`, `ElevFG[]`, `ElevDelta[]`
  - Optional link: `VerticalAlignment`
- Displays:
  - EG wire only (`ShowEGWire`, `WireZOffset`)
- Must NOT display FG.

### 4) HorizontalAlignment
- Role: horizontal geometry engine and display shape for stationing
- Supports:
  - Sample mode (`Sample Alignment`)
  - Practical mode (`Edit Alignment`)
    - `CurveRadii[]`, `TransitionLengths[]`, `UseTransitionCurves`, `SpiralSegments`
    - Criteria: `DesignSpeedKph`, `SuperelevationPct`, `SideFriction`, `MinRadius`, `MinTangentLength`, `MinTransitionLength`
    - Output: `CriteriaMessages`, `CriteriaStatus`

### 5) Centerline3D
- Role: data/engine only for H+V integrated 3D centerline.
- Inputs:
  - `Alignment` (required)
  - `Stationing` (optional; for station list)
  - `VerticalAlignment` (optional)
  - `ProfileBundle` (optional FG fallback)
- Controls:
  - `UseStationing`
  - `SamplingInterval`
  - `ElevationSource` (`Auto`, `VerticalAlignment`, `ProfileBundleFG`, `FlatZero`)
- Outputs:
  - `StationValues`, `CenterlinePoints`, `TotalLength3D`

### 6) Centerline3DDisplay
- Role: display only for 3D centerline.
- Input:
  - direct source links (`Alignment`, `Stationing`, `VerticalAlignment`, `ProfileBundle`)
  - optional legacy link: `SourceCenterline`
- Controls:
  - `ShowWire`
  - `UseStationing`, `SamplingInterval`, `ElevationSource`
  - `MaxChordError`, `MinStep`, `MaxStep`
  - `UseKeyStations`
- Behavior:
  - Builds display wire using adaptive sampling (curve-heavy regions are sampled denser).

### 7) AssemblyTemplate
- Role: section template parameter object.
- Key inputs:
  - `LeftWidth`, `RightWidth`
  - `LeftSlopePct`, `RightSlopePct`
  - `HeightLeft`, `HeightRight`
  - side slope options:
    - `UseSideSlopes`
    - `LeftSideWidth`, `RightSideWidth`
    - `LeftSideSlopePct`, `RightSideSlopePct`
    - `UseDaylightToTerrain`, `DaylightSearchStep`, `DaylightMaxTriangles`
- Display:
  - crown line + depth envelope wire
  - `HeightLeft/HeightRight` changes are visible in 3D view immediately
  - `HeightLeft/HeightRight` are in the `Assembly` property group

### 8) SectionSet
- Role: section generation container + aggregate display.
- Station mode:
  - `Range`: Start/End/Interval
  - `Manual`: station list text
- Sources:
  - `SourceCenterlineDisplay`
  - `AssemblyTemplate`
  - optional `TerrainMesh` (for daylight-to-terrain, Mesh/Shape)
  - terrain source resolve order when daylight is enabled:
    - `SectionSet.TerrainMesh`
    - `CorridorRoadProject.Terrain`
    - document terrain candidate fallback
- Optional:
  - child `SectionSlice` objects in tree
  - rebuild controls: `AutoRebuildChildren`, `RebuildNow`
- Schema policy:
  - `SectionSchemaVersion=1`: 3-point section (`Left->Center->Right`)
  - `SectionSchemaVersion=2`: side-slope extended section (>=3 points)
- Daylight status/warnings:
  - no terrain source found -> fixed side width fallback
  - terrain source found but sampler failed -> fixed side width fallback
- Daylight performance controls:
  - `AssemblyTemplate.DaylightMaxTriangles`
  - wide-triangle bucket guard
- Sampling policy:
  - daylight terrain sampling should use shared core (`objects/surface_sampling_core.py`) via module wrappers.

### 9) CorridorLoft
- Role: corridor loft generator from `SectionSet`.
- Controls:
  - `OutputType` (`Solid`)
  - `HeightLeft`, `HeightRight` (fallback heights)
  - `UseRuled`
  - `AutoUpdate`, `RebuildNow`
- Results:
  - `SectionCount`, `PointCountPerSection`, `SchemaVersion`
  - `NeedsRecompute`
  - `FailedRanges`, `Status`
- Output mode:
  - `Solid`: loft from closed profiles using downward heights
  - height source priority: `AssemblyTemplate.HeightLeft/HeightRight` -> `CorridorLoft.HeightLeft/HeightRight`
- Pending-update marker:
  - tree label suffix: ` [Recompute]`
  - status prefix: `NEEDS_RECOMPUTE`

### 10) DesignGradingSurface
- Role: render visual grading surface (road + side slopes/daylight) from `SectionSet`.
- Controls:
  - `AutoUpdate`, `RebuildNow`
- Results:
  - `SectionCount`, `PointCountPerSection`, `FaceCount`, `SchemaVersion`
  - `NeedsRecompute`, `Status`
- Output mode:
  - ruled-surface base is tessellated to output mesh facets
  - intended for 3D side-slope visualization and mesh-based downstream analysis

### 11) CutFillCalc
- Role: compare `ExistingSurface` (mesh) vs design top surface from `CorridorLoft`.
- Controls:
  - `CellSize`, `MaxSamples`, `MinMeshFacets`, `DomainMargin`, `UseCorridorBounds`
  - `MaxTrianglesPerSource`, `MaxCandidateTriangles`, `MaxTriangleChecks`
  - `NoDataWarnRatio`
  - manual domain (`XMin/XMax/YMin/YMax`)
  - `AutoUpdate`, `RebuildNow`
- Results:
  - `SampleCount`, `ValidCount`
  - `DeltaMin/DeltaMax/DeltaMean`
  - `CutVolume`, `FillVolume`, `NoDataArea`
  - `DomainArea`, `NoDataRatio`
  - `SignConvention`
  - `Status`
- 3D display controls:
  - `ShowDeltaMap`, `DeltaDeadband`, `DeltaClamp`, `VisualZOffset`, `MaxVisualCells`
- 3D color policy:
  - Cut=red, Fill=blue, Neutral=light gray, NoData=gray
- Runtime behavior:
  - progress callback updates stage/percent during run
  - cancel request sets `Status = CANCELED: user requested cancel`
  - when `AutoUpdate=False`, edits do not auto-run comparison and remain pending until `RebuildNow=True`
- Performance guards:
  - run precheck: estimated samples must be within `MaxSamples`
  - source triangle decimation by `MaxTrianglesPerSource`
  - per-sample candidate cap by `MaxCandidateTriangles`
  - run precheck: estimated triangle checks must be within `MaxTriangleChecks`
  - scale-aware defaults from `LengthScale` for `CellSize`/`DomainMargin`/delta display thresholds
  - minimum cell guard: `CellSize >= 0.2 m * LengthScale`
  - scale-aware design tessellation deflection
  - wide-triangle bucket expansion guard to avoid pathological bucket growth
- Shared-core policy:
  - triangle extraction/bucket/intersection primitives should be sourced from `objects/surface_sampling_core.py`.

### 12) DesignTerrain
- Role: build composite terrain mesh from `DesignGradingSurface` and existing terrain.
- Inputs:
  - `SourceDesignSurface` (`DesignGradingSurface`)
  - `ExistingTerrain` (Mesh)
- Controls:
  - `CellSize`, `MaxSamples`, `DomainMargin`
  - `MaxTrianglesPerSource`, `MaxCandidateTriangles`, `MaxTriangleChecks`
  - `AutoUpdate`, `RebuildNow`
- Guardrails:
  - scale-aware defaults from `Project.LengthScale`
  - minimum cell guard: `CellSize >= 0.2 m * LengthScale`
  - source triangle decimation by `MaxTrianglesPerSource`
  - per-sample candidate cap by `MaxCandidateTriangles`
  - run precheck: estimated triangle checks must be within `MaxTriangleChecks`
- Shared-core policy:
  - triangle extraction/bucket/intersection primitives should be sourced from `objects/surface_sampling_core.py`.
- Results:
  - `SampleCount`, `ValidCount`, `NoDataArea`
  - `NeedsRecompute`, `Status`
- Merge rule:
  - where design surface exists, use design Z
  - otherwise use existing terrain Z

### 13) CorridorRoadProject
- Role: project container + global scale policy.
- Key property:
  - `LengthScale` (internal units per meter; `1.0=m`, `1000.0=mm-like`)
- Scale behavior:
  - sample/default length values are initialized with `LengthScale`
  - station/section/assembly/centerline default distances follow `LengthScale`
  - geometric computation remains in internal units
  - changing `LengthScale` does not auto-rescale existing object values

## Section Basis Rules (Fixed)
- Section baseline must use resolved H+V source data (not display tessellation).
- Source priority:
  - XY from `HorizontalAlignment.point_at_station`
  - Z from `VerticalAlignment` -> `ProfileBundleFG` -> `FlatZero`
- Section frame is fixed to `T-N-Z`:
  - `T = normalize(P(s+eps)-P(s-eps))`
  - `Z = (0,0,1)`
  - `N = normalize(Z x T)` (left)
  - continuity guard: use previous `N` when degenerate and flip by dot sign

## Corridor Loft Preconditions (Fixed)
- Section shape contract:
  - `SectionSchemaVersion = 1 or 2`
  - `v1` point order fixed: `Left -> Center -> Right`
  - `v2` point order: `LeftOuter? -> Left -> Center -> Right -> RightOuter?`
  - point count/order must match across stations; mismatch stops Loft
- Output policy:
  - `OutputType = Solid`
  - `Solid`: closed-profile loft with valid `HeightLeft/HeightRight`
- Parametric update policy:
  - default `AutoUpdate = True`
  - rebuild triggers: Alignment, Vertical/Profile source, AssemblyTemplate, SectionSet
  - source edits mark `CorridorLoft` as pending recompute (no auto corridor recompute)
  - manual trigger: `RebuildNow=True`
- Failure guards:
  - prechecks: >=2 sections, same point count/order, valid stations, no NaN/critical duplicates
  - continuity fix for orientation flips
  - adaptive segmented fallback (range split) with failed ranges logged in `Status`

## UI / TaskPanel Rules
### Edit Profiles (Data/EG)
- Table edits ProfileBundle station/profile data.
- FG display controls must map to `FGDisplay` object properties.
- EG terrain source is explicitly selectable from Mesh/Shape list.
- `Apply` commits sampling+data updates; standard buttons are `Close` only (no `OK/Cancel`).

### Generate Sections Panel
- standard buttons are `Close` only (no `OK/Cancel`).
- section creation/update runs only from `Generate Sections Now`.
- supports side slopes and Stage-2 terrain-daylight options.
- daylight terrain source can be Mesh or Shape (`Project.Terrain` or `SectionSet.TerrainMesh`).
- `Daylight Auto (SectionSet)` is enabled by default on panel open.

### Scale UX
- `New Project` opens scale input (`LengthScale`) when project is created.
- `Sample Alignment` opens scale input before sample generation.
- If project is missing, `Sample Alignment` creates project container and stores `LengthScale`.

### Generate Design Grading Surface
- command creates/updates `DesignGradingSurface` from current `SectionSet`.
- intended for 3D visualization of side slopes/daylight.

### Generate Design Terrain
- command opens dedicated TaskPanel (`ui/task_design_terrain.py`).
- standard dialog button is `Close` only (no `OK/Cancel`; run-cancel is separate).
- TaskPanel requires explicit source selection:
  - `DesignGradingSurface`
  - `ExistingTerrain` (Mesh)
- TaskPanel applies options (`CellSize`, `MaxSamples`, `DomainMargin`, `AutoUpdate`) and runs merge.
- TaskPanel provides quality presets (`Fast/Balanced/Precise/Custom`) and estimate hint.
- TaskPanel exposes large-scene guards (`MaxTrianglesPerSource`, `MaxCandidateTriangles`, `MaxTriangleChecks`).
- TaskPanel blocks risky runs when estimated samples/checks exceed guard limits.
- preset/estimate helper logic should be shared from `ui/common/perf_quality.py`.
- TaskPanel shows progress and supports cancel during long runs.
- updates project links (`Terrain`, `DesignGradingSurface`, `DesignTerrain`).

### Command Labels
- toolbar/menu labels do not include `Generate`.
- command IDs follow current feature naming (e.g., `CorridorRoad_GenerateCutFillCalc`).

### Cut-Fill Calc Panel
- command opens dedicated TaskPanel (no immediate heavy run on command click)
- standard dialog button is `Close` only (no `OK/Cancel`; run-cancel is separate)
- user explicitly selects `CorridorLoft` and Existing mesh source
- panel shows run status/progress and supports cancel
- panel provides 3D map controls (deadband/clamp/z-offset/max visual cells)
- panel provides quality presets (`Fast/Balanced/Precise/Custom`) and estimate hint
- panel exposes large-scene guards (`MaxTrianglesPerSource`, `MaxCandidateTriangles`, `MaxTriangleChecks`)
- panel blocks risky runs when estimated samples/checks exceed guard limits
- preset/estimate helper logic should be shared from `ui/common/perf_quality.py`
- run path updates `CutFillCalc` + project links (`CorridorLoft`, `Terrain`, `CutFillCalc`)

### PVI Editor
- Updates/creates `VerticalAlignment`.
- Ensures `FGDisplay` exists and links `SourceVA`.
- PVI station/elevation/curve-length values are loaded/saved with `LengthScale` conversion.
- standard buttons are `Close` only (no `OK/Cancel`).

### Alignment Editor
- Edits IP coordinates, radius, and transition length.
- Updates criteria input values and shows criteria report messages.

## Naming / Consistency
- Keep module names stable:
  - `objects/obj_vertical_alignment.py`
  - `objects/obj_fg_display.py`
  - `objects/obj_profile_bundle.py`
  - `objects/obj_alignment.py`
  - `ui/task_profile_editor.py`
  - `ui/task_pvi_editor.py`
  - `ui/task_alignment_editor.py`
  - `objects/doc_query.py`
  - `objects/project_links.py`
  - `objects/surface_sampling_core.py`
  - `ui/common/profile_fg_helpers.py`
  - `ui/common/perf_quality.py`
- Keep sample command and practical command separated:
  - `CorridorRoad_CreateAlignment` = Sample Alignment
  - `CorridorRoad_EditAlignment` = Practical editing
- Shared-helper usage policy:
  - document object lookup should prefer `objects/doc_query.py`.
  - project link/adopt updates should prefer `objects/project_links.py`.
  - PVI/Profile FG helper logic should prefer `ui/common/profile_fg_helpers.py`.
  - DesignTerrain/CutFill preset+estimate logic should prefer `ui/common/perf_quality.py`.
  - surface triangle/bucket/intersection primitives should prefer `objects/surface_sampling_core.py`.

## Model Representation Policy (Fixed)
- `CorridorLoft` uses `Solid` model.
- `DesignGradingSurface` uses `Mesh` model.
- `DesignTerrain` uses `Mesh` model.
- Other design/analysis objects use `Surface/Wire` representation.

## Existing/Design Surface Entry Decisions (Fixed 7)
Before implementing `Existing/Design Surface` comparison:

1. Corridor recompute UX
- source edits must mark corridor as pending recompute (`[Recompute]`, `NEEDS_RECOMPUTE`)
- corridor recompute is explicit/manual

2. Design surface source
- use `CorridorLoft` top surface only

3. Existing surface input
- phase-1 input type is `Mesh` only

4. Domain and resolution
- default domain: corridor extents + margin
- default resolution: `1.0 m` (adjustable `0.2~5.0 m`)

5. Result schema
- store `DeltaMin/Max/Mean`, `CutVolume`, `FillVolume`, `NoDataArea`, `CellSize`, `Status`

6. Validation sample
- keep one fixed sample case
- tolerance: elevation `±0.01 m`, volume `±1%`

7. Execution UX / responsiveness
- Surface comparison run must provide visible progress state.
- User must be able to cancel from TaskPanel during long runs.
- Long-run path should avoid unnecessary document-wide recompute dependency.

## Pre-Cut/Fill Decisions (Fixed 8)
Before finalizing cut/fill volume reporting, these are fixed:

1. Sign convention
- `delta = Design - Existing`
- `delta > 0` is Fill, `delta < 0` is Cut

2. Design surface scope
- Use corridor top surface only (no side-face inclusion).

3. Comparison domain policy
- Default: corridor bounds + margin (`UseCorridorBounds=True`).
- Manual bounds are explicit override.

4. Sampling policy
- Default `CellSize = 1.0 m`, with operational recommendation `2.0~5.0 m` for large scenes.
- Hard guard: estimated samples must not exceed `MaxSamples`.

5. Existing mesh quality gate
- Existing mesh must pass minimum facet count (`MinMeshFacets`) and non-degenerate XY bounds.

6. NoData governance
- Track `NoDataArea` and `NoDataRatio`.
- Warn when `NoDataRatio > NoDataWarnRatio`.

7. Result reporting minimum set
- `CutVolume`, `FillVolume`, `DeltaMin/DeltaMax/DeltaMean`
- `SampleCount`, `ValidCount`, `NoDataArea`, `NoDataRatio`
- `CellSize`, `Status`, `SignConvention`

8. Regression baseline
- Keep one fixed sample case for regression.
- Target tolerance: elevation +/-0.01 m, volume +/-1%.

9. 3D visualization rule
- Delta map uses fixed color policy: Cut=red, Fill=blue, Neutral=light gray, NoData=gray.
- Use `DeltaDeadband` for neutral band and `DeltaClamp` for color saturation.
- Large scenes must throttle display density via `MaxVisualCells`.

## Validation Policy
- Prefer FreeCAD runtime validation (object creation, property changes, recompute behavior).
- Do not require `git grep` or `python -m compileall` as mandatory workflow steps in this repository.

