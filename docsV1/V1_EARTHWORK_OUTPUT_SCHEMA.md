# CorridorRoad V1 Earthwork Output Schema

Date: 2026-04-23
Branch: `v1-dev`
Status: Draft baseline, profile earthwork depth/area attachment bridge noted
Depends on:

- `docsV1/V1_EARTHWORK_BALANCE_PLAN.md`
- `docsV1/V1_OUTPUT_STRATEGY.md`
- `docsV1/V1_PROFILE_OUTPUT_SCHEMA.md`
- `docsV1/V1_EXCHANGE_OUTPUT_SCHEMA.md`

## 1. Purpose

This document defines the normalized `EarthworkBalanceOutput` and `MassHaulOutput` contracts for v1.

It exists so that:

- cut/fill reports
- mass-haul diagrams
- scenario comparison views
- profile-linked earthwork annotations
- exchange packaging helpers

can consume one stable analytical payload family.

## 2. Scope

This schema covers:

- earthwork balance root metadata
- station-based balance rows
- borrow/waste and surplus/deficit rows
- cumulative mass-haul rows
- balance-point, summary, comparison, and diagnostic rows

This schema does not define:

- optimization objective configuration
- raw source authoring rules
- final sheet layout behavior

## 3. Core Rule

`EarthworkBalanceOutput` and `MassHaulOutput` are derived analytical output contracts.

They are not source authoring models.

Consumers may review, compare, export, or annotate them, but they must not treat them as the durable engineering source of truth.

## 4. Schema Versioning

Recommended initial versions:

- `EarthworkBalanceOutputSchemaVersion = 1`
- `MassHaulOutputSchemaVersion = 1`

## 5. EarthworkBalanceOutput Root Structure

Recommended top-level fields:

- `schema_version`
- `earthwork_output_id`
- `project_id`
- optional `corridor_id`
- `label`
- `unit_context`
- `selection_scope`
- `source_refs`
- `result_refs`
- `balance_rows`
- `material_rows`
- `zone_rows`
- `summary_rows`
- `comparison_rows`
- `diagnostic_rows`

## 6. MassHaulOutput Root Structure

Recommended top-level fields:

- `schema_version`
- `mass_haul_output_id`
- `project_id`
- optional `corridor_id`
- `label`
- `unit_context`
- `selection_scope`
- `source_refs`
- `result_refs`
- `curve_rows`
- `balance_point_rows`
- `haul_zone_rows`
- `summary_rows`
- `comparison_rows`
- `diagnostic_rows`

## 7. Required Root Metadata

### 7.1 Identity fields

Required fields should include:

- `project_id`
- `earthwork_output_id` or `mass_haul_output_id`

### 7.2 Optional corridor scope

Recommended optional field:

- `corridor_id`

This should be present when the output is corridor-scoped rather than project-global.

### 7.3 Label field

Recommended field:

- `label`

This should provide a human-readable identifier for the output package.

## 8. Unit Context

### 8.1 Purpose

`unit_context` ensures earthwork values are interpretable without silent assumptions.

### 8.2 Recommended fields

- `linear_unit`
- `area_unit`
- `volume_unit`
- optional `mass_unit`

### 8.3 Rule

Earthwork outputs must not rely on hidden unit conventions.

## 9. Selection Scope

### 9.1 Purpose

`selection_scope` records what portion of the project or corridor the analysis output represents.

### 9.2 Recommended fields

- `scope_kind`
- optional `alignment_id`
- optional `corridor_id`
- optional `station_start`
- optional `station_end`
- optional `region_ids`
- optional `scenario_id`
- `notes`

### 9.3 Recommended scope kinds

- `project_total`
- `corridor_total`
- `station_range`
- `region_subset`
- `scenario_subset`

## 10. Source References

### 10.1 Purpose

`source_refs` identify which normalized source models contributed to the earthwork output.

### 10.2 Recommended fields

- `ref_id`
- `source_kind`
- `source_id`
- `label`
- `notes`

### 10.3 Recommended source kinds

- `alignment`
- `profile`
- `region`
- `structure`
- `template`

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

- `applied_section_set`
- `surface`
- `earthwork_result`
- `mass_haul_result`
- `quantity_result`

## 12. Balance Rows

### 12.1 Purpose

`balance_rows` carry station-based cut/fill and related balance values.

### 12.2 Recommended balance row fields

- `balance_row_id`
- optional `station_start`
- optional `station_end`
- `cut_value`
- `fill_value`
- optional `usable_cut_value`
- optional `unusable_cut_value`
- optional `balance_ratio`
- `unit`
- `notes`

### 12.3 Rule

Balance rows should remain traceable to normalized section and surface-derived analysis, not opaque report calculations.

## 13. Material Rows

### 13.1 Purpose

`material_rows` carry material usability and related earthwork interpretation.

### 13.2 Recommended material row fields

- `material_row_id`
- `kind`
- optional `station_start`
- optional `station_end`
- `value`
- `unit`
- optional `material_class`
- `notes`

### 13.3 Recommended kinds

- `usable_cut`
- `unusable_cut`
- `fill_demand`
- `borrow_requirement`
- `waste_requirement`

## 14. Zone Rows

### 14.1 Purpose

`zone_rows` identify station ranges with meaningful earthwork state.

### 14.2 Recommended zone row fields

- `zone_row_id`
- `kind`
- `station_start`
- `station_end`
- optional `value`
- optional `unit`
- `notes`

### 14.3 Recommended kinds

- `surplus_zone`
- `deficit_zone`
- `borrow_zone`
- `waste_zone`
- `review_zone`

## 15. Curve Rows

### 15.1 Purpose

`curve_rows` carry cumulative mass-haul curve data.

### 15.2 Recommended curve row fields

- `curve_row_id`
- `kind`
- `station_values`
- `cumulative_mass_values`
- `unit`
- `notes`

### 15.3 Recommended kinds

- `cumulative_mass_curve`
- `comparison_mass_curve`

### 15.4 Rule

Mass-haul curve rows should remain attached to normalized earthwork result identity rather than only existing as chart pixels.

## 16. Balance Point Rows

### 16.1 Purpose

`balance_point_rows` identify meaningful balance points along the corridor.

### 16.2 Recommended fields

- `balance_point_row_id`
- `station`
- `kind`
- optional `value`
- optional `unit`
- `notes`

### 16.3 Recommended kinds

- `balance_point`
- `near_balance_point`
- `candidate_balance_point`

## 17. Haul Zone Rows

### 17.1 Purpose

`haul_zone_rows` identify haul-related station ranges and interpretation zones.

### 17.2 Recommended fields

- `haul_zone_row_id`
- `kind`
- `station_start`
- `station_end`
- optional `direction`
- optional `value`
- optional `unit`
- `notes`

### 17.3 Recommended kinds

- `haul_direction_zone`
- `free_haul_zone`
- `overhaul_zone`
- `borrow_zone`
- `waste_zone`

## 18. Summary Rows

### 18.1 Purpose

`summary_rows` provide compact, display-friendly earthwork rollups.

### 18.2 Recommended fields

- `summary_id`
- `kind`
- `label`
- `value`
- `unit`
- `notes`

### 18.3 Recommended kinds

- `total_cut`
- `total_fill`
- `usable_cut_summary`
- `borrow_summary`
- `waste_summary`
- `balance_ratio_summary`
- `mass_haul_summary`
- `final_cumulative_mass`
- `max_surplus_cumulative_mass`
- `max_deficit_cumulative_mass`

Current implementation note:

- `MassHaulService` builds a cumulative mass curve from ordered earthwork balance rows
- balance points are interpolated where the cumulative curve crosses zero inside a station window
- `MassHaulOutput.summary_rows` include final cumulative mass and max surplus/deficit cumulative mass

## 19. Comparison Rows

### 19.1 Purpose

`comparison_rows` carry earthwork and mass-haul comparisons across scenarios or alternatives.

### 19.2 Recommended fields

- `comparison_row_id`
- `comparison_id`
- `comparison_kind`
- `base_ref`
- `compare_ref`
- `delta_value`
- `unit`
- `impact_summary`
- `notes`

### 19.3 Recommended kinds

- `baseline_vs_candidate`
- `profile_change_comparison`
- `region_policy_comparison`
- `scenario_balance_comparison`
- `mass_haul_comparison`

## 20. Diagnostic Rows

### 20.1 Purpose

`diagnostic_rows` surface analytical and traceability issues in a normalized way.

### 20.2 Recommended fields

- `diagnostic_id`
- `severity`
- `kind`
- optional `station`
- optional `balance_row_ref`
- optional `curve_row_ref`
- `message`
- `notes`

### 20.3 Recommended kinds

- `missing_surface_reference`
- `invalid_station_range`
- `material_classification_gap`
- `mass_curve_inconsistency`
- `traceability_loss`
- `comparison_incompatibility`

## 21. Relationship to ProfileOutput

`ProfileOutput` may attach selected earthwork context through `earthwork_rows`.

Architectural rule:

- `ProfileOutput` carries attached earthwork annotations for profile review
- early profile attachments may include `profile_cut_depth`, `profile_fill_depth`, `profile_cut_area`, and `profile_fill_area`
- current profile area attachments are rectangular-equivalent `depth * explicit_section_width` hints, not final earthwork balance output truth
- `EarthworkBalanceOutput` and `MassHaulOutput` carry the primary analytical truth for earthwork reporting and comparison

Profile consumers should not pretend to own earthwork truth.

## 22. Relationship to QuantityOutput

Earthwork and quantity outputs are related but distinct.

The rule is:

- `QuantityOutput` carries measurable component and reporting quantities
- `EarthworkBalanceOutput` and `MassHaulOutput` carry balance and haul analysis

Cross-references may exist, but the payload families should remain conceptually separate.

## 23. Relationship to Exchange Outputs

Earthwork outputs may be referenced by `ExchangeOutputSchema` through:

- `result_refs`
- `output_refs`
- package diagnostics where relevant

This is useful when exchange packages include earthwork summaries or related analysis notes.

## 24. Output Modes

Recommended output modes supported by the same schema family:

- project-total earthwork output
- corridor-total earthwork output
- station-range output
- scenario-comparison output
- dedicated mass-haul output

The same schema family should support all of them through `selection_scope` and row families.

## 25. Validation Rules

Validation should check for:

- missing surface or section references
- incompatible station ranges in comparisons
- invalid mass curve sampling
- inconsistent units inside one output package
- orphaned balance or haul rows

Validation results should appear in `diagnostic_rows`.

## 26. Anti-Patterns

The following should be avoided:

- hiding mass-haul truth only inside charts
- mixing quantity totals into earthwork rows with no clear meaning
- letting profile annotations become the only earthwork representation
- rebuilding earthwork meaning inside every viewer or report tool
- collapsing borrow, waste, balance, and comparison semantics into one unlabeled total

## 27. Summary

In v1, `EarthworkBalanceOutput` and `MassHaulOutput` are the normalized output contracts for:

- station-based cut/fill balance
- usable and unusable material interpretation
- borrow and waste zones
- cumulative mass-haul curves
- scenario and alternative comparisons
- compact analytical summaries

They should remain distinct from `QuantityOutput`, so that:

- earthwork analysis stays explainable
- profile and review systems can attach context without owning truth
- exchange packaging can reference stable analytical outputs
- mass-haul and balance workflows share one consistent payload family
