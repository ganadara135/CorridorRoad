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

## 4) Design Rules
- Separation of concerns is mandatory:
  - Vertical engine != FG display
  - Profile data storage != FG display
  - Centerline3D engine != Centerline3DDisplay rendering
- Keep sample and practical workflows separated, not mixed.
- Prefer small, patch-like changes and minimal churn.

## 5) Validation Strategy
- Primary validation is runtime behavior in FreeCAD:
  - object creation
  - recompute
  - property update reactions
  - command/task-panel flow
- `git grep` / `python -m compileall` are not mandatory validation gates in this project workflow.
