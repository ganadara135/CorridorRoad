# CorridorRoad V1 Quantity Output Schema

Date: 2026-04-23
Branch: `v1-dev`
Status: Draft baseline
Depends on:

- `docsV1/V1_OUTPUT_STRATEGY.md`
- `docsV1/V1_QUANTITY_MODEL.md`
- `docsV1/V1_EXCHANGE_OUTPUT_SCHEMA.md`
- `docsV1/V1_SECTION_OUTPUT_SCHEMA.md`

## 1. Purpose

This document defines the normalized `QuantityOutput` contract for v1.

It exists so that:

- quantity reports
- quantity sheets
- scenario comparison views
- exchange packaging helpers

can consume the same quantity payload instead of rebuilding totals independently.

## 2. Scope

This schema covers:

- quantity output root metadata
- fragment, aggregate, grouping, and comparison rows
- summary and diagnostic rows
- output selection scope and traceability

This schema does not define:

- final sheet layout details
- procurement-specific document formatting
- raw source authoring rules

## 3. Core Rule

`QuantityOutput` is a derived output contract built from normalized quantity results.

It is not a source authoring model.

Consumers may render, export, compare, or summarize it, but they must not treat it as the durable engineering source of truth.

## 4. Schema Versioning

Recommended initial version:

- `QuantityOutputSchemaVersion = 1`

## 5. QuantityOutput Root Structure

Recommended top-level fields:

- `schema_version`
- `quantity_output_id`
- `project_id`
- optional `corridor_id`
- `label`
- `unit_context`
- `selection_scope`
- `source_refs`
- `result_refs`
- `fragment_rows`
- `aggregate_rows`
- `grouping_rows`
- `comparison_rows`
- `summary_rows`
- `diagnostic_rows`

## 6. Required Root Metadata

### 6.1 Identity fields

Required fields should include:

- `quantity_output_id`
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

`unit_context` ensures that quantity values are interpretable without silent assumptions.

### 7.2 Recommended fields

- `linear_unit`
- `area_unit`
- `volume_unit`
- optional `count_unit`

### 7.3 Rule

Quantity outputs must not rely on hidden unit conventions.

## 8. Selection Scope

### 8.1 Purpose

`selection_scope` records what portion of the project or corridor the output represents.

### 8.2 Recommended fields

- `scope_kind`
- optional `alignment_id`
- optional `corridor_id`
- optional `station_start`
- optional `station_end`
- optional `region_ids`
- optional `scenario_id`
- `notes`

### 8.3 Recommended scope kinds

- `project_total`
- `corridor_total`
- `station_range`
- `region_subset`
- `scenario_subset`

## 9. Source References

### 9.1 Purpose

`source_refs` identify which normalized source models contributed to the quantity output.

### 9.2 Recommended fields

- `ref_id`
- `source_kind`
- `source_id`
- `label`
- `notes`

### 9.3 Recommended source kinds

- `template`
- `region`
- `structure`
- `alignment`
- `profile`

## 10. Result References

### 10.1 Purpose

`result_refs` identify which derived result families contributed to the output.

### 10.2 Recommended fields

- `ref_id`
- `result_kind`
- `result_id`
- `label`
- `notes`

### 10.3 Recommended result kinds

- `applied_section`
- `applied_section_set`
- `surface`
- `quantity_result`
- `earthwork_result`

## 11. Fragment Rows

### 11.1 Purpose

`fragment_rows` carry small, traceable quantity contributions.

### 11.2 Recommended fragment row fields

- `fragment_row_id`
- `fragment_id`
- `quantity_kind`
- `measurement_kind`
- `value`
- `unit`
- optional `station_start`
- optional `station_end`
- optional `component_ref`
- optional `region_ref`
- optional `structure_ref`
- optional `source_ref`
- `notes`

### 11.3 Recommended quantity kinds

- `pavement_quantity`
- `component_quantity`
- `surface_area_quantity`
- `linear_quantity`
- `structure_adjacent_quantity`
- `earthwork_linked_quantity`

### 11.4 Rule

Fragment rows should preserve enough semantics for regrouping and drill-down review.

## 12. Aggregate Rows

### 12.1 Purpose

`aggregate_rows` carry grouped or summarized quantity values.

### 12.2 Recommended aggregate row fields

- `aggregate_row_id`
- `aggregate_id`
- `aggregate_kind`
- `grouping_ref`
- `value`
- `unit`
- `fragment_refs`
- `notes`

### 12.3 Recommended aggregate kinds

- `project_total`
- `corridor_total`
- `station_range_total`
- `region_total`
- `component_total`
- `pavement_total`
- `structure_note_total`

### 12.4 Rule

Aggregate rows should remain traceable back to explicit fragment references.

## 13. Grouping Rows

### 13.1 Purpose

`grouping_rows` preserve how fragments and aggregates are grouped for analysis or output.

### 13.2 Recommended grouping row fields

- `grouping_row_id`
- `grouping_id`
- `grouping_kind`
- `grouping_key`
- optional `station_start`
- optional `station_end`
- optional `region_ref`
- optional `scenario_ref`
- `notes`

### 13.3 Recommended grouping kinds

- `by_component`
- `by_region`
- `by_station_range`
- `by_structure_context`
- `by_scenario`

## 14. Comparison Rows

### 14.1 Purpose

`comparison_rows` carry quantity comparisons across scenarios or alternatives.

### 14.2 Recommended comparison row fields

- `comparison_row_id`
- `comparison_id`
- `comparison_kind`
- `base_ref`
- `compare_ref`
- `delta_value`
- `unit`
- `impact_summary`
- `notes`

### 14.3 Recommended comparison kinds

- `baseline_vs_candidate`
- `region_policy_comparison`
- `scenario_total_comparison`
- `earthwork_aware_comparison`

### 14.4 Rule

Comparison rows should compare normalized quantity results, not presentation-layer tables.

## 15. Summary Rows

### 15.1 Purpose

`summary_rows` provide compact, display-friendly quantity rollups.

### 15.2 Recommended summary row fields

- `summary_id`
- `kind`
- `label`
- `value`
- `unit`
- optional `grouping_ref`
- `notes`

### 15.3 Recommended kinds

- `headline_total`
- `pavement_summary`
- `region_summary`
- `structure_note_summary`
- `scenario_delta_summary`

## 16. Diagnostic Rows

### 16.1 Purpose

`diagnostic_rows` surface quantity-engineering issues in a normalized way.

### 16.2 Recommended diagnostic row fields

- `diagnostic_id`
- `severity`
- `kind`
- optional `fragment_ref`
- optional `aggregate_ref`
- optional `grouping_ref`
- `message`
- `notes`

### 16.3 Recommended kinds

- `missing_fragment_source`
- `invalid_unit_mix`
- `orphaned_aggregate`
- `grouping_conflict`
- `traceability_loss`
- `comparison_incompatibility`

## 17. Output Modes

Recommended output modes supported by the same schema:

- project total output
- corridor total output
- station-range output
- region-summary output
- scenario-comparison output

The same schema should support all of them through `selection_scope` and row families.

## 18. Relationship to Section Outputs

`SectionOutput` and `SectionSheetOutput` may embed or reference quantity snippets.

Architectural rule:

- `SectionOutput` carries section-local quantity rows where useful
- `QuantityOutput` carries the normalized quantity-focused contract for broader reporting and comparison

The two schemas should remain compatible, but one should not replace the other.

## 19. Relationship to Exchange Outputs

`QuantityOutput` may be referenced by `ExchangeOutputSchema` through:

- `output_refs`
- package metadata
- degraded-export diagnostics where relevant

This is especially useful when exchange packages include quantity summaries or notes.

## 20. Relationship to Viewer and Reports

Viewer and report systems may consume:

- fragment rows for drill-down
- aggregate rows for totals
- grouping rows for filters
- comparison rows for alternatives
- summary rows for quick readouts

But they must not become the new quantity source.

## 21. Validation Rules

Validation should check for:

- missing fragment references
- invalid unit mixing inside one aggregate
- orphaned grouping rows
- inconsistent selection scope
- incompatible comparison references

Validation results should appear in `diagnostic_rows`.

## 22. Anti-Patterns

The following should be avoided:

- letting spreadsheets or report tables become the quantity truth
- outputting only totals with no fragment traceability
- rebuilding quantity meaning inside every report tool
- hiding scenario comparisons in ad-hoc UI state only
- mixing earthwork balance payloads directly into quantity rows without clear meaning

## 23. Summary

In v1, `QuantityOutput` is the normalized output contract for:

- traceable quantity fragments
- grouped aggregates
- reusable grouping semantics
- scenario and alternative comparisons
- compact report summaries

It should remain consistent with `QuantityModel`, so that:

- reports and sheets can consume one stable payload
- scenario comparison stays reliable
- exchange packaging can reference quantity outputs cleanly
- quantity logic remains separate from presentation details
