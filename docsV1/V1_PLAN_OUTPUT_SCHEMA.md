# CorridorRoad V1 Plan Output Schema

Date: 2026-04-23
Branch: `v1-dev`
Status: Draft baseline
Depends on:

- `docsV1/V1_OUTPUT_STRATEGY.md`
- `docsV1/V1_PLAN_PROFILE_SHEET_PLAN.md`
- `docsV1/V1_EXCHANGE_PLAN.md`
- `docsV1/V1_3D_REVIEW_DISPLAY_PLAN.md`

## 1. Purpose

This document defines the normalized `PlanOutput` contract for v1.

It exists so that:

- plan sheets
- DXF plan exports
- plan-oriented review tools
- 3D plan overlays

can consume the same plan payload instead of deriving their own incompatible interpretations.

## 2. Scope

This schema covers:

- plan-view geometry payloads
- station and alignment annotation rows
- region and structure references
- terrain and breakline context rows
- plan-level summary and diagnostic rows

This schema does not define:

- profile geometry
- section geometry
- final DXF writer format details

## 3. Core Rule

`PlanOutput` is a derived output contract.

It is not a source authoring model.

Consumers may render or export it, but they must not treat it as the durable engineering source of truth.

## 4. Schema Versioning

Recommended initial version:

- `PlanOutputSchemaVersion = 1`

## 5. PlanOutput Root Structure

Recommended top-level fields:

- `schema_version`
- `plan_output_id`
- `project_id`
- `alignment_id`
- `label`
- `unit_context`
- `coordinate_context`
- `selection_scope`
- `geometry_rows`
- `station_rows`
- `region_rows`
- `structure_rows`
- `terrain_rows`
- `breakline_rows`
- `annotation_rows`
- `summary_rows`
- `diagnostic_rows`

## 6. Required Root Metadata

### 6.1 Identity fields

Required fields should include:

- `plan_output_id`
- `project_id`
- `alignment_id`

### 6.2 Label field

Recommended field:

- `label`

This should provide a human-readable identifier for the plan output package.

### 6.3 Scope field

Recommended field:

- `selection_scope`

This should record whether the plan output represents:

- full alignment
- station range
- review subset
- export subset

## 7. Unit Context

Recommended fields:

- `linear_unit`
- optional `angle_unit`

Rule:

Plan outputs must not rely on silent unit assumptions.

## 8. Coordinate Context

Recommended fields:

- `coordinate_mode`
- `crs_code`
- `origin_mode`
- `north_rotation`
- `notes`

Rule:

Plan outputs must explicitly preserve enough coordinate context for:

- sheet generation
- DXF export
- 3D plan overlay

## 9. Geometry Rows

### 9.1 Purpose

`geometry_rows` carry plan-view geometry primitives.

### 9.2 Recommended geometry row fields

- `row_id`
- `kind`
- `x_values`
- `y_values`
- `closed`
- `style_role`
- `source_ref`

### 9.3 Recommended geometry row kinds

- `alignment_centerline`
- `reference_polyline`
- `region_extent_line`
- `structure_outline`
- `terrain_boundary`
- `breakline`
- `marker_line`

### 9.4 Rule

Geometry rows should be renderable and exportable, but semantic meaning should also be preserved in dedicated row families.

## 10. Station Rows

### 10.1 Purpose

`station_rows` define station labels and reference markers in plan view.

### 10.2 Recommended fields

- `station_row_id`
- `station`
- `station_label`
- `x`
- `y`
- `kind`
- `priority`
- `notes`

### 10.3 Recommended kinds

- `regular_station`
- `key_station`
- `region_boundary_station`
- `event_station`

## 11. Region Rows

### 11.1 Purpose

`region_rows` preserve station-range policy context in plan space.

### 11.2 Recommended fields

- `region_row_id`
- `region_id`
- `region_kind`
- `start_station`
- `end_station`
- `geometry_ref`
- `notes`

### 11.3 Rule

Region rows should let plan consumers highlight and annotate policy ranges without re-reading region logic directly from internal models.

## 12. Structure Rows

### 12.1 Purpose

`structure_rows` describe structure presence and interaction context in plan output.

### 12.2 Recommended fields

- `structure_row_id`
- `structure_id`
- `kind`
- `x`
- `y`
- `geometry_ref`
- `notes`

### 12.3 Recommended kinds

- `structure_marker`
- `structure_outline`
- `structure_zone`

## 13. Terrain Rows

### 13.1 Purpose

`terrain_rows` preserve terrain-related plan context.

### 13.2 Recommended fields

- `terrain_row_id`
- `surface_id`
- `kind`
- `geometry_ref`
- `notes`

### 13.3 Recommended kinds

- `surface_boundary`
- `coverage_extent`
- `terrain_warning_zone`

## 14. Breakline Rows

### 14.1 Purpose

`breakline_rows` preserve terrain breakline context where plan consumers need it.

### 14.2 Recommended fields

- `breakline_row_id`
- `breakline_id`
- `kind`
- `geometry_ref`
- `notes`

### 14.3 Recommended kinds

- `hard_breakline`
- `soft_breakline`
- `feature_line`

## 15. Annotation Rows

### 15.1 Purpose

`annotation_rows` provide plan-oriented text and lightweight annotation content.

### 15.2 Recommended fields

- `annotation_id`
- `kind`
- `label`
- `x`
- `y`
- `priority`
- `related_ref_id`

### 15.3 Recommended kinds

- `station_label`
- `region_label`
- `structure_label`
- `note_label`

## 16. Summary Rows

### 16.1 Purpose

`summary_rows` provide compact rollups for sheets and previews.

### 16.2 Recommended fields

- `summary_id`
- `kind`
- `label`
- `value`
- `priority`

### 16.3 Recommended kinds

- `alignment_summary`
- `range_summary`
- `region_summary`
- `terrain_summary`
- `structure_summary`

## 17. Diagnostic Rows

### 17.1 Purpose

`diagnostic_rows` surface plan-related output issues.

### 17.2 Recommended fields

- `diagnostic_id`
- `severity`
- `kind`
- `message`
- `related_ref_id`
- `action_hint`

### 17.3 Recommended kinds

- `missing_alignment_geometry`
- `missing_station_rows`
- `region_mapping_warning`
- `terrain_context_missing`
- `coordinate_context_warning`

## 18. Selection Scope

Recommended fields:

- `scope_kind`
- `station_start`
- `station_end`
- `alignment_id`
- `notes`

Recommended scope kinds:

- `whole_alignment`
- `station_range`
- `sheet_subset`
- `review_subset`

## 19. Consumer Rule

The following consumers should use `PlanOutput` directly where practical:

- plan sheets
- DXF plan exporters
- plan preview tools
- 3D plan overlays

If a consumer needs additional meaning, the schema should be extended instead of duplicating hidden logic.

## 20. Validation Rules

The plan-output schema should be validated for:

- missing required root metadata
- empty geometry rows with no diagnostics
- station rows outside output scope
- broken geometry references
- missing coordinate context

## 21. Anti-Patterns to Avoid

Avoid the following:

- writing plan exports directly from scattered document objects
- storing only raw polylines with no station or region semantics
- deriving plan annotations differently in every consumer
- treating 3D plan overlay geometry as the real plan export source

## 22. Recommended Follow-Up Documents

This schema document should be followed by:

1. `V1_PROFILE_OUTPUT_SCHEMA.md`
2. `V1_SHEET_LAYOUT_HINT_SCHEMA.md`
3. `V1_LANDXML_MAPPING_PLAN.md`

## 23. Final Rule

In v1, `PlanOutput` should be the shared plan-view contract for drawing, export, and review consumers.
