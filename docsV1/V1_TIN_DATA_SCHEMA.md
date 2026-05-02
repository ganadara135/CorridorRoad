# CorridorRoad V1 TIN Data Schema

Date: 2026-04-23
Branch: `v1-dev`
Status: Draft baseline
Depends on:

- `docsV1/V1_TIN_ENGINE_PLAN.md`
- `docsV1/V1_ARCHITECTURE.md`
- `docsV1/V1_EXCHANGE_OUTPUT_SCHEMA.md`

## 1. Purpose

This document defines the normalized internal data schema for TIN-related objects in v1.

It exists so that terrain ingestion, triangulation, sampling, comparison, and exchange can rely on a shared data contract.

## 2. Scope

This schema covers:

- point sets
- breakline sets
- boundary sets
- void boundary sets
- TIN surface roots
- vertex rows
- face rows
- quality and provenance metadata

This schema does not define:

- triangulation algorithm implementation
- UI import workflows
- sheet or viewer rendering details

## 3. Core Rule

TIN data should be stored in a normalized structure that preserves:

- geometry
- topology
- source provenance
- coordinate context
- quality metadata

The TIN schema must not collapse into "just a mesh" too early.

## 4. Schema Versioning

Recommended initial versions:

- `TINSourceSchemaVersion = 1`
- `TINSurfaceSchemaVersion = 1`

## 5. TIN Source Families

Recommended source families:

- `SurveyPointSet`
- `BreaklineSet`
- `BoundarySet`
- `VoidBoundarySet`

Recommended result families:

- `SurveyTIN`
- `ExistingGroundTIN`
- `DesignTIN`
- `SubgradeTIN`
- `DaylightTIN`
- `VolumeSurface`

## 6. Common Metadata Fields

Recommended common root fields for all TIN-related objects:

- `schema_version`
- `object_id`
- `object_kind`
- `project_id`
- `label`
- `unit_context`
- `coordinate_context`
- `source_refs`
- `diagnostic_rows`

## 7. Point Set Schema

### 7.1 Root fields

Recommended fields:

- `schema_version`
- `point_set_id`
- `point_set_kind`
- `project_id`
- `point_rows`
- `unit_context`
- `coordinate_context`
- `source_refs`
- `diagnostic_rows`

### 7.2 Point rows

Recommended point row fields:

- `point_id`
- `x`
- `y`
- `z`
- `point_role`
- `source_row_ref`
- `notes`

### 7.3 Recommended point roles

- `survey_point`
- `mass_point`
- `control_point`
- `boundary_support_point`

## 8. Breakline Set Schema

### 8.1 Root fields

Recommended fields:

- `schema_version`
- `breakline_set_id`
- `project_id`
- `breakline_rows`
- `unit_context`
- `coordinate_context`
- `source_refs`
- `diagnostic_rows`

### 8.2 Breakline rows

Recommended fields:

- `breakline_id`
- `kind`
- `vertex_refs`
- `closed`
- `enforced`
- `source_row_ref`
- `notes`

### 8.3 Recommended breakline kinds

- `hard_breakline`
- `soft_breakline`
- `feature_line`
- `ridge_line`
- `toe_line`

## 9. Boundary Set Schema

### 9.1 Root fields

Recommended fields:

- `schema_version`
- `boundary_set_id`
- `project_id`
- `boundary_rows`
- `unit_context`
- `coordinate_context`
- `source_refs`
- `diagnostic_rows`

### 9.2 Boundary rows

Recommended fields:

- `boundary_id`
- `kind`
- `vertex_refs`
- `closed`
- `priority`
- `notes`

### 9.3 Recommended boundary kinds

- `outer_boundary`
- `clip_boundary`
- `review_boundary`
- `export_boundary`

## 10. Void Boundary Schema

### 10.1 Root fields

Recommended fields:

- `schema_version`
- `void_boundary_set_id`
- `project_id`
- `void_rows`
- `unit_context`
- `coordinate_context`
- `source_refs`
- `diagnostic_rows`

### 10.2 Void rows

Recommended fields:

- `void_id`
- `kind`
- `vertex_refs`
- `closed`
- `notes`

### 10.3 Recommended kinds

- `hole`
- `excluded_area`
- `invalid_surface_zone`

## 11. TIN Surface Root Schema

### 11.1 Root fields

Recommended fields:

- `schema_version`
- `surface_id`
- `surface_kind`
- `project_id`
- `label`
- `vertex_rows`
- `face_rows`
- `breakline_refs`
- `boundary_refs`
- `void_refs`
- `quality_rows`
- `provenance_rows`
- `unit_context`
- `coordinate_context`
- `diagnostic_rows`

### 11.2 Recommended surface kinds

- `survey_tin`
- `existing_ground_tin`
- `design_tin`
- `subgrade_tin`
- `daylight_tin`
- `volume_surface`

## 12. Vertex Row Schema

### 12.1 Purpose

`vertex_rows` store the vertex list for a TIN surface.

### 12.2 Recommended fields

- `vertex_id`
- `x`
- `y`
- `z`
- `source_point_ref`
- `notes`

## 13. Face Row Schema

### 13.1 Purpose

`face_rows` store triangle topology.

### 13.2 Recommended fields

- `face_id`
- `v1`
- `v2`
- `v3`
- `face_kind`
- `quality_ref`
- `notes`

### 13.3 Recommended face kinds

- `primary_triangle`
- `boundary_triangle`
- `clipped_triangle`
- `merged_triangle`

## 14. Provenance Rows

### 14.1 Purpose

`provenance_rows` preserve source lineage.

### 14.2 Recommended fields

- `provenance_id`
- `source_kind`
- `source_id`
- `operation_kind`
- `notes`

### 14.3 Recommended operation kinds

- `imported`
- `triangulated`
- `clipped`
- `merged`
- `converted`

## 15. Quality Rows

### 15.1 Purpose

`quality_rows` preserve measurable quality or validation context.

### 15.2 Recommended fields

- `quality_id`
- `kind`
- `value`
- `unit`
- `severity`
- `notes`

### 15.3 Recommended kinds

- `point_count`
- `triangle_count`
- `degenerate_triangle_count`
- `sparse_coverage_warning`
- `boundary_validity`
- `breakline_validity`

## 16. Unit Context

Recommended fields:

- `linear_unit`
- `area_unit`
- `volume_unit`

Rule:

TIN data must not rely on silent unit interpretation.

## 17. Coordinate Context

Recommended fields:

- `coordinate_mode`
- `crs_code`
- `origin_mode`
- `north_rotation`
- `notes`

Rule:

TIN coordinates must preserve enough context to support local/world transformation and exchange.

## 18. Diagnostic Rows

Recommended fields:

- `diagnostic_id`
- `severity`
- `kind`
- `message`
- `related_ref_id`
- `action_hint`

Recommended kinds:

- `duplicate_point`
- `invalid_boundary`
- `invalid_breakline`
- `degenerate_triangle`
- `triangulation_gap`
- `coordinate_ambiguity`

## 19. Reference Rules

### 19.1 Vertex reference rule

Boundary, breakline, and void rows should reference stable vertex or point identities when practical.

### 19.2 Surface reference rule

TIN surfaces should preserve references back to source sets when possible.

### 19.3 Exchange reference rule

The schema should be mappable into `surface_rows`, `boundary_rows`, and related exchange payloads without lossy ad-hoc reconstruction.

## 20. Validation Rules

The TIN schema should be validated for:

- missing root metadata
- duplicate vertex ids
- invalid face vertex references
- non-closed boundaries where closure is required
- malformed void boundaries
- missing coordinate context
- inconsistent source references

## 21. Anti-Patterns to Avoid

Avoid the following:

- storing only opaque mesh blobs with no topology rows
- losing boundary and breakline identities after triangulation
- mixing local/world semantics implicitly
- making exchange rely on display meshes instead of normalized TIN rows

## 22. Recommended Follow-Up Documents

This schema document should be followed by:

1. `V1_TIN_SAMPLING_CONTRACT.md`
2. `V1_SURFACE_OUTPUT_SCHEMA.md`
3. `V1_LANDXML_MAPPING_PLAN.md`

## 23. Final Rule

In v1, TIN data should remain a first-class structured dataset with identity, topology, provenance, and quality metadata.
