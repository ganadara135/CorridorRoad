# Date: 2026-03-29

# Surface Comparison Source Matrix

## Fully Supported

- `CutFillCalc`: `Corridor top surface` vs `ExistingSurface mesh`
  - Result mode: `corridor_top_vs_existing_mesh`
  - Result support: `supported`
  - Coordinate handling:
    - design side is local model coordinates
    - existing mesh may be `Local` or `World`
  - Domain modes:
    - `corridor_bounds`
    - `manual_bounds_local`
    - `manual_bounds_world`
  - Output rows:
    - `ComparisonSourceSummaryRows`
    - `DomainSummaryRows`
    - `StationBinnedSummaryRows`

## Partially Supported

- None in the current roadmap scope.

## Deferred

- `DesignGradingSurface mesh` vs `ExistingSurface mesh`
- `DesignTerrain mesh` vs `ExistingSurface mesh`
- arbitrary `Surface A` vs `Surface B`
- corridor-clipped mesh/mesh comparison using a true solid clip volume
- polygon-selected analysis domain
- structure-masked comparison domain

## Notes

- The current implementation keeps the design side tied to corridor top-face extraction from the current `CorridorLoft` object.
- Domain and station-bin reporting are now explicit result contracts, but they do not yet change the underlying comparison source pair.
- Future source pairs should add a new explicit `ComparisonSourceMode` value rather than overloading `corridor_top_vs_existing_mesh`.
