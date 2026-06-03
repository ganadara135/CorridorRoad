# Workflow

Parametric Road v1 uses a source -> evaluation -> result -> output -> presentation structure.

## Layering

Source:

- Alignment
- Profile
- Superelevation
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

`TIN -> Alignment -> Stations -> Profile -> Review Plan/Profile -> 3D Centerline -> Superelevation -> Assembly -> Regions -> Intersections -> Structures -> Drainage -> Applied Sections -> Build Corridor -> Review -> Outputs -> AI Assist -> Watertight Solids`

Regions define station spans and the base Assembly. Intersections then group intersection Regions and participating Alignments into junction control areas. Structures and Drainage then choose their owning Region from their own source panels.

3D Centerline is the shared downstream baseline for station/offset/elevation context. Structures, Drainage, Applied Sections, Build Corridor, and Watertight Solids should prefer it when available.

For Intersections, 3D Centerline can be multi-alignment. Starter Sources create the participating Alignment/Profile/Stationing/Region sources and then generate a multi-alignment 3D Centerline preview so the primary road and side road do not share one baseline.

Superelevation is the station-based crossfall source after 3D Centerline. It does not replace Assembly; it overrides lane and shoulder crossfall during Applied Sections generation.

Use this order when changing Superelevation:

1. Edit or load Superelevation control rows.
2. Validate and Apply Superelevation.
3. Use `Show Samples` to review station values and 3D crossfall bars.
4. Generate Applied Sections.
5. Build Corridor again so Design Surface output reflects the resolved crossfall.

## Region And Transition Review Flow

Region source rows are defined from Stationing-based `Start STA` values.

Applied Sections resolve the active Region at each station.

Build Corridor then uses Applied Sections plus Region source ranges to build surfaces, display Region Boundary rows, and apply stored Surface Transition records.

Build Parametric generated previews and diagnostics are exposed in the FreeCAD tree under:

`04_Parametric Model / Build Parametric Outputs`

This includes generated surface previews, Region surface previews, transition span markers, and Build Parametric review markers. Users can hide/show these objects and inspect their properties from the tree after Build Corridor runs.

Use this order when changing Region or Surface Transition settings:

1. Update Region source rows.
2. Apply Region changes.
3. Generate Applied Sections.
4. Open Build Corridor.
5. Review Region Boundaries.
6. Update Surface Transition spacing where needed.
7. Build Corridor again to regenerate transition-aware surfaces.

## Intersection Flow

Intersections are source-stage control data.

Use `Create Starter Sources` when a quick test junction is needed. It creates editable Alignment, Profile, Stationing, and Region sources, then generates the 3D Centerline preview for the participating Alignments.

Use this order for the starter workflow:

1. Open Intersections.
2. Select the intersection type.
3. Set Source Mode to `Create Starter Sources`.
4. Create starter sources.
5. Confirm the status message includes the generated 3D Centerline.
6. Review or refresh 3D Centerline.
7. Apply Intersections.
8. Build Sections.
9. Build Parametric.
10. Review Region Boundaries and Slope Face Issues.

Build Parametric reads Region source rows from all participating Alignments. The Region Boundaries table includes an Alignment column for this reason.

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

Built solid output objects are exposed in the FreeCAD tree under:

`09_Outputs & Exchange / Watertight Solids`

The Watertight Solids panel also routes existing `V1WatertightSolidOutput` objects into this folder when the panel opens or refreshes, so users can hide/show built solids and inspect object properties directly from the tree.
