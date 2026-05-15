# Workflow

Parametric Road v1 uses a source -> evaluation -> result -> output -> presentation structure.

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
- 3D Centerline station/offset/elevation resolution
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
- watertight solid outputs and simulation package manifests
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

`TIN -> Alignment -> Stations -> Profile -> Review Plan/Profile -> 3D Centerline -> Assembly -> Regions -> Structures -> Drainage -> Applied Sections -> Build Corridor -> Review -> Outputs -> AI Assist -> Watertight Solids`

Regions define station spans and the base Assembly. Structures and Drainage then choose their owning Region from their own source panels.

3D Centerline is the shared downstream baseline for station/offset/elevation context. Structures, Drainage, Applied Sections, Build Corridor, and Watertight Solids should prefer it when available.

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

## Drainage And Structure Flow

Use Structures before Drainage when the Drainage model needs Structure-backed pipe nodes.

1. Apply Regions.
2. Apply Structures with connection points.
3. Preview Structures if needed.
4. Apply Drainage Elements, Policies, and Flow Routes.
5. Use Drainage `Show Flow Network` or Drainage Review.
6. Rebuild Applied Sections and Build Corridor when downstream section or surface context must reflect the source changes.

`ditch -> inlet` Flow Routes are capture relationships. They do not create pipe bodies unless a Structure-backed pipe element is explicitly modeled.

## Watertight Solid Flow

Watertight Solids is the final stage after Build Corridor and AI Assist.

1. Build Corridor.
2. Open Watertight Solids.
3. Refresh targets.
4. Validate selected targets.
5. Build selected or enabled targets.
6. Build or export a package when simulation or exchange handoff is needed.
