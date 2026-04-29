# CorridorRoad V1 Coordinate Import Policy

Date: 2026-04-29
Status: Active implementation rule

## Purpose

Define how external CSV coordinates enter v1 source models and result models.

## Scope

This policy applies to:

- point-cloud CSV terrain used to build Existing Ground TIN
- alignment PI CSV import/export
- downstream Profile, Corridor, section, and earthwork consumers that depend on terrain and alignment being in the same frame

## Core Rule

V1 internal engineering geometry is stored in Local X/Y/Z.

External CSV input can be World E/N/Z or Local X/Y/Z.

When Project Setup is `World-first`, CSV input is treated as World E/N/Z and converted to Local X/Y/Z before storage.

When Project Setup is `Local-first`, CSV input is treated as Local X/Y/Z and stored without coordinate transform.

CSV export should be explicit.

The default export mode is `Project default`, which follows Project Setup:

- `World-first` exports Local model coordinates as World E/N/Z
- `Local-first` exports Local model coordinates as Local X/Y/Z

Editors may also offer explicit `World E/N` and `Local X/Y` export choices.

## Design Goals

- keep TIN, Alignment, Profile, and Corridor calculations in one internal coordinate frame
- avoid large-coordinate instability inside FreeCAD geometry operations
- preserve enough coordinate metadata to understand how each imported result was produced
- make World-first survey workflows practical without forcing every downstream service to know about CRS transforms

## Object Families

- `TINSurface` stores local vertex rows after import.
- `AlignmentModel` and v1 alignment source objects store local PI rows after CSV import.
- TIN preview/result objects record coordinate import metadata.

## Root Fields

Coordinate import metadata should include:

- `SourceCoords`: `World` or `Local`
- `ModelCoords`: `Local`
- `CoordinateWorkflow`: Project Setup workflow at import time
- `CRSEPSG`
- `ProjectOriginE/N/Z`
- `LocalOriginX/Y/Z`
- `NorthRotationDeg`

CSV export metadata should record the coordinate frame of the exported file:

- `# CorridorRoadCoords,input=World,model=Local,workflow=World-first,epsg=EPSG:5186`

The `input` value describes how the exported CSV should be interpreted when imported again.

## Relationships

CSV terrain and CSV alignment must use the same import policy for one project.

Profile EG sampling assumes:

- Alignment station-to-XY evaluation returns Local X/Y
- TIN sampling receives Local X/Y
- TIN vertices are stored in Local X/Y/Z

## Diagnostics

Import UI should report the resolved coordinate path:

- `CSV coordinates: World E/N/Z -> Local X/Y/Z`
- `CSV coordinates: Local X/Y/Z`

TIN result objects should expose coordinate metadata through FreeCAD properties.

Alignment CSV export should show the resolved coordinate mode in the status message:

- `Export coordinates: World E/N/Z`
- `Export coordinates: Local X/Y/Z`

## Non-goals

- This policy does not implement geodetic reprojection between EPSG codes.
- This policy does not force output exchange always Local; CSV export can follow Project Setup or an explicit user-selected coordinate mode.
- This policy does not change legacy v0 coordinate behavior except where v1 commands call shared v1 services.
