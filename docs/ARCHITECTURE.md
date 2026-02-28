# CorridorRoad Architecture

## 1) Pipeline View
Terrain (EG) -> Horizontal Alignment -> Stations -> EG Profile -> FG Profile (from PVI) -> Delta -> 3D Centerline -> Assembly -> Sections -> Corridor/Loft -> Surface Comparison -> Cut/Fill

## 2) Object Responsibilities
### 2.1 VerticalAlignment (`objects/obj_vertical_alignment.py`)
- Purpose: vertical geometry engine only.
- Owns PVI data and solver logic.
- May display PVI polyline only (`ShowPVIWire`).
- Must not own FG display toggles.

### 2.2 FGDisplay (`objects/obj_fg_display.py`)
- Purpose: FG rendering only.
- Required label: `Finished Grade (FG)`.
- Required properties:
  - `SourceVA`
  - `ShowWire`
  - `CurvesOnly`
  - `ZOffset`
- Generates FG geometry from VerticalAlignment engine.

### 2.3 ProfileBundle (`objects/obj_profile_bundle.py`)
- Purpose: station-profile data container + EG display.
- Stores:
  - `Stations`, `ElevEG`, `ElevFG`, `ElevDelta`
  - Optional `VerticalAlignment` link
- Displays EG only (`ShowEGWire`, `WireZOffset`).

### 2.4 HorizontalAlignment (`objects/obj_alignment.py`)
- Purpose: horizontal geometry and stationing source shape.
- Supports:
  - Tangent + circular curve
  - Optional transition curve (S-C-S) approximation
- Practical properties:
  - Geometry: `IPPoints`, `CurveRadii`, `TransitionLengths`, `UseTransitionCurves`, `SpiralSegments`
  - Criteria: `DesignSpeedKph`, `SuperelevationPct`, `SideFriction`, `MinRadius`, `MinTangentLength`, `MinTransitionLength`
  - Results: `CriteriaMessages`, `CriteriaStatus`, `TotalLength`

### 2.5 Centerline3D (`objects/obj_centerline3d.py`)
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

### 2.6 Centerline3DDisplay (`objects/obj_centerline3d_display.py`)
- Purpose: 3D centerline rendering only.
- Input:
  - direct source links: `Alignment`, `Stationing`, `VerticalAlignment`, `ProfileBundle`
  - optional legacy link: `SourceCenterline` (Centerline3D)
- Controls:
  - `ShowWire`, `UseStationing`, `SamplingInterval`, `ElevationSource`
  - `MaxChordError`, `MinStep`, `MaxStep`, `UseKeyStations`
- Results:
  - `SampledStations`, `SampledPoints`, `SampleCount`, `Status`

### 2.7 AssemblyTemplate (`objects/obj_assembly_template.py`)
- Purpose: cross-section template parameters.
- Key params:
  - `LeftWidth`, `RightWidth`
  - `LeftSlopePct`, `RightSlopePct`

### 2.8 SectionSet (`objects/obj_section_set.py`)
- Purpose: section generation settings + aggregate section wire display.
- Inputs:
  - `SourceCenterlineDisplay`
  - `AssemblyTemplate`
- Modes:
  - `Range` (`StartStation`, `EndStation`, `Interval`)
  - `Manual` (`StationText`)
- Results:
  - `StationValues`, `SectionCount`, `Status`
- Optional tree children:
  - `SectionSlice` objects under `Group`
- Rebuild controls:
  - `AutoRebuildChildren`
  - `RebuildNow` (property-panel trigger)

## 3) UI Contracts
### 3.1 Sample Alignment (`commands/cmd_create_alignment.py`)
- Creates simple baseline alignment object and sample values.
- Keep as lightweight starter command.

### 3.2 Practical Alignment Editor (`commands/cmd_edit_alignment.py`, `ui/task_alignment_editor.py`)
- Edits practical alignment inputs:
  - IP coordinates
  - Radius/transition arrays
  - Criteria settings
- Shows criteria report messages.

### 3.3 Profile/PVI Editors
- `ui/task_profile_editor.py` controls FG visibility through FGDisplay only.
- `ui/task_pvi_editor.py` ensures FGDisplay exists and links to current VA.

### 3.4 Centerline Command (`commands/cmd_generate_centerline3d.py`)
- Creates/updates `Centerline3DDisplay` (direct source mode).
- Auto-links available Alignment/Stationing/VerticalAlignment/ProfileBundle.
- Uses `Auto` elevation mode by default (VA -> ProfileBundle FG -> FlatZero).
- Removes legacy `Centerline3D` engine object if present.

### 3.5 Section Command (`commands/cmd_generate_sections.py`, `ui/task_section_generator.py`)
- Provides user-facing section workflow:
  - select mode: `Range` or `Manual`
  - create/update `SectionSet`
  - optionally create child sections per station in tree

## 4) Design Rules
- Separation of concerns is mandatory:
  - Vertical engine != FG display
  - Profile data storage != FG display
  - Centerline3D engine != Centerline3DDisplay rendering
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
- `SectionSchemaVersion = 1`
- Section point order is fixed: `Left -> Center -> Right`
- Point count/order must be identical at all stations
- If mismatch is detected, Loft must stop with explicit status/error

### 6.2 Output Type Policy
- Phase-1 target is `Top Surface` only (open section Loft)
- `OutputType` enum should exist as `Surface|Solid`
- Current implementation scope: `Surface` only
- `Solid` generation is deferred to phase-2

### 6.3 Parametric Update Policy
- Default: `AutoUpdate = True`
- Rebuild triggers:
  - Alignment changes
  - Vertical/Profile source changes
  - AssemblyTemplate changes
  - SectionSet changes
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
  - try segmented Loft by station ranges
  - record failed range/stations in `Status`

## 7) Validation Strategy
- Primary validation is runtime behavior in FreeCAD:
  - object creation
  - recompute
  - property update reactions
  - command/task-panel flow
- `git grep` / `python -m compileall` are not mandatory validation gates in this project workflow.
