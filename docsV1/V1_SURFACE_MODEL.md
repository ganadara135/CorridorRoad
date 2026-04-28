# CorridorRoad V1 Surface Model

Date: 2026-04-23
Branch: `v1-dev`
Status: Draft baseline
Depends on:

- `docsV1/V1_MASTER_PLAN.md`
- `docsV1/V1_ARCHITECTURE.md`
- `docsV1/V1_TIN_ENGINE_PLAN.md`
- `docsV1/V1_TIN_DATA_SCHEMA.md`
- `docsV1/V1_CORRIDOR_MODEL.md`
- `docsV1/V1_EARTHWORK_BALANCE_PLAN.md`

## 1. Purpose

This document defines the v1 internal model for normalized surface result families.

It exists to make clear:

- what `SurfaceModel` owns
- how surface families differ from raw TIN engine data
- how corridor-derived surfaces are organized
- how surfaces feed earthwork, outputs, and exchange

## 2. Scope

This model covers:

- surface identity and grouping
- design, subgrade, daylight, and comparison surfaces
- surface provenance and build relationships
- clipping, merge, and comparison context
- diagnostics and traceability

This model does not cover:

- low-level triangulation algorithm details
- raw survey point ingestion workflows
- final viewer styling behavior
- quantity report layout behavior

## 3. Core Rule

`SurfaceModel` is a derived engineering result system built on normalized TIN contracts.

This means:

- it is not a replacement for the TIN engine
- it organizes analysis-ready and corridor-ready surface families
- surfaces must remain traceable to source terrain and corridor results
- exported or displayed meshes must not replace normalized surface truth

## 4. Surface Philosophy in v1

In v1, surfaces are not just visual skins.

They are:

- normalized TIN-based engineering results
- corridor-derived and analysis-ready surface families
- major inputs to earthwork and exchange
- reviewable outputs with provenance

This keeps surface behavior aligned with the TIN-first architecture.

## 5. Relationship to TIN Engine

The architectural distinction is:

- the TIN engine provides triangulation, storage, sampling, clip, merge, and comparison services
- `SurfaceModel` organizes meaningful surface result families that corridor and analysis systems consume

The surface subsystem should reuse TIN contracts rather than inventing a parallel mesh system.

## 6. Relationship to Corridor

`CorridorModel` is a major upstream source for surface generation.

Typical corridor-derived surface families include:

- `DesignTIN`
- `SubgradeTIN`
- `DaylightTIN`
- corridor-derived comparison or clipped surfaces

Terminology note:

- The practical design object is the slope face.
- `DaylightTIN` is the v1 surface family name for slope-face terrain tie-in output.
- Early geometry may show a slope-face strip; later geometry should resolve the real slope-face daylight line against existing ground.

`SurfaceModel` is where those results become explicit, grouped, and traceable.

## 7. Surface Scope in v1

Recommended early v1 support:

- existing-ground surface references
- finished-grade design surfaces
- subgrade surfaces
- daylight surfaces
- clipped/export-range surfaces
- comparison and volume-support surfaces

Deferred or later refinements may include:

- richer multi-surface composition stacks
- staged-construction surface sets
- more advanced material-specific analysis surfaces

### 7.1 Surface vs Solid representation boundary

`SurfaceModel` represents open, terrain-like, TIN-based result surfaces.

Use surface representation for:

- existing ground TIN and normalized survey terrain
- finished grade design surface
- subgrade surface
- daylight and tie-in surfaces
- cut/fill comparison surfaces
- clipped review, export, and analysis surfaces
- temporary grading and intermediate construction surfaces
- drainage grading surfaces where the result is terrain-like, such as ditch flowline influence, swale grading, or channel side grading
- TIN preview and review meshes derived from normalized surface data

Ditch drainage surfaces should derive from the point roles and shape rules in `docsV1/V1_DITCH_SHAPE_CONTRACT.md`.

Do not use surface representation as the durable model for:

- closed pavement bodies with physical thickness
- curbs, gutters, barriers, guardrails, walls, pipes, culverts, inlets, manholes, bridge members, or other component bodies
- IFC-style physical elements that need material, volume, and component identity
- quantity solids where a closed volume is the main deliverable

### 7.2 Solid representation boundary

Solid representation belongs to physical component outputs with thickness, material, volume, or explicit asset identity.

Use solid representation for:

- pavement layer bodies when material thickness and volume matter
- curb, gutter, barrier, guardrail, median, and retaining-wall bodies
- bridge deck, girder, abutment, pier, bearing, and approach-slab bodies
- culvert barrels, headwalls, wing walls, pipes, inlets, manholes, and drainage structures
- structure-adjacent corridor cutouts where a closed volume is required
- IFC/export bodies where downstream consumers expect physical components
- construction or quantity bodies where closed volume is the required result

### 7.3 Non-overlap rule

Surface and solid outputs may be derived from the same `AppliedSectionSet`, but they must not replace each other.

- A surface is an open height field or TIN-family result.
- A solid is a closed or component-like body with thickness, material, volume, or asset identity.
- Viewer meshes generated from either one are presentation artifacts, not source truth.
- Editing must return to source models, replayable TIN edits, region rules, assembly rules, or explicit overrides rather than mutating generated surface or solid display geometry.

## 8. Surface Object Families

Recommended primary object families:

- `SurfaceModel`
- `SurfaceRow`
- `SurfaceBuildRelation`
- `SurfaceClipSet`
- `SurfaceComparisonSet`
- `SurfaceResolutionResult`

## 9. SurfaceModel Root

### 9.1 Purpose

`SurfaceModel` is the durable identity container for grouped surface results in a project or corridor context.

### 9.2 Recommended root fields

- `schema_version`
- `surface_model_id`
- `project_id`
- optional `corridor_id`
- `label`
- `surface_rows`
- `build_relation_rows`
- `comparison_rows`
- `source_refs`
- `diagnostic_rows`

### 9.3 Rule

The surface model should keep relationships between surface families explicit instead of scattering them across unrelated objects.

## 10. SurfaceRow

### 10.1 Purpose

Each `SurfaceRow` represents one meaningful surface result.

### 10.2 Recommended fields

- `surface_id`
- `surface_kind`
- `tin_ref`
- `status`
- `coordinate_context`
- `unit_context`
- `source_ref`
- `notes`

### 10.3 Recommended kinds

- `existing_ground_surface`
- `design_surface`
- `subgrade_surface`
- `daylight_surface`
- `drainage_surface`
- `comparison_surface`
- `volume_support_surface`
- `clipped_export_surface`

### 10.4 Rule

Every surface row should point to normalized TIN-family data rather than ad-hoc scene geometry.

## 11. SurfaceBuildRelation

### 11.1 Purpose

`SurfaceBuildRelation` preserves how one surface was derived from source terrain or corridor results.

### 11.2 Recommended fields

- `build_relation_id`
- `surface_ref`
- `relation_kind`
- `input_refs`
- `operation_summary`
- `notes`

### 11.3 Recommended relation kinds

- `corridor_build`
- `clip_build`
- `merge_build`
- `comparison_build`
- `import_normalization`

### 11.4 Rule

Surface provenance should remain explicit enough to answer what inputs and operations produced the result.

## 12. SurfaceClipSet

### 12.1 Purpose

`SurfaceClipSet` captures clipped or range-limited surface variants.

### 12.2 Recommended fields

- `clip_set_id`
- `surface_ref`
- `clip_kind`
- `clip_boundary_ref`
- `station_start`
- `station_end`
- `notes`

### 12.3 Recommended kinds

- `export_clip`
- `review_clip`
- `station_range_clip`
- `corridor_zone_clip`

### 12.4 Rule

Clipped surfaces should remain identifiable as derived variants, not replace the underlying parent surface silently.

## 13. SurfaceComparisonSet

### 13.1 Purpose

`SurfaceComparisonSet` preserves meaningful surface-to-surface comparison relationships.

### 13.2 Recommended fields

- `comparison_id`
- `base_surface_ref`
- `compare_surface_ref`
- `comparison_kind`
- `result_surface_ref`
- `notes`

### 13.3 Recommended kinds

- `design_vs_existing`
- `subgrade_vs_existing`
- `daylight_vs_existing`
- `volume_support_comparison`

### 13.4 Rule

Comparison relationships should be explicit result objects rather than hidden inside earthwork tools only.

## 14. Existing Ground vs Design Surface Policy

### 14.1 Rule

Existing-ground surfaces and corridor-derived design surfaces must remain explicitly distinguishable.

### 14.2 Why it matters

This distinction is required for:

- earthwork balance
- surface review
- exchange
- output validation

### 14.3 Recommended policy

Imported or normalized survey surfaces belong in the existing-ground family.

Corridor-generated results belong in design, subgrade, daylight, and comparison families.

## 15. Surface Build Services

Recommended service families:

- `SurfaceBuildService`
- `SurfaceClipService`
- `SurfaceMergeService`
- `SurfaceComparisonService`

These services should reuse TIN contracts and corridor semantics rather than inventing display-driven shortcuts.

Current implementation status:

- [x] define `SurfaceModel`, `SurfaceRow`, and `SurfaceBuildRelation`
- [x] build an initial corridor-derived surface family through `CorridorSurfaceService`
- [x] persist `V1SurfaceModel` under `03_Surfaces / Design TIN`
- [x] build first-slice design-surface ribbon mesh preview from applied-section frames
- [x] drive first-slice design-surface preview width from Assembly-derived left/right applied-section widths
- [x] build first-slice subgrade-surface ribbon mesh preview from Assembly-derived subgrade depth
- [x] build design and subgrade TIN previews from persisted `AppliedSectionPoint` rows when component-boundary point rows are available
- [x] add conditional `drainage_surface` rows when `AppliedSectionSet` contains ditch surface point rows
- [x] build first-slice drainage/ditch TIN previews from persisted `ditch_surface` point rows
- [x] build first-slice slope-face strip preview from Assembly-derived side-slope width and slope
- [x] tie first-slice slope-face outer points to sampled existing-ground TIN where an EG TIN preview is available
- [x] resolve actual slope-face intersection points against existing-ground TIN within the configured side-slope search width
- [x] expose slope-face EG intersection, outer-edge sample, and fallback diagnostics on the preview object and as 3D review markers
- [x] split slope-face fallback diagnostics into missing EG TIN and no EG hit within search width
- [x] expose Build Corridor output review rows for centerline, design surface, subgrade surface, slope-face surface, and drainage surface previews
- [ ] build full design, subgrade, and daylight TIN geometry from complete semantic section points
- [ ] add clipped review/export surface variants

## 16. SurfaceResolutionResult

### 16.1 Purpose

This result object captures the active or selected surface context for downstream consumers.

### 16.2 Recommended fields

- `resolution_id`
- `selected_surface_ids`
- `selected_comparison_ids`
- `diagnostic_rows`
- `notes`

### 16.3 Rule

Resolution results are derived helper objects, not new source data.

## 17. Relationship to Earthwork Balance

`SurfaceModel` is one of the main upstream inputs to earthwork analysis.

It should provide:

- explicit EG vs design surface relationships
- surface comparison support
- clipped analysis ranges where needed
- provenance and confidence context

`EarthworkBalanceModel` should consume normalized surface families, not unlabeled viewer meshes.

## 18. Relationship to Outputs and Exchange

The surface subsystem is a main upstream source for:

- `SurfaceOutput`
- `EarthworkBalanceOutput`
- `LandXML` surface export
- 3D review overlays

Output and exchange systems should consume normalized surface rows and build relations instead of rebuilding surface meaning from scratch.

## 19. Relationship to Viewer and 3D Review

Viewer and 3D review systems may consume surface-derived context through:

- surface overlays
- clipped review surfaces
- comparison highlights
- daylight boundary review

But they must not become the new surface source.

Review systems should inspect surface identity and provenance, not mutate surface definitions directly.

## 20. Diagnostics

Diagnostics should be produced when:

- a corridor-derived surface cannot be built completely
- a clip boundary is invalid
- a merge loses provenance clarity
- a comparison surface is inconsistent
- a surface row references missing TIN data

Recommended diagnostic fields:

- `diagnostic_id`
- `severity`
- `kind`
- `source_ref`
- optional `surface_ref`
- `message`
- `notes`

## 21. Identity and Provenance

Surface objects should preserve:

- stable `surface_id`
- related `corridor_id` where applicable
- `tin_ref`
- build relation identity
- import or build provenance
- scenario or candidate status where applicable

This is important for:

- surface review
- earthwork comparison
- exchange packaging
- AI-assisted alternative evaluation

## 22. Validation Rules

Validation should check for:

- missing TIN references
- invalid surface kind combinations
- orphaned clipped surfaces
- invalid comparison relationships
- mismatched coordinate or unit context
- degraded build relations with missing inputs

Validation results should be recorded in `diagnostic_rows`.

## 23. AI and Alternative Design

AI-assisted workflows may propose:

- alternative surface sets tied to corridor candidates
- clipped comparison views for review
- earthwork-aware design surface comparisons
- daylight-surface improvement scenarios

But accepted changes must still flow through normalized corridor and surface recompute.

The AI layer must not keep a hidden surface world outside the TIN and surface contracts.

## 24. Anti-Patterns

The following should be avoided:

- treating display meshes as surface truth
- exporting surfaces from untracked viewer geometry
- losing EG vs design distinction
- hiding comparison logic inside one earthwork-only tool
- rebuilding surface meaning independently in every consumer

## 25. Summary

In v1, `SurfaceModel` is the derived result model for:

- grouped engineering surface families
- corridor-derived design, subgrade, and daylight surfaces
- clipped and comparison surfaces
- traceable surface provenance

It should remain TIN-based and provenance-aware, so that:

- `CorridorModel` can hand off stable surface results
- earthwork balance can compare surfaces reliably
- exchange and outputs can package surfaces consistently
- review systems can inspect surface context without replacing source truth
