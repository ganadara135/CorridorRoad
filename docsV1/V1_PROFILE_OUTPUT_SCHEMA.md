# CorridorRoad V1 Profile Output Schema

Date: 2026-04-23
Branch: `v1-dev`
Status: Draft baseline
Depends on:

- `docsV1/V1_PLAN_PROFILE_SHEET_PLAN.md`
- `docsV1/V1_EARTHWORK_BALANCE_PLAN.md`
- `docsV1/V1_3D_REVIEW_DISPLAY_PLAN.md`
- `docsV1/V1_OUTPUT_STRATEGY.md`

## 1. Purpose

This document defines the normalized `ProfileOutput` contract for v1.

It exists so that:

- profile sheets
- profile previews
- 3D profile overlays
- mass-haul/profile-linked review
- DXF profile exports

can consume the same profile payload family.

## 2. Scope

This schema covers:

- EG and FG profile rows
- PVI and grade-transition rows
- structure/profile interaction rows
- optional earthwork and mass-haul attachment rows
- summary and diagnostic rows

This schema does not define:

- section geometry
- plan geometry
- final sheet layout behavior

## 3. Core Rule

`ProfileOutput` is a derived contract built from profile-related source and result data.

It is not a source authoring model.

Consumers may review or export it, but must not treat it as the durable source of vertical design truth.

## 4. Schema Versioning

Recommended initial version:

- `ProfileOutputSchemaVersion = 1`

## 5. ProfileOutput Root Structure

Recommended top-level fields:

- `schema_version`
- `profile_output_id`
- `project_id`
- `alignment_id`
- `profile_id`
- `label`
- `unit_context`
- `coordinate_context`
- `selection_scope`
- `line_rows`
- `pvi_rows`
- `grade_rows`
- `structure_rows`
- `earthwork_rows`
- `annotation_rows`
- `summary_rows`
- `diagnostic_rows`

## 6. Required Root Metadata

Required fields should include:

- `profile_output_id`
- `project_id`
- `alignment_id`
- `profile_id`

Recommended optional fields:

- `label`
- `selection_scope`

## 7. Unit Context

Recommended fields:

- `linear_unit`
- `slope_unit`
- optional `area_unit`
- optional `volume_unit`

Rule:

Profile outputs must make numeric interpretation explicit.

## 8. Coordinate Context

Recommended fields:

- `coordinate_mode`
- `station_reference_mode`
- `vertical_reference`
- `notes`

Rule:

Profile consumers must know whether the profile is interpreted in local station/elevation space and how vertical context is defined.

## 9. Line Rows

### 9.1 Purpose

`line_rows` represent the actual EG/FG and related longitudinal traces.

### 9.2 Recommended fields

- `line_row_id`
- `kind`
- `station_values`
- `elevation_values`
- `style_role`
- `source_ref`

### 9.3 Recommended kinds

- `existing_ground_line`
- `finished_grade_line`
- `design_reference_line`
- `comparison_line`

## 10. PVI Rows

### 10.1 Purpose

`pvi_rows` preserve PVI-related control information for review and output.

### 10.2 Recommended fields

- `pvi_row_id`
- `station`
- `elevation`
- `label`
- `notes`

### 10.3 Rule

PVI rows should remain identifiable in profile outputs even if different consumers render them differently.

## 11. Grade Rows

### 11.1 Purpose

`grade_rows` describe grade-related segments and transitions.

### 11.2 Recommended fields

- `grade_row_id`
- `station_start`
- `station_end`
- `grade_value`
- `kind`
- `notes`

### 11.3 Recommended kinds

- `tangent_grade`
- `vertical_curve`
- `transition_grade`

## 12. Structure Rows

### 12.1 Purpose

`structure_rows` preserve structure/profile interaction context.

### 12.2 Recommended fields

- `structure_row_id`
- `structure_id`
- `kind`
- `station`
- `elevation`
- `notes`

### 12.3 Recommended kinds

- `structure_marker`
- `clearance_marker`
- `crossing_marker`
- `profile_conflict_zone`

## 13. Earthwork Rows

### 13.1 Purpose

`earthwork_rows` attach earthwork-balance and mass-haul context to profile outputs.

### 13.2 Recommended fields

- `earthwork_row_id`
- `kind`
- `station_start`
- `station_end`
- `value`
- `unit`
- `notes`

### 13.3 Recommended kinds

- `mass_haul_curve_segment`
- `balance_point`
- `borrow_zone`
- `waste_zone`
- `surplus_range`
- `deficit_range`

### 13.4 Rule

Earthwork rows included in profile outputs should be derived from normalized earthwork outputs, not re-computed inside profile renderers.

## 14. Annotation Rows

### 14.1 Purpose

`annotation_rows` carry text or lightweight annotation data needed by profile consumers.

### 14.2 Recommended fields

- `annotation_id`
- `kind`
- `label`
- `station`
- `elevation`
- `priority`
- `related_ref_id`

### 14.3 Recommended kinds

- `pvi_label`
- `grade_label`
- `structure_label`
- `earthwork_label`
- `note_label`

## 15. Summary Rows

### 15.1 Purpose

`summary_rows` provide compact rollups for profile views and profile sheets.

### 15.2 Recommended fields

- `summary_id`
- `kind`
- `label`
- `value`
- `priority`

### 15.3 Recommended kinds

- `profile_summary`
- `grade_summary`
- `earthwork_summary`
- `structure_summary`

## 16. Diagnostic Rows

### 16.1 Purpose

`diagnostic_rows` surface profile-output issues and caveats.

### 16.2 Recommended fields

- `diagnostic_id`
- `severity`
- `kind`
- `message`
- `related_ref_id`
- `action_hint`

### 16.3 Recommended kinds

- `missing_profile_line`
- `missing_pvi_rows`
- `coordinate_context_warning`
- `earthwork_attachment_missing`
- `structure_profile_conflict_warning`

## 17. Selection Scope

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

## 18. Consumer Rule

The following consumers should use `ProfileOutput` directly where practical:

- profile sheets
- DXF profile exporters
- 3D profile overlays
- mass-haul/profile review tools

If a consumer needs more meaning, the schema should be extended instead of hidden logic being duplicated.

## 19. Earthwork Integration Rule

When earthwork information is shown in profile context:

- it should remain traceable to earthwork result objects
- profile output should not pretend to own earthwork truth
- balance and mass-haul information should remain clearly labeled as attached analytical context

## 20. Validation Rules

The profile-output schema should be validated for:

- missing required root metadata
- mismatched station/elevation row lengths
- empty line rows with no diagnostics
- invalid station scopes
- missing coordinate context

## 21. Anti-Patterns to Avoid

Avoid the following:

- computing different EG/FG meaning in each renderer
- drawing mass-haul data without normalized earthwork rows
- hiding vertical context assumptions
- using 3D overlay geometry as the real profile export source

## 22. Recommended Follow-Up Documents

This schema document should be followed by:

1. `V1_SHEET_LAYOUT_HINT_SCHEMA.md`
2. `V1_LANDXML_MAPPING_PLAN.md`
3. `V1_DXF_MAPPING_PLAN.md`

## 23. Final Rule

In v1, `ProfileOutput` should be the shared longitudinal-view contract for profile drawing, export, and review consumers.
