# CorridorRoad V1 Sheet Layout Hint Schema

Date: 2026-04-23
Branch: `v1-dev`
Status: Draft baseline
Depends on:

- `docsV1/V1_PLAN_PROFILE_SHEET_PLAN.md`
- `docsV1/V1_SECTION_OUTPUT_SCHEMA.md`
- `docsV1/V1_PLAN_OUTPUT_SCHEMA.md`
- `docsV1/V1_PROFILE_OUTPUT_SCHEMA.md`

## 1. Purpose

This document defines the normalized sheet-layout hint contract for v1.

It exists to provide a shared, non-engineering layout layer for:

- plan sheets
- profile sheets
- section sheets
- DXF sheet export
- future SVG or print-oriented sheet outputs

## 2. Core Rule

Layout hints guide presentation.

They do not redefine engineering meaning.

Engineering data must come from normalized output contracts first. Layout hints only tell consumers how to organize and present that data.

## 3. Scope

This schema covers:

- sheet-level hints
- panel-level hints
- label and dimension visibility hints
- grouping and ordering hints
- summary-block hints

This schema does not define:

- output geometry
- engineering calculations
- final CAD-layer implementation details

## 4. Schema Versioning

Recommended initial version:

- `SheetLayoutHintSchemaVersion = 1`

## 5. SheetLayoutHints Root Structure

Recommended top-level fields:

- `schema_version`
- `sheet_layout_hint_id`
- `sheet_kind`
- `target_output_kind`
- `preferred_scale`
- `panel_rows`
- `label_rows`
- `dimension_rows`
- `summary_rows`
- `metadata_rows`
- `diagnostic_rows`

## 6. Sheet Kind

Recommended `sheet_kind` values:

- `plan_sheet`
- `profile_sheet`
- `section_sheet`
- `combined_sheet`

## 7. Target Output Kind

Recommended `target_output_kind` values:

- `plan_output`
- `profile_output`
- `section_output`
- `section_sheet_output`

## 8. Preferred Scale

### 8.1 Purpose

`preferred_scale` indicates the intended sheet scaling context.

### 8.2 Recommended fields

- `numerator`
- `denominator`
- `notes`

### 8.3 Rule

This is a hint, not a promise that every consumer can realize the exact same scale automatically.

## 9. Panel Rows

### 9.1 Purpose

`panel_rows` define how output content should be divided into panels or blocks on a sheet.

### 9.2 Recommended fields

- `panel_id`
- `panel_kind`
- `order`
- `grouping_mode`
- `target_ref_id`
- `preferred_width`
- `preferred_height`
- `notes`

### 9.3 Recommended panel kinds

- `plan_panel`
- `profile_panel`
- `section_panel`
- `summary_panel`
- `metadata_panel`

### 9.4 Recommended grouping modes

- `single`
- `stacked`
- `row_grouped`
- `column_grouped`
- `station_series`

## 10. Label Rows

### 10.1 Purpose

`label_rows` control label visibility and priority without changing engineering semantics.

### 10.2 Recommended fields

- `label_id`
- `label_kind`
- `visible`
- `priority`
- `abbreviation_mode`
- `notes`

### 10.3 Recommended label kinds

- `station_label`
- `component_label`
- `region_label`
- `structure_label`
- `grade_label`
- `earthwork_label`

## 11. Dimension Rows

### 11.1 Purpose

`dimension_rows` control whether dimension categories appear and how strongly they are prioritized.

### 11.2 Recommended fields

- `dimension_hint_id`
- `dimension_kind`
- `visible`
- `priority`
- `band_role`
- `notes`

### 11.3 Recommended dimension kinds

- `component_width`
- `overall_width`
- `offset_dimension`
- `structure_clearance`
- `terrain_reach`
- `profile_grade_dimension`

## 12. Summary Rows

### 12.1 Purpose

`summary_rows` define summary-block intent for sheet consumers.

### 12.2 Recommended fields

- `summary_hint_id`
- `summary_kind`
- `visible`
- `priority`
- `placement_mode`
- `notes`

### 12.3 Recommended summary kinds

- `alignment_summary`
- `profile_summary`
- `section_summary`
- `earthwork_summary`
- `structure_summary`
- `quantity_summary`

### 12.4 Recommended placement modes

- `top_block`
- `bottom_block`
- `side_block`
- `inline_panel`

## 13. Metadata Rows

### 13.1 Purpose

`metadata_rows` define title-block-like content that should appear on a sheet.

### 13.2 Recommended fields

- `metadata_id`
- `kind`
- `label`
- `value_ref`
- `visible`
- `priority`

### 13.3 Recommended kinds

- `project_name`
- `alignment_name`
- `sheet_type`
- `station_scope`
- `unit_label`
- `generated_at`

## 14. Diagnostic Rows

### 14.1 Purpose

`diagnostic_rows` report layout-specific issues or degraded presentation states.

### 14.2 Recommended fields

- `diagnostic_id`
- `severity`
- `kind`
- `message`
- `related_panel_id`
- `action_hint`

### 14.3 Recommended kinds

- `panel_overflow`
- `label_congestion`
- `dimension_suppressed`
- `summary_block_truncated`
- `scale_conflict`

## 15. Shared Layout Rule

The same sheet layout hint contract should be reusable across:

- plan outputs
- profile outputs
- section outputs
- section sheet outputs

This helps keep:

- preview behavior
- DXF export behavior
- future SVG sheet behavior

more consistent.

## 16. Consumer Rule

Sheet consumers should use layout hints to decide presentation, but they should still remain robust when:

- a hint is missing
- a hint is unsupported
- a panel is too dense for the requested layout

Consumers may degrade gracefully, but they should report degraded behavior clearly.

## 17. Validation Rules

The layout-hint schema should be validated for:

- missing root metadata
- invalid `sheet_kind`
- duplicate panel orders
- invalid visibility flags
- references to unknown target outputs

## 18. Anti-Patterns to Avoid

Avoid the following:

- embedding engineering calculations in layout hints
- making each exporter invent a different panel model
- hiding suppressed labels or dimensions with no diagnostics
- treating layout hints as mandatory hard constraints in every case

## 19. Recommended Follow-Up Documents

This schema document should be followed by:

1. `V1_LANDXML_MAPPING_PLAN.md`
2. `V1_DXF_MAPPING_PLAN.md`
3. `V1_SURFACE_OUTPUT_SCHEMA.md`

## 20. Final Rule

In v1, sheet layout hints should remain a shared presentation contract layered on top of normalized engineering outputs, not a substitute for them.
