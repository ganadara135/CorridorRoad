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
