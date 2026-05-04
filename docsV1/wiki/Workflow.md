# Workflow

CorridorRoad v1 uses a source -> evaluation -> result -> output -> presentation structure.

## Layering

Source:

- Alignment
- Profile
- Assembly
- Region
- Structure
- Drainage

Evaluation:

- station resolution
- section application
- terrain sampling
- structure and drainage context resolution

Result:

- Applied Sections
- CorridorModel
- SurfaceModel
- Earthwork result models

Output:

- review payloads
- structure output packages
- quantity and exchange packages

Presentation:

- task panels
- review viewers
- preview objects
- diagnostics and markers

## Rule

Generated geometry is not the source of design intent.

If a result looks wrong, correct the source model or policy that created it, then rebuild the result.

## Primary Flow

`TIN -> Alignment -> Stations -> Profile -> Assembly -> Structures -> Region -> Drainage -> Applied Sections -> Build Corridor -> Review -> Outputs`

Drainage is already visible in the workflow but remains a planned editor stage in `1.0.0`.

## Region And Transition Review Flow

Region source rows are defined from Stationing-based `Start STA` values.

Applied Sections resolve the active Region at each station.

Build Corridor then uses Applied Sections plus Region source ranges to build surfaces, display Region Boundary rows, and apply stored Surface Transition records.

Use this order when changing Region or Surface Transition settings:

1. Update Region source rows.
2. Apply Region changes.
3. Generate Applied Sections.
4. Open Build Corridor.
5. Review Region Boundaries.
6. Update Surface Transition spacing where needed.
7. Build Corridor again to regenerate transition-aware surfaces.
