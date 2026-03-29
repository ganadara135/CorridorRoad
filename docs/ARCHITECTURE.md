<!-- SPDX-License-Identifier: LGPL-2.1-or-later -->
<!-- SPDX-FileNotice: Part of the Corridor Road addon. -->

# CorridorRoad Architecture

For current mixed-workflow support and warning expectations, also see `docs/MIXED_WORKFLOW_VALIDATION_MATRIX.md`.

## 1) Pipeline View
Terrain (EG) -> Horizontal Alignment -> Stations -> Profiles (Data/EG) -> FG Profile (from PVI) -> Delta -> 3D Centerline -> Assembly -> Sections -> Corridor/Loft (Solid) + DesignGradingSurface (Mesh) -> DesignTerrain (Mesh) -> Cut-Fill Calc -> Cut/Fill

## 2) Object Responsibilities
### 2.1 VerticalAlignment (`freecad/Corridor_Road/objects/obj_vertical_alignment.py`)
- Purpose: vertical geometry engine only.
- Owns PVI data and solver logic.
- May display PVI polyline only (`ShowPVIWire`).
- Default display policy:
  - `ShowPVIWire=True`
  - `Edit PVI` save/apply keeps the PVI object visible in 3D view by default.
- Must not own FG display toggles.

### 2.2 FGDisplay (`freecad/Corridor_Road/objects/obj_fg_display.py`)
- Purpose: FG rendering only.
- Required label: `Finished Grade (FG)`.
- Required properties:
  - `SourceVA`
  - `ShowWire`
  - `CurvesOnly`
  - `ZOffset`
- Generates FG geometry from VerticalAlignment engine.

### 2.3 ProfileBundle (`freecad/Corridor_Road/objects/obj_profile_bundle.py`)
- Purpose: station-profile data container + EG display.
- Stores:
  - `Stations`, `ElevEG`, `ElevFG`, `ElevDelta`
  - Optional `VerticalAlignment` link
- Displays EG only (`ShowEGWire`, `WireZOffset`).

### 2.4 HorizontalAlignment (`freecad/Corridor_Road/objects/obj_alignment.py`)
- Purpose: horizontal geometry and stationing source shape.
- Supports:
  - Tangent + circular curve
  - Optional transition curve (S-C-S) approximation
  - Stable station helpers on mixed edge types:
    - `point_at_station(s)` (length-based edge parameter)
    - `tangent_at_station(s)`, `normal_at_station(s)`
    - `station_at_xy(x, y)` (approximate inverse mapping)
- Practical properties:
  - Geometry: `IPPoints`, `CurveRadii`, `TransitionLengths`, `UseTransitionCurves`, `SpiralSegments`
  - Criteria: `DesignSpeedKph`, `SuperelevationPct`, `SideFriction`, `MinRadius`, `MinTangentLength`, `MinTransitionLength`
  - Results: `CriteriaMessages`, `CriteriaStatus`, `CriteriaStandard`, `TotalLength`
  - Key-station outputs:
    - `IPKeyStations` (PI station list)
    - `TSKeyStations`, `SCKeyStations`, `CSKeyStations`, `STKeyStations` (transition/key station lists)

### 2.5 Centerline3D (`freecad/Corridor_Road/objects/obj_centerline3d.py`)
- Purpose: 3D centerline computation engine (no display shape ownership).
- Inputs:
  - `Alignment` (required)
  - `Stationing` (optional station list source)
  - `VerticalAlignment` (optional elevation source)
  - `ProfileBundle` (optional FG fallback source)
- Controls:
  - `UseStationing`, `SamplingInterval`, `ElevationSource`
- Results:
  - `StationValues`, `CenterlinePoints`, `TotalLength3D`, `ResolvedElevationSource`, `Status`
- Section helpers:
  - `point3d_at_station(s)`
  - `tangent3d_at_station(s, eps)`
  - `frame_at_station(s, eps, prev_n)` returning `T-N-Z`

### 2.6 Centerline3DDisplay (`freecad/Corridor_Road/objects/obj_centerline3d_display.py`)
- Purpose: 3D centerline rendering only.
- Input:
  - direct source links: `Alignment`, `Stationing`, `VerticalAlignment`, `ProfileBundle`
  - optional legacy link: `SourceCenterline` (Centerline3D)
- Controls:
  - `ShowWire`, `UseStationing`, `SamplingInterval`, `ElevationSource`
  - `MaxChordError`, `MinStep`, `MaxStep`, `UseKeyStations`
- Results:
  - `SampledStations`, `SampledPoints`, `SampleCount`, `Status`

### 2.7 AssemblyTemplate (`freecad/Corridor_Road/objects/obj_assembly_template.py`)
- Purpose: cross-section template parameters.
- Key params:
  - `LeftWidth`, `RightWidth`
  - `LeftSlopePct`, `RightSlopePct`
  - `HeightLeft`, `HeightRight` (used by corridor solid output)
  - side slope options:
    - `UseSideSlopes`
    - `LeftSideWidth`, `RightSideWidth`
    - `LeftSideSlopePct`, `RightSideSlopePct`
    - `UseDaylightToTerrain`, `DaylightSearchStep`, `DaylightMaxSearchWidth`, `DaylightMaxWidthDelta`, `DaylightMaxTriangles`
- Display behavior:
  - template wire shows crown line and depth envelope
  - `HeightLeft/HeightRight` edits are visible in 3D view immediately
  - `HeightLeft/HeightRight` belong to `Assembly` property group
- Sync behavior:
  - `Edit Alignment -> Apply Alignment` syncs alignment `SuperelevationPct`
    into `LeftSlopePct/RightSlopePct` when an assembly template is linked/found.

### 2.7A StructureSet (`freecad/Corridor_Road/objects/obj_structure_set.py`)
- Purpose: structure data source + 3D/reference display geometry.
- Owns:
  - structure record arrays
  - optional station-profile arrays (`ProfileStructureIds`, `ProfileStations`, `ProfileOffsets`, `ProfileWidths`, `ProfileHeights`, ...)
  - geometry fields (`GeometryMode`, `TemplateName`, `ShapeSourcePath`, `ScaleFactor`, `PlacementMode`, `UseSourceBaseAsBottom`)
  - result diagnostics (`ResolvedShapeSourceKinds`, `ResolvedShapeStatusNotes`, `ResolvedFrameSources`, `ResolvedFrameStatusNotes`, `Status`)
- Geometry modes:
  - `box`
  - `template`
  - `external_shape`
- Template support:
  - `box_culvert`
  - `utility_crossing`
  - `retaining_wall`
  - `abutment_block`
- External-shape support:
  - `.step` / `.stp`
  - `.brep` / `.brp`
  - `.FCStd#ObjectName`
- Placement rule:
  - prefer `Centerline3D.frame_at_station(...)`
  - alignment frame is fallback only
  - centerline regeneration should trigger `StructureSet` recompute
- Station-profile rule:
  - `resolve_profile_at_station(...)` and `resolve_profile_span(...)` are the shared API for variable-size structure consumption
  - current runtime consumers:
    - 3D structure display
    - `Structure Sections` overlays
    - section overrides / earthwork
    - corridor `notch` handling
  - profile-driven 3D display currently prefers section-wire loft between resolved profile stations and only falls back to segment solids when lofting fails
- Earthwork rule:
  - `external_shape` currently affects display/reference placement only
  - section overrides, grading surface generation, and corridor structure handling must continue to use structure `Type` plus simple dimensional metadata
  - do not assume imported STEP/BREP/FCStd solids are directly consumed by earthwork

### 2.8 SectionSet (`freecad/Corridor_Road/objects/obj_section_set.py`)
- Purpose: section generation settings + aggregate section wire display.
- Inputs:
  - `SourceCenterlineDisplay`
  - `AssemblyTemplate`
  - `TypicalSectionTemplate` (optional, component-based top profile)
  - optional `TerrainMesh` (for daylight-to-terrain, Mesh only)
  - `TerrainMeshCoords` (`Local` or `World`) for daylight terrain interpretation
  - terrain source resolve order when daylight is enabled:
    - `SectionSet.TerrainMesh`
    - `CorridorRoadProject.Terrain`
    - document terrain candidate fallback
- Modes:
  - `Range` (`StartStation`, `EndStation`, `Interval`)
  - `Manual` (`StationText`)
  - Range helper:
    - `IncludeAlignmentIPStations` adds alignment IP key stations to range list
    - `IncludeAlignmentSCCSStations` adds transition TS/SC/CS/ST key stations to range list
    - `UseStructureSet`, `StructureSet`
    - `IncludeStructureStartEnd`, `IncludeStructureCenters`
    - `IncludeTransitionStations`, `AutoTransitionDistance`, `TransitionDistance`
    - `CreateStructureTaggedChildren`, `ApplyStructureOverrides`
- Results:
  - `StationValues`, `SectionSchemaVersion`, `TopProfileSource`, `SectionCount`, `Status`
  - schema policy:
    - `SectionSchemaVersion=1`: 3-point section (`Left->Center->Right`)
    - `SectionSchemaVersion=2`: extended/open profile (side slopes and/or Typical Section break points)
- daylight runtime status:
  - `WARN: UseDaylightToTerrain=True but no terrain source found...`
  - `WARN: Terrain source found but daylight sampler failed...`
- daylight coordinate rule:
  - when `TerrainMeshCoords=World`, daylight terrain triangles are transformed to local before section sampling
- daylight performance guards:
  - `AssemblyTemplate.DaylightMaxTriangles`
  - `AssemblyTemplate.DaylightMaxWidthDelta`
  - wide-triangle bucket guard to avoid bucket blow-up
- daylight continuity policy:
  - neighboring section daylight widths should be smoothed/clamped by `DaylightMaxWidthDelta` to reduce abrupt loft twists.
- structure-earthwork rule:
  - structure overrides are type-driven and simplified
  - `external_shape` does not yet define the true section-cutting profile
  - when station-profile control points exist, section overlays and section overrides should consume resolved profile values at the active station
- Optional tree children:
  - `SectionSlice` objects under `Group`
  - `Structure Sections` overlay objects for structure-only section visualization
  - label format: `STA {station}` with optional key tags (e.g., `[PI]`, `[TS]`, `[SC]`, `[CS]`, `[ST]`, `[STR]`)
- Rebuild controls:
  - `AutoRebuildChildren`
  - `RebuildNow` (property-panel trigger)

### 2.9 CorridorLoft (`freecad/Corridor_Road/objects/obj_corridor_loft.py`)
- Purpose: corridor loft generation from `SectionSet`.
- Inputs:
  - `SourceSectionSet`
- Controls:
  - `OutputType` (`Solid` only)
  - `HeightLeft`, `HeightRight` (fallback when template values are unavailable)
  - `UseRuled`
  - `AutoFixSectionOrientation`
  - `SplitAtStructureZones`
  - `UseStructureCorridorModes`
  - `DefaultStructureCorridorMode`
  - `NotchTransitionScale`
  - `AutoUpdate`
  - `RebuildNow`
- Results:
  - `SectionCount`, `PointCountPerSection`, `SchemaVersion`
  - `AutoFixedSectionCount`
  - `StructureSegmentCount`, `StructureSplitStations`
  - `SkippedStationRanges`, `SkipMarkerCount`
  - `ResolvedStructureNotchCount`, `ResolvedNotchStationCount`
  - `ClosedProfileSchemaVersion`
  - `NeedsRecompute`
  - `FailedRanges`, `Status`
- Output mode:
  - `Solid`: loft from closed profiles generated with downward heights
  - Height source priority: `AssemblyTemplate.HeightLeft/HeightRight` -> `CorridorLoft.HeightLeft/HeightRight`
- Structure-aware corridor behavior:
  - `split_only` keeps corridor continuity while splitting loft at structure boundaries
  - `skip_zone` omits corridor body across structure-active spans
  - `notch` is primarily for `culvert` / `crossing` and should prefer a notch-aware closed-profile schema
- Current notch policy:
  - transition stations can drive ramped notch entry/exit
  - result reporting should expose notch-aware station count and closed-profile schema version
  - boolean cut remains optional and is not required for the first notch-capable workflow
  - when station-profile control points exist, notch width/height-related values should consume resolved profile values along the active span
- External-shape relation:
  - corridor structure handling is derived from `ResolvedCorridorMode`, structure type, and simplified dimensions
  - `external_shape` is not yet used as a direct boolean cutter or loft-profile source for earthwork
- Pending-update marker:
  - tree label suffix: ` [Recompute]`
  - status text starts with `NEEDS_RECOMPUTE` when source changed
- orientation continuity policy:
  - when `AutoFixSectionOrientation=True`, section point order may be reversed automatically if neighboring section comparison indicates a likely left/right flip.

### 2.10 DesignGradingSurface (`freecad/Corridor_Road/objects/obj_design_grading_surface.py`)
- Purpose: visual grading surface (road top + side slopes/daylight) from `SectionSet`.
- Inputs:
  - `SourceSectionSet`
- Earthwork/source rule:
  - consumes section wires rebuilt from `SectionSet`
  - does not directly consume the real `external_shape` solid
  - therefore follows the same structure `Type`-based simplification policy used by section overrides
- Controls:
  - `AutoUpdate`, `RebuildNow`
- Results:
  - `SectionCount`, `PointCountPerSection`, `FaceCount`, `SchemaVersion`
  - `NeedsRecompute`, `Status`
- Output mode:
  - ruled-surface base is tessellated to output mesh facets
  - intended for 3D visualization of cut/fill side slopes and mesh-based analysis
- Pending-update marker:
  - tree label suffix: ` [Recompute]`
  - status text starts with `NEEDS_RECOMPUTE` when source changed

### 2.11 CutFillCalc (`freecad/Corridor_Road/objects/obj_cut_fill_calc.py`)
- Purpose: Existing/Design surface comparison and cut/fill summary.
- Inputs:
  - `SourceCorridor` (`CorridorLoft`)
  - `ExistingSurface` (Mesh object)
- Controls:
  - `CellSize`, `MaxSamples`, `MinMeshFacets`, `DomainMargin`, `UseCorridorBounds`
  - `NoDataWarnRatio`
  - `DomainCoords` (`Local` or `World`) for manual `X/Y` domain input
  - `ExistingSurfaceCoords` (`Local` or `World`)
  - manual domain: `XMin/XMax/YMin/YMax`
  - `AutoUpdate`, `RebuildNow`
- Results:
  - `SampleCount`, `ValidCount`
  - `DeltaMin/DeltaMax/DeltaMean`
  - `CutVolume`, `FillVolume`, `NoDataArea`
  - `DomainArea`, `NoDataRatio`
  - `SignConvention`
  - `Status`
- 3D delta map controls:
  - `ShowDeltaMap`
  - `DeltaDeadband`
  - `DeltaClamp`
  - `VisualZOffset`
  - `MaxVisualCells`
- 3D color policy:
  - Cut=red, Fill=blue, Neutral=light gray, NoData=gray
- Comparison rule:
  - design side uses top surface extracted from `CorridorLoft`
  - existing side uses mesh triangles
  - grid sampling integrates `delta = Design - Existing`
- Coordinate rule:
  - design side is local-model coordinates
  - manual domain is interpreted by `DomainCoords` (world input is converted to local bbox)
  - when `ExistingSurfaceCoords=World`, existing mesh triangles are transformed to local before sampling
- Runtime/UX:
  - supports progress callback (stage + percent)
  - supports cancel request during run
  - cancel result is stored as `Status = CANCELED: user requested cancel`
  - when `AutoUpdate=False`, source/parameter edits set pending status and do not auto-run
- Performance guards:
  - precheck `EstimatedSamples <= MaxSamples`
  - scale-aware defaults (`CellSize`, `DomainMargin`, display delta thresholds) from `Project.LengthScale`
  - minimum cell guard: `CellSize >= 0.2 m * LengthScale`
  - design tessellation deflection is scale-aware
  - wide-triangle bucket expansion is guarded to avoid bucket blow-up
  - status/progress updates are emitted in mesh-read, bucketing, and sampling phases

### 2.12 DesignTerrain (`freecad/Corridor_Road/objects/obj_design_terrain.py`)
- Purpose: composite terrain mesh from `DesignGradingSurface` and existing terrain.
- Inputs:
  - `SourceDesignSurface` (`DesignGradingSurface`)
  - `ExistingTerrain` (Mesh source)
- Controls:
  - `CellSize`, `MaxSamples`, `DomainMargin`
  - `ExistingTerrainCoords` (`Local` or `World`)
  - `AutoUpdate`, `RebuildNow`
- Guardrails:
  - scale-aware defaults from `Project.LengthScale`
  - minimum cell guard: `CellSize >= 0.2 m * LengthScale`
- Results:
  - `SampleCount`, `ValidCount`, `NoDataArea`, `NeedsRecompute`, `Status`
- Merge rule:
  - use design surface elevation where available
  - else keep existing terrain elevation
- Coordinate rule:
  - design surface side is local-model coordinates
  - when `ExistingTerrainCoords=World`, existing terrain triangles are transformed to local before merge

### 2.13 CorridorRoadProject (`freecad/Corridor_Road/objects/obj_project.py`)
- Purpose: project container + global unit/scale policy.
- Key property:
  - `LengthScale` (internal units per meter; `1.0=m`, `1000.0=mm-like`)
  - `DesignStandard` (`KDS` or `AASHTO`)
- Coordinate setup properties:
  - `CRSEPSG`, `HorizontalDatum`, `VerticalDatum`
  - `ProjectOriginE/N/Z`, `LocalOriginX/Y/Z`, `NorthRotationDeg`
  - `CoordSetupLocked`, `CoordSetupStatus`
- Shared coordinate transform helpers:
  - `world_to_local(...)`, `local_to_world(...)`
  - vector variants: `world_to_local_vec(...)`, `local_to_world_vec(...)`
  - bulk/localized geometry helpers for world/local conversion: `freecad/Corridor_Road/objects/coord_transform.py`
  - world XY domain/bounds conversion helper: `world_xy_bounds_to_local(...)`
  - repeated point conversion caching helper: `world_point_to_local_cached(...)`
- Scale usage:
  - sample/default length values are initialized by `LengthScale`
  - station/section/assembly/centerline defaults follow project scale
  - geometry math stays in internal units; source survey data remains unchanged
  - changing `LengthScale` does not retroactively rescale existing object values

## 3) UI Contracts
- Shared coordinate-mode UX policy:
  - coordinate setup hint text and default Local/World mode decision should use `freecad/Corridor_Road/ui/common/coord_ui.py`
  - hint text includes CRS/status plus transform essentials (north rotation, world/local origins)

### 3.0 Project Setup (`freecad/Corridor_Road/commands/cmd_project_setup.py`, `freecad/Corridor_Road/ui/task_project_setup.py`)
- Provides initial coordinate-system setup UI:
  - design standard selection (`KDS` / `AASHTO`)
  - CRS/EPSG, datum, world/local origin, north rotation
  - setup lock/status
- `Apply Setup` commits values to `CorridorRoadProject`.
- `New Project` opens this task panel automatically after project creation.

### 3.1 Sample Alignment (`freecad/Corridor_Road/commands/cmd_create_alignment.py`)
- Creates simple baseline alignment object and sample values.
- Sample defaults include feasible S-C-S transition settings (`CurveRadii`, `TransitionLengths`, `UseTransitionCurves=True`).
- Keep as lightweight starter command.
- Uses current project `LengthScale` (no scale popup).
- Creates `CorridorRoadProject` automatically when missing and uses default `LengthScale`.
- Sample points are generated around project local origin (`LocalOriginX/Y`).

### 3.2 Practical Alignment Editor (`freecad/Corridor_Road/commands/cmd_edit_alignment.py`, `freecad/Corridor_Road/ui/task_alignment_editor.py`)
- Edits practical alignment inputs:
  - IP coordinates
  - Radius/transition arrays
  - Criteria settings
  - Design standard selector (`KDS` / `AASHTO`) synced with project
  - Sketch import (`Load from Sketch`) for horizontal plan source objects
  - CSV import/export (`Inspect CSV`, `Load from CSV`, `Save CSV`)
- Supports target alignment selection in TaskPanel.
- Coordinate input mode:
  - `Local (X/Y)` writes local model coordinates directly
  - `World (E/N)` converts to/from local using project coordinate setup
- Shows criteria report messages.
- Report shows applied criteria standard and pending editor standard (if changed before apply).
- `Apply Alignment` also propagates `SuperelevationPct` to
  `AssemblyTemplate.LeftSlopePct/RightSlopePct` when available.
- TaskPanel button policy:
  - standard button is `Close`
  - apply action is explicit `Apply Alignment`
- Input guards:
  - duplicate/too-close consecutive IP rows are rejected
  - endpoint radius/transition values are forced to zero with warning text
- Diagnostics:
  - report includes status, total length, and approximate IP station summary.
  - criteria checks include reverse-curve diagnostics (`[REVERSE]`, `[REVERSE-TANGENT]`, `[REVERSE-TRANSITION]`).
- Sketch import conversion policy:
  - source sketch must be a single connected open path in XY.
  - `line-arc-line` is converted to PI + exact arc radius (TS/ST tangent points are skipped as IP rows).
  - imported transition lengths default to zero (`Ls=0.0`).
- CSV import/export policy:
  - parser/writer helper is centralized in `freecad/Corridor_Road/objects/csv_alignment_import.py`.
  - import supports encoding/delimiter/header auto-detection and explicit override.
  - import supports column mapping (`x/y/r/ls/sta`) and optional station sort.
  - import can interpret CSV coordinates as local/world/panel-mode and converts to table mode.
  - export writes current PI table rows with mode-aware coordinate headers (`X/Y` or `E/N`).

### 3.3 Profile/PVI Editors
- `freecad/Corridor_Road/ui/task_profile_editor.py` controls FG visibility through FGDisplay only.
- Profile editor EG terrain sampling coordinate mode:
  - `Local (X/Y)` samples terrain with local alignment XY directly
  - `World (E/N)` converts local alignment XY to world XY for sampling, then converts sampled Z back to local
- `freecad/Corridor_Road/ui/task_pvi_editor.py` ensures FGDisplay exists and links to current VA.
- `Generate FG Now (apply)` shows a completion dialog on success.
- saved/generated `Vertical Alignment (PVI)` is visible in 3D view by default.

### 3.4 Centerline Command (`freecad/Corridor_Road/commands/cmd_generate_centerline3d.py`)
- Creates/updates `Centerline3DDisplay` (direct source mode).
- Auto-links available Alignment/Stationing/VerticalAlignment/ProfileBundle.
- Uses `Auto` elevation mode by default (VA -> ProfileBundle FG -> FlatZero).
- Removes legacy `Centerline3D` engine object if present.
- Touches linked `StructureSet` so structure solids recompute against the latest 3D centerline frame.

### 3.5 Section Command (`freecad/Corridor_Road/commands/cmd_generate_sections.py`, `freecad/Corridor_Road/ui/task_section_generator.py`)
- Provides user-facing section workflow:
  - select mode: `Range` or `Manual`
  - optional key-station injection in range mode (`Include Alignment IP Key Stations`, `Include Alignment TS/SC/CS/ST Key Stations`)
  - optional structure-station merge from linked `StructureSet`
  - transition-station insertion around structure boundaries
  - optional `Typical Section Template` source for finished-grade top profile
  - create/update `SectionSet`
  - optional side slopes + terrain-daylight (Stage-2, Mesh source only)
  - daylight terrain coordinate mode selection (`Local`/`World`)
  - daylight width smoothing control (`Daylight Max Width Delta`)
  - optionally create child sections per station in tree
  - `Close` closes dialog only (no generation)
  - generation action is `Generate Sections Now` button

### 3.5B Typical Section (`freecad/Corridor_Road/commands/cmd_edit_typical_section.py`, `freecad/Corridor_Road/ui/task_typical_section_editor.py`)
- Creates/updates `TypicalSectionTemplate`
- Supports component-table editing and direct CSV import
- Supports pavement-layer table editing and direct pavement CSV import
- Current CSV columns:
  - `Id`, `Type`, `Side`, `Width`, `CrossSlopePct`, `Height`, `Offset`, `Order`, `Enabled`
- Current pavement CSV columns:
  - `Id`, `Type`, `Thickness`, `Enabled`
- Current sample CSVs:
  - `typical_section_basic_rural.csv`
  - `typical_section_urban_complete_street.csv`
  - `typical_section_with_ditch.csv`
  - `typical_section_pavement_basic.csv`
- Current component notes:
  - `curb` = vertical step + top width
  - `ditch` = V-like sag break
  - `berm` = flat road-edge platform segment
  - `bench` = reserved term for future earthwork mid-slope benching
- Current pavement notes:
  - pavement layers are data-first, not separate corridor solids yet
  - `TypicalSectionTemplate` stores `PavementLayerCount`, `EnabledPavementLayerCount`, `PavementTotalThickness`
  - `SectionSet`, `CorridorLoft`, and `DesignGradingSurface` mirror the pavement summary for downstream reporting
  - pavement preview offset wires were removed; `TypicalSectionTemplate.Shape` now stays focused on the top-profile wire for faster panel/apply behavior
- execution-plan/status document:
  - `docs/TYPICAL_SECTION_EXECUTION_PLAN.md`

### 3.5A Edit Structures (`freecad/Corridor_Road/ui/task_structure_editor.py`)
- Station columns are driven by generated `Stationing` values.
- `BottomElevation` / `Cover` enablement follows structure type policy.
- `Browse Shape` supports `.step`, `.brep`, and `.FCStd`.
- `Apply` reports external-shape fallback diagnostics and frame-source diagnostics.
- Current editor structure:
  - upper structure-header table = compact overview
  - grouped column reveal = `Template`, `External Shape`, `Advanced`
  - `Selected Structure Details` = preferred advanced-field editor
  - lower profile table = station-profile control points for the selected structure
- Current quick actions:
  - `Add Common Structure`
  - `Clone Selected`
  - structure-set `Preset` loader
  - profile-level `Profile Preset` loader
- Current UX policy:
  - selection context updates on explicit row press/click, not hover
  - row validation state is surfaced directly in the upper table and summary labels

### 3.6 Corridor Command (`freecad/Corridor_Road/commands/cmd_generate_corridor_loft.py`)
- Creates/updates `CorridorLoft`.
- Links current `SectionSet`.
- Forces `OutputType` to `Solid`.

### 3.7 Design Grading Surface Command (`freecad/Corridor_Road/commands/cmd_generate_design_grading_surface.py`)
- Creates/updates `DesignGradingSurface`.
- Links current `SectionSet`.
- Uses section schema (v1/v2) and daylight-resolved section wires.
- successful run shows a completion dialog with section/facet summary.

### 3.8 Cut-Fill Calc Command (`freecad/Corridor_Road/commands/cmd_generate_cut_fill_calc.py`)
- Opens dedicated TaskPanel (`freecad/Corridor_Road/ui/task_cut_fill_calc.py`).
- TaskPanel responsibilities:
  - explicit source selection (`CorridorLoft`, Existing Mesh)
  - existing mesh coordinate mode selection (`Local`/`World`)
  - manual domain coordinate mode selection (`Local`/`World`)
  - set comparison controls (domain/resolution/update policy)
  - show run progress and support cancel
- Execution path:
  - updates/creates `CutFillCalc`
  - updates project links (`CorridorLoft`, `Terrain`, `CutFillCalc`)
  - runs comparison through object proxy execution path for responsive UI

### 3.9 Design Terrain Command (`freecad/Corridor_Road/commands/cmd_generate_design_terrain.py`)
- Opens dedicated TaskPanel (`freecad/Corridor_Road/ui/task_design_terrain.py`).
- TaskPanel responsibilities:
  - explicit source selection (`DesignGradingSurface`, `ExistingTerrain (Mesh)`)
  - existing terrain coordinate mode selection (`Local`/`World`)
  - set `CellSize` / `MaxSamples` / `DomainMargin` / `AutoUpdate`
  - show run progress and support cancel
- Execution path:
  - updates/creates `DesignTerrain`
  - updates project links (`Terrain`, `DesignGradingSurface`, `DesignTerrain`)
  - runs design-terrain merge through object proxy execution path

### 3.10 Command Label Policy
- Toolbar/menu labels omit `Generate` prefix.
- Command IDs follow current feature naming (`CorridorRoad_GenerateCutFillCalc` etc.).

## 4) Design Rules
- Separation of concerns is mandatory:
  - Vertical engine != FG display
  - Profile data storage != FG display
  - Centerline3D engine != Centerline3DDisplay rendering
- Model representation policy:
  - `CorridorLoft` is Solid model
  - `DesignGradingSurface` is Mesh model (visual grading)
  - `DesignTerrain` is Mesh model (composite terrain)
  - other design/analysis objects are Surface/Wire based
- Section baseline must come from resolved H+V source data, not display wire tessellation.
- Section frame must use fixed T-N-Z rule for consistency across recomputes.
- Keep sample and practical workflows separated, not mixed.
- Prefer small, patch-like changes and minimal churn.

## 5) Section Basis Rules
### 5.1 Baseline Source Priority
- XY: `HorizontalAlignment.point_at_station`
- Z source priority:
  - `VerticalAlignment.elevation_at_station` if available
  - else `ProfileBundle` FG interpolation
  - else `FlatZero`
- Display tessellation settings (`SamplingInterval`, `MaxChordError`) must not change section baseline.

### 5.2 Section Frame Rule (T-N-Z)
- `T(s) = normalize(P(s+eps) - P(s-eps))`
- `Z = (0,0,1)` fixed global up
- `N = normalize(Z x T)` (left normal)
- Near-degenerate `N` uses previous `N` (if available), else fallback `(0,1,0)`
- If `dot(N, prev_n) < 0`, flip `N` to maintain continuity
- Recommended default: `eps = 0.1 m`

## 6) Corridor Loft Preconditions (Fixed)
### 6.1 Section Shape Contract
- `SectionSchemaVersion = 1 or 2`
- `v1`: section point order fixed: `Left -> Center -> Right`
- `v2`: side-slope extended order: `LeftOuter? -> Left -> Center -> Right -> RightOuter?`
- Point count/order must be identical at all stations
- If mismatch is detected, Loft must stop with explicit status/error

### 6.2 Output Type Policy
- `OutputType` is `Solid` only
- `Solid` uses closed profiles built from section wires + `HeightLeft/HeightRight` (downward)
- `HeightLeft/HeightRight` must be finite and non-negative, and at least one side must be > 0

### 6.3 Parametric Update Policy
- Default: `AutoUpdate = True`
- Rebuild triggers:
  - Alignment changes
  - Vertical/Profile source changes
  - AssemblyTemplate changes
  - SectionSet changes
- Section/Assembly source edits must not auto-recompute `CorridorLoft`
- Instead, linked corridor objects are marked as pending recompute in tree/status
- Manual override trigger must exist: `RebuildNow=True`

### 6.4 Loft Failure Guards
- Prechecks:
  - at least 2 sections
  - equal point count/order
  - valid station values
  - no NaN/duplicate critical points
- Continuity guard:
  - detect orientation flips between neighboring sections
  - auto-fix orientation before Loft
- Failure fallback:
  - try adaptive segmented Loft by station ranges (range split on failure)
  - record failed range/stations in `Status`

## 7) Validation Strategy
- Primary validation is runtime behavior in FreeCAD:
  - object creation
  - recompute
  - property update reactions
  - command/task-panel flow
- Standard runtime scenario sheet: `docs/RUNTIME_VALIDATION_CHECKLIST.md`
- `git grep` / `python -m compileall` are not mandatory validation gates in this project workflow.

## 8) Pre-CutFillCalc Decisions (Fixed 7)
Before entering `Existing/Design Surface` comparison stage, these are fixed:

1. Corridor recompute UX
- Source edits do not auto-recompute `CorridorLoft`.
- Mark pending state in tree/status (`[Recompute]`, `NEEDS_RECOMPUTE`).
- Recompute is explicit (manual trigger/command).

2. Design Surface extraction
- Comparison design surface is extracted from `CorridorLoft` top surface only.

3. Existing Surface input format
- Phase-1 existing surface input is `Mesh` only.

4. Comparison domain/resolution
- Default domain: corridor extents with margin.
- Default cell/sample size: `1.0 m` (user-adjustable range: `0.2~5.0 m`).

5. Result schema
- `CutFillCalc` must store: `DeltaMin/Max/Mean`, `CutVolume`, `FillVolume`, `NoDataArea`, `CellSize`, `Status`.

6. Validation sample and tolerance
- Keep one fixed sample case for regression.
- Target tolerance: elevation `±0.01 m`, volume `±1%`.

7. Execution UX / responsiveness
- Surface comparison run must provide visible progress state.
- User must be able to cancel from TaskPanel during long runs.
- Long-run path should avoid unnecessary document-wide recompute dependency.

## 9) Pre-Cut/Fill Decisions (Fixed 8)
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
