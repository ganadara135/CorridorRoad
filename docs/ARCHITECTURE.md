# CorridorRoad Workbench — Codex Context

This repository is a FreeCAD Workbench (Python) for road corridor design.

## Project Goal (Pipeline)
Terrain(EG) → Horizontal Alignment → Stations → EG Profile → FG Profile (from PVI) → Delta Profile → 3D Centerline → Assembly → Sections → Loft Corridor → Surface Comparison → Cut/Fill Volume (incl. slopes)

## Core Architecture Rules (MUST)
### 1) VerticalAlignment (PVI)
- Role: **data/engine only**
- Owns:
  - PVIStations, PVIElevations, CurveLengths
  - ClampOverlaps, MinTangent
  - elevation_at_station(station)
  - curve solving (BVC/EVC handling + clamp)
- Displays:
  - May display **PVI polyline only** (ShowPVIWire)
- Must NOT own / must NOT display:
  - ShowFGWire
  - FGCurvesOnly
  - FGWireZOffset
  - Any FG display wire

### 2) Finished Grade (FG) — FGDisplay object
- Role: **display-only**
- Tree label MUST be: **"Finished Grade (FG)"**
- Properties:
  - SourceVA (Link to VerticalAlignment)
  - ShowWire (bool)
  - CurvesOnly (bool): if true show only vertical curve segments
  - ZOffset (float)
- Generates FG shape from SourceVA using:
  - line edges for tangents (optional)
  - quadratic Bezier edges for vertical curves (exact 2nd-degree curve)
- CurvesOnly may create disconnected segments → return Compound safely.

### 3) ProfileBundle
- Role: station-based profile storage (data + EG display)
- Stores:
  - Stations[]
  - ElevEG[]
  - ElevFG[] (data storage, not display responsibility)
  - ElevDelta[] = FG - EG
  - Link: VerticalAlignment (optional traceability)
- Displays:
  - EG wire only (ShowEGWire, WireZOffset)
- Must NOT display FG, must NOT have ShowFGWire.

## UI / TaskPanels Rules (MUST)
### Edit Profiles (EG/FG)
- Table edits Stations/EG/FG data in ProfileBundle.
- FG display toggles MUST control **Finished Grade (FG)** object:
  - Show FG → FGDisplay.ShowWire
  - FG Z Offset → FGDisplay.ZOffset
  - Curves Only → FGDisplay.CurvesOnly (if shown in UI)
- Must NOT reference removed VA FG properties.

### PVI Editor
- Updates/creates VerticalAlignment.
- Ensures FGDisplay exists and is linked (SourceVA=VA).
- Should NOT store FG display settings on VA.

## Naming / Consistency
- Use "FG" (Finished Grade) instead of "design" in naming.
- Keep module names stable:
  - objects/obj_vertical_alignment.py
  - objects/obj_fg_display.py
  - objects/obj_profile_bundle.py
  - ui/task_profile_editor.py
  - ui/task_pvi_editor.py
  - commands/cmd_edit_profiles.py etc.

## Safety / Migration
- When removing properties from VerticalAlignment, search repo for references.
- Provide a simple migration helper if old documents still contain removed props.
- Prefer small patches, patch-like diffs, and minimal churn.

## Validation Checklist (before commit)
1) `git grep -n "ShowFGWire\|FGCurvesOnly\|FGWireZOffset" CorridorRoad` returns nothing (except documentation if any).
2) `python -m compileall CorridorRoad` passes.
3) In FreeCAD:
   - "Finished Grade (FG)" appears and CurvesOnly works in Property editor.
   - VerticalAlignment shows only PVI (if enabled).
   - Edit Profiles opens without AttributeError and toggles FGDisplay.
