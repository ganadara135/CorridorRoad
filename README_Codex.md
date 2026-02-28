# CorridorRoad Workbench - Codex Context

This repository is a FreeCAD Workbench (Python) for road corridor design.

## Project Goal (Pipeline)
Terrain (EG) -> Horizontal Alignment -> Stations -> EG Profile -> FG Profile (from PVI) -> Delta Profile -> 3D Centerline -> Assembly -> Sections -> Corridor/Loft -> Surface Comparison -> Cut/Fill Volume

## Current Implementation Scope
### Implemented
- Sample Horizontal Alignment command (`Sample Alignment`)
- Practical alignment editing:
  - Tangent + circular curves + transition curves (S-C-S)
  - Criteria checks (radius / tangent / transition length)
  - Actionable guidance messages
- Station generation from alignment
- Sample EG profile generation
- VerticalAlignment (PVI) engine and FG sampling
- FG display as dedicated object (`Finished Grade (FG)`)
- ProfileBundle storage (Stations/ElevEG/ElevFG/ElevDelta) and EG display
- 3D centerline generation from H+V integration (`Centerline3D`)

### Not Yet Implemented
- Assembly/subassembly modeling
- Section generation pipeline
- Corridor lofting workflow
- Surface comparison and cut/fill volume workflow

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
  - Practical mode (`Edit Alignment (Practical)`)
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

### 8) SectionSet
- Role: section generation container + aggregate display.
- Station mode:
  - `Range`: Start/End/Interval
  - `Manual`: station list text
- Sources:
  - `SourceCenterlineDisplay`
  - `AssemblyTemplate`
- Optional:
  - child `SectionSlice` objects in tree
  - rebuild controls: `AutoRebuildChildren`, `RebuildNow`

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
  - `SectionSchemaVersion = 1`
  - point order fixed: `Left -> Center -> Right`
  - point count/order must match across stations; mismatch stops Loft
- Output policy:
  - phase-1: `Top Surface` only (open section Loft)
  - keep `OutputType = Surface|Solid` for compatibility
  - current support: `Surface` only
- Parametric update policy:
  - default `AutoUpdate = True`
  - rebuild triggers: Alignment, Vertical/Profile source, AssemblyTemplate, SectionSet
  - manual trigger: `RebuildNow=True`
- Failure guards:
  - prechecks: >=2 sections, same point count/order, valid stations, no NaN/critical duplicates
  - continuity fix for orientation flips
  - fallback to segmented Loft with failed ranges logged in `Status`

## UI / TaskPanel Rules
### Edit Profiles (EG/FG)
- Table edits ProfileBundle station/profile data.
- FG display controls must map to `FGDisplay` object properties.

### PVI Editor
- Updates/creates `VerticalAlignment`.
- Ensures `FGDisplay` exists and links `SourceVA`.

### Practical Alignment Editor
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
- Keep sample command and practical command separated:
  - `CorridorRoad_CreateAlignment` = Sample Alignment
  - `CorridorRoad_EditAlignment` = Practical editing

## Validation Policy
- Prefer FreeCAD runtime validation (object creation, property changes, recompute behavior).
- Do not require `git grep` or `python -m compileall` as mandatory workflow steps in this repository.
