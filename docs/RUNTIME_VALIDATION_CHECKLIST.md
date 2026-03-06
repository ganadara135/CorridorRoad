# Runtime Validation Checklist (FreeCAD)

This checklist validates coordinate-system integrated workflows without relying on static-only checks.

## 0) Preconditions
- Open a project that has:
  - `CorridorRoadProject`
  - one alignment
  - one existing terrain mesh
- In `Project Setup`, confirm:
  - `CRSEPSG` is set (or intentionally blank for local-only test)
  - `ProjectOriginE/N/Z`, `LocalOriginX/Y/Z`, `NorthRotationDeg` are valid
  - `CoordSetupStatus` is `Initialized` (for world-mode scenarios)

## 1) Alignment Editor (Local/World input)
- Open `Edit Alignment`.
- Check coordinate hint text shows:
  - CRS/status
  - rotation
  - world/local origins
- Switch `Coord Input`:
  - `Local (X/Y)` -> table headers are `X/Y`
  - `World (E/N)` -> table headers are `E/N`
- Edit one IP row in world mode, click `Apply Alignment`.
- Expected:
  - no exception
  - alignment shape updates normally
  - criteria report still updates

## 2) Edit Profiles (EG sampling in Local/World)
- Open `Edit Profiles`.
- Select valid terrain mesh.
- Toggle `EG Terrain Coords` Local/World and run `Apply`.
- Expected:
  - EG values are sampled (not all zero unless true no-hit)
  - mode switch does not break table update
  - only `Close` standard button is present

## 3) Generate Sections (Daylight + terrain coord mode)
- Open `Generate Sections`.
- Ensure `Daylight Auto` is enabled.
- Select daylight terrain source and test:
  - `Daylight Terrain Coords = Local`
  - `Daylight Terrain Coords = World`
- Run `Generate Sections Now`.
- Expected:
  - sections are created per station
  - daylight side reaches terrain where intersection exists
  - station label format uses `STA ...` (no `Section @` prefix)

## 4) Design Terrain (existing terrain Local/World)
- Open `Design Terrain`.
- Select `DesignGradingSurface` and `ExistingTerrain`.
- Test both `Existing Terrain Coords` modes and run.
- Expected:
  - progress/cancel works
  - `Status` ends with `Completed` (or explicit `CANCELED`/`ERROR`)
  - result mesh is generated and linked to project

## 5) Cut-Fill Calc (existing mesh + manual domain coords)
- Open `Cut-Fill Calc`.
- Select `CorridorLoft` and existing mesh.
- Test:
  - `Existing Mesh Coords`: Local/World
  - Manual domain with `Manual Domain Coords`: Local/World
- Run calculation.
- Expected:
  - progress/cancel works
  - `Status` is explicit
  - volumes/delta fields update

## 6) Performance sanity (large mesh)
- Use a larger terrain mesh and run `Design Terrain`/`Cut-Fill`.
- Expected:
  - no UI freeze from coordinate conversion phase
  - progress advances through mesh read -> transform -> bucket -> sampling
  - guardrails block risky runs with clear messages

## 7) Regression quick pass (after any coordinate-related patch)
- Re-run steps 1, 4, 5 at minimum.
- Confirm no world/local mode default regression:
  - initialized setup defaults to world mode in relevant panels
  - uninitialized setup defaults to local mode
