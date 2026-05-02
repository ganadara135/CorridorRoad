# CorridorRoad V1 Surface Output Schema

Date: 2026-04-23
Branch: `v1-dev`
Status: Draft baseline
Depends on:

- `docsV1/V1_OUTPUT_STRATEGY.md`
- `docsV1/V1_SURFACE_MODEL.md`
- `docsV1/V1_TIN_DATA_SCHEMA.md`
- `docsV1/V1_EXCHANGE_OUTPUT_SCHEMA.md`

## 1. Purpose

This document defines the normalized `SurfaceOutput` contract for v1.

It exists so that:

- surface review tools
- surface reports and sheets
- 3D surface overlays
- exchange packaging helpers

can consume the same surface payload instead of rebuilding surface meaning independently.

## 2. Scope

This schema covers:

- surface output root metadata
- surface family rows
- boundary, void, and clip rows
- quality, provenance, and comparison rows
- summary and diagnostic rows

This schema does not define:

- low-level triangulation algorithm behavior
- raw survey import rules
- final viewer styling behavior

## 3. Core Rule

`SurfaceOutput` is a derived output contract built from normalized surface and TIN results.

It is not a source authoring model.

Consumers may render, export, compare, or summarize it, but they must not treat it as the durable engineering source of truth.

## 4. Schema Versioning

Recommended initial version:

- `SurfaceOutputSchemaVersion = 1`

## 5. SurfaceOutput Root Structure

Recommended top-level fields:

- `schema_version`
- `surface_output_id`
- `project_id`
- optional `corridor_id`
- `label`
- `unit_context`
- `coordinate_context`
- `selection_scope`
- `source_refs`
- `result_refs`
- `surface_rows`
- `boundary_rows`
- `void_rows`
- `clip_rows`
- `comparison_rows`
- `quality_rows`
- `provenance_rows`
- `summary_rows`
- `diagnostic_rows`

## 6. Required Root Metadata

### 6.1 Identity fields

Required fields should include:

- `surface_output_id`
- `project_id`

### 6.2 Optional corridor scope

Recommended optional field:

- `corridor_id`

This should be present when the output is corridor-scoped rather than project-global.

### 6.3 Label field

Recommended field:

- `label`

This should provide a human-readable identifier for the output package.

## 7. Unit Context

### 7.1 Purpose

`unit_context` ensures that surface values are interpretable without silent assumptions.

### 7.2 Recommended fields

- `linear_unit`
- `area_unit`
- `volume_unit`

### 7.3 Rule

Surface outputs must not rely on hidden unit conventions.

## 8. Coordinate Context

### 8.1 Purpose

`coordinate_context` records spatial interpretation for review and export.

### 8.2 Recommended fields

- `coordinate_mode`
- `crs_code`
- `origin_mode`
- `north_rotation`
- `notes`

### 8.3 Rule

Surface outputs must preserve enough coordinate context for:

- 3D review overlays
- LandXML export
- clipped review and report workflows

## 9. Selection Scope

### 9.1 Purpose

`selection_scope` records what portion of the project or corridor the output represents.

### 9.2 Recommended fields

- `scope_kind`
- optional `alignment_id`
- optional `corridor_id`
- optional `station_start`
- optional `station_end`
- optional `surface_ids`
- optional `scenario_id`
- `notes`

### 9.3 Recommended scope kinds

- `project_surface_set`
- `corridor_surface_set`
- `station_range_surface_set`
- `review_subset`
- `export_subset`

## 10. Source References

### 10.1 Purpose

`source_refs` identify which normalized source models contributed to the surface output.

### 10.2 Recommended fields

- `ref_id`
- `source_kind`
- `source_id`
- `label`
- `notes`

### 10.3 Recommended source kinds

- `survey_source`
- `alignment`
- `profile`
- `region`
- `structure`

## 11. Result References

### 11.1 Purpose

`result_refs` identify which derived result families contributed to the output.

### 11.2 Recommended fields

- `ref_id`
- `result_kind`
- `result_id`
- `label`
- `notes`

### 11.3 Recommended result kinds

- `surface`
- `applied_section_set`
- `corridor_result`
- `earthwork_result`

## 12. Surface Rows

### 12.1 Purpose

`surface_rows` carry the primary engineering surface payloads represented by the output.

### 12.2 Recommended surface row fields

- `surface_row_id`
- `surface_id`
- `surface_kind`
- `tin_ref`
- `status`
- optional `parent_surface_ref`
- optional `comparison_ref`
- `notes`

### 12.3 Recommended surface kinds

- `existing_ground_surface`
- `design_surface`
- `subgrade_surface`
- `daylight_surface`
- `comparison_surface`
- `volume_support_surface`
- `clipped_export_surface`

### 12.4 Rule

Surface rows should identify meaningful surface families, not just pass through unlabeled TIN objects.

## 13. Boundary Rows

### 13.1 Purpose

`boundary_rows` carry boundary information needed by review, output, and export consumers.

### 13.2 Recommended boundary row fields

- `boundary_row_id`
- `surface_ref`
- `boundary_kind`
- `vertex_refs`
- `closed`
- `notes`

### 13.3 Recommended boundary kinds

- `outer_boundary`
- `clip_boundary`
- `review_boundary`
- `export_boundary`

## 14. Void Rows

### 14.1 Purpose

`void_rows` carry hole or excluded-area information for surface outputs.

### 14.2 Recommended void row fields

- `void_row_id`
- `surface_ref`
- `void_kind`
- `vertex_refs`
- `closed`
- `notes`

### 14.3 Recommended void kinds

- `hole`
- `excluded_area`
- `invalid_surface_zone`

## 15. Clip Rows

### 15.1 Purpose

`clip_rows` preserve clipped or range-limited surface variants.

### 15.2 Recommended clip row fields

- `clip_row_id`
- `surface_ref`
- `clip_kind`
- optional `clip_boundary_ref`
- optional `station_start`
- optional `station_end`
- `notes`

### 15.3 Recommended clip kinds

- `export_clip`
- `review_clip`
- `station_range_clip`
- `corridor_zone_clip`

## 16. Comparison Rows

### 16.1 Purpose

`comparison_rows` carry explicit surface comparison relationships.

### 16.2 Recommended comparison row fields

- `comparison_row_id`
- `comparison_id`
- `comparison_kind`
- `base_surface_ref`
- `compare_surface_ref`
- optional `result_surface_ref`
- `notes`

### 16.3 Recommended comparison kinds

- `design_vs_existing`
- `subgrade_vs_existing`
- `daylight_vs_existing`
- `volume_support_comparison`

### 16.4 Rule

Surface comparison rows should remain explicit instead of being hidden only in earthwork tooling.

## 17. Quality Rows

### 17.1 Purpose

`quality_rows` preserve measurable validation and quality context for surface outputs.

### 17.2 Recommended quality row fields

- `quality_row_id`
- optional `surface_ref`
- `kind`
- optional `value`
- optional `unit`
- `notes`

### 17.3 Recommended kinds

- `triangle_count`
- `degenerate_triangle_count`
- `boundary_integrity`
- `sampling_confidence`
- `comparison_confidence`

## 18. Provenance Rows

### 18.1 Purpose

`provenance_rows` preserve how each surface output was derived.

### 18.2 Recommended provenance row fields

- `provenance_row_id`
- optional `surface_ref`
- `relation_kind`
- `input_refs`
- `operation_summary`
- `notes`

### 18.3 Recommended relation kinds

- `corridor_build`
- `import_normalization`
- `clip_build`
- `merge_build`
- `comparison_build`

## 19. Summary Rows

### 19.1 Purpose

`summary_rows` provide compact, display-friendly surface rollups.

### 19.2 Recommended summary row fields

- `summary_id`
- `kind`
- `label`
- optional `value`
- optional `unit`
- `notes`

### 19.3 Recommended kinds

- `surface_count`
- `design_surface_summary`
- `daylight_surface_summary`
- `comparison_summary`
- `quality_summary`

## 20. Diagnostic Rows

### 20.1 Purpose

`diagnostic_rows` surface engineering and traceability issues in a normalized way.

### 20.2 Recommended diagnostic row fields

- `diagnostic_id`
- `severity`
- `kind`
- optional `surface_ref`
- optional `comparison_ref`
- `message`
- `notes`

### 20.3 Recommended kinds

- `missing_tin_reference`
- `invalid_boundary`
- `invalid_void`
- `orphaned_clip`
- `comparison_inconsistency`
- `traceability_loss`

## 21. Relationship to TIN Data Schema

`SurfaceOutput` should reference normalized TIN-family data rather than duplicate the full TIN schema.

Architectural rule:

- `V1_TIN_DATA_SCHEMA.md` defines TIN storage and topology contracts
- `SurfaceOutput` defines the output-facing organization of meaningful surface families

This keeps output contracts lighter while preserving engineering meaning.

## 22. Relationship to Earthwork and Exchange

Surface outputs are a major upstream input to:

- `EarthworkBalanceOutput`
- `MassHaulOutput`
- `ExchangeOutput`

Earthwork and exchange systems should consume normalized surface rows and provenance instead of reconstructing surfaces from display state.

## 23. Relationship to Viewer and Reports

Viewer and report systems may consume:

- surface rows for family selection
- boundary and void rows for display context
- comparison rows for review
- quality and provenance rows for diagnostics

But they must not become the new surface source.

## 24. Validation Rules

Validation should check for:

- missing TIN references
- inconsistent coordinate context
- orphaned boundary or void rows
- clipped outputs with no parent surface context
- comparison rows with incompatible surfaces

Validation results should appear in `diagnostic_rows`.

## 25. Anti-Patterns

The following should be avoided:

- treating exported or displayed meshes as surface truth
- duplicating full TIN topology in every output consumer
- hiding comparison semantics inside one report or viewer
- losing provenance during clipping or export packaging
- mixing earthwork totals directly into surface rows with no clear meaning

## 26. Summary

In v1, `SurfaceOutput` is the normalized output contract for:

- meaningful surface families
- boundary, void, and clip context
- surface comparison relationships
- quality and provenance reporting
- review and exchange-ready surface packaging

It should remain consistent with `SurfaceModel` and TIN contracts, so that:

- review tools can inspect surfaces coherently
- exchange packaging can reference stable surface outputs
- earthwork workflows can rely on explicit surface identity
- output systems do not rebuild surface meaning independently
